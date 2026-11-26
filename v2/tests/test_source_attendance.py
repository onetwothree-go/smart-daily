"""TK-V2-901 飞书考勤采集源红测试（第 4 周变更涟漪）。

依据 design 0.7-diff 0.4 §3/§4-1/§4-2/§6、tasks TK-V2-901、proposal C11。
B#5（导出打卡数据 scope）、B#6（user_id → 成员键映射）未齐（U13），
**本测试只用桩/夹具验收契约，不联调真实接口**；真实接口联调项单独留 ☐。

红→绿：本文件先于 attendance.py 落地，pytest 应红；实现后应绿。
"""

import inspect
from datetime import date, datetime
from pathlib import Path

import httpx
import pytest

from smart_daily_v2.identity import normalize_key
from smart_daily_v2.models import LOCAL_TZ, WorkItem
from smart_daily_v2.sources.base import SourceUnavailableError, WorkSource

SINCE = datetime(2026, 11, 9, 0, 0, tzinfo=LOCAL_TZ)
UNTIL = datetime(2026, 11, 10, 0, 0, tzinfo=LOCAL_TZ)

# 桩：user_id → 姓名键（B#6 未定，测试内显式注入，不假定同名即同人）
MEMBER_MAP = {"ou-member-a": " MemberA ", "ou-member-b": "memberb"}


def _record(
    record_id: str,
    *,
    status: str = "正常",
    check_time: str | None = "2026-11-09T09:05:00+08:00",
    off_time: str | None = "2026-11-09T18:10:00+08:00",
) -> dict[str, object]:
    return {
        "record_id": record_id,
        "status": status,
        "check_time": check_time,
        "off_time": off_time,
    }


def _user_task(
    user_id: str, records: list[dict[str, object]], *, user_name: str = "占位"
) -> dict[str, object]:
    return {"user_id": user_id, "user_name": user_name, "records": records}


def _page(user_tasks: list[dict[str, object]], *, code: int = 0) -> dict[str, object]:
    payload = {"code": code, "msg": "placeholder error" if code else ""}
    payload["data"] = {"user_task_results": user_tasks}
    return payload


def _response(payload: object, *, status: int = 200) -> httpx.Response:
    return httpx.Response(
        status,
        json=payload,
        request=httpx.Request("POST", "https://example.com"),
    )


def _install_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "fake-app-id")
    monkeypatch.setenv("FEISHU_APP_SECRET", "fake-app-secret")
    monkeypatch.setenv("FEISHU_API", "https://example.com")


def _make_source() -> object:
    from smart_daily_v2.sources.attendance import FeishuAttendanceSource

    return FeishuAttendanceSource(
        feishu_app_id="fake-app-id",
        feishu_app_secret="fake-app-secret",
        feishu_api="https://example.com",
        member_map=dict(MEMBER_MAP),
    )


def _fake_post(
    monkeypatch: pytest.MonkeyPatch, attendance_payload: object
) -> list[dict[str, object]]:
    """token 与打卡接口都走 POST，按 URL 区分桩响应并记录调用。"""

    calls: list[dict[str, object]] = []

    def fake_post(url: str, *, json, timeout, headers=None, params=None) -> httpx.Response:
        calls.append(
            {
                "url": url,
                "json": json,
                "headers": headers,
                "timeout": timeout,
                "params": params,
            }
        )
        if "/auth/v3/tenant_access_token/internal" in url:
            return _response({"code": 0, "tenant_access_token": "fake-token", "expire": 7200})
        return _response(attendance_payload)

    monkeypatch.setattr(httpx, "post", fake_post)
    return calls


def test_two_records_map_to_workitems_with_derived_fields(monkeypatch) -> None:
    payload = _page(
        [
            _user_task("ou-member-a", [_record("att-901-001")]),
            _user_task(
                "ou-member-b",
                [_record("att-901-002", status="迟到", check_time="2026-11-09T09:31:00+08:00")],
            ),
        ]
    )
    calls = _fake_post(monkeypatch, payload)

    items = _make_source().collect(since=SINCE, until=UNTIL)

    assert len(items) == 2
    assert all(isinstance(item, WorkItem) for item in items)
    assert [item.record_id for item in items] == ["att-901-001", "att-901-002"]
    assert all(item.source == "feishu_attendance" for item in items)
    assert all(item.kind == "attendance" for item in items)
    for item, expected_id in zip(items, ["att-901-001", "att-901-002"], strict=True):
        assert expected_id in item.detail  # C11 方案①：record_id 内嵌 detail 对账
    assert "正常" in items[0].detail
    assert "迟到" in items[1].detail
    assert items[0].member == normalize_key(MEMBER_MAP["ou-member-a"])
    assert items[1].member == normalize_key(MEMBER_MAP["ou-member-b"])
    assert items[0].occurred_at == datetime.fromisoformat("2026-11-09T09:05:00+08:00")
    assert items[1].occurred_at == datetime.fromisoformat("2026-11-09T09:31:00+08:00")
    assert all(item.local_day == date(2026, 11, 9) for item in items)
    assert all(item.occurred_at.tzinfo is not None for item in items)
    assert all(
        "/attendance/v1/user_tasks/query" in call["url"]
        for call in calls
        if "auth" not in call["url"]
    )


def test_off_time_is_fallback_when_check_time_missing(monkeypatch) -> None:
    payload = _page(
        [
            _user_task(
                "ou-member-a",
                [_record("att-901-003", check_time=None, off_time="2026-11-09T18:20:00+08:00")],
            )
        ]
    )
    _fake_post(monkeypatch, payload)

    items = _make_source().collect(since=SINCE, until=UNTIL)

    assert len(items) == 1
    assert items[0].occurred_at == datetime.fromisoformat("2026-11-09T18:20:00+08:00")
    assert items[0].local_day == date(2026, 11, 9)


def test_record_without_any_punch_is_skipped(monkeypatch) -> None:
    payload = _page(
        [
            _user_task(
                "ou-member-a",
                [_record("att-901-004", check_time=None, off_time=None)],
            )
        ]
    )
    _fake_post(monkeypatch, payload)

    items = _make_source().collect(since=SINCE, until=UNTIL)

    assert items == []


def test_closed_interval_filters_out_of_window_records(monkeypatch) -> None:
    payload = _page(
        [
            _user_task(
                "ou-member-a",
                [
                    _record("att-901-005", check_time="2026-11-09T09:00:00+08:00"),
                    _record("att-901-006", check_time="2026-11-11T09:00:00+08:00"),
                ],
            )
        ]
    )
    _fake_post(monkeypatch, payload)

    items = _make_source().collect(since=SINCE, until=UNTIL)

    assert [item.record_id for item in items] == ["att-901-005"]


def test_empty_response_returns_empty_list(monkeypatch) -> None:
    _fake_post(monkeypatch, _page([]))

    assert _make_source().collect(since=SINCE, until=UNTIL) == []


def test_missing_credentials_sends_no_request(monkeypatch) -> None:
    calls: list[object] = []
    monkeypatch.setattr(httpx, "post", lambda *a, **k: calls.append(a))

    from smart_daily_v2.sources.attendance import FeishuAttendanceSource

    source = FeishuAttendanceSource(
        feishu_app_id="",
        feishu_app_secret="",
        feishu_api="https://example.com",
        member_map=dict(MEMBER_MAP),
    )
    with pytest.raises(SourceUnavailableError):
        source.collect(since=SINCE, until=UNTIL)

    assert calls == []


def test_error_code_raises_source_unavailable(monkeypatch) -> None:
    _fake_post(monkeypatch, _page([], code=1220005))

    with pytest.raises(SourceUnavailableError) as exc_info:
        _make_source().collect(since=SINCE, until=UNTIL)

    assert "1220005" in str(exc_info.value)


def test_request_uses_user_tasks_query_endpoint_and_employee_type(monkeypatch) -> None:
    calls = _fake_post(monkeypatch, _page([]))

    _make_source().collect(since=SINCE, until=UNTIL)

    attendance_calls = [c for c in calls if "auth" not in c["url"]]
    assert len(attendance_calls) == 1
    request = attendance_calls[0]
    assert request["url"].endswith("/attendance/v1/user_tasks/query")
    assert "https://example.com" in request["url"]
    assert "open.feishu.cn" not in request["url"]
    assert request["params"]["employee_type"] == "employee_id"
    body = request["json"]
    assert set(body["user_ids"]) == set(MEMBER_MAP)
    assert body["check_date_from"] == SINCE.strftime("%Y%m%d")
    assert body["check_date_to"] == UNTIL.strftime("%Y%m%d")
    assert "Authorization" in request["headers"]


def test_unmapped_user_falls_back_to_user_id_with_marker(monkeypatch) -> None:
    payload = _page([_user_task("ou-unknown", [_record("att-901-007")])])
    _fake_post(monkeypatch, payload)

    items = _make_source().collect(since=SINCE, until=UNTIL)

    assert len(items) == 1
    assert items[0].member == normalize_key("ou-unknown")
    assert "未映射" in items[0].detail  # 不静默、不假定同名即同人


def test_workitems_pass_normalize_idempotently(monkeypatch) -> None:
    from smart_daily_v2.models import normalize

    payload = _page([_user_task("ou-member-a", [_record("att-901-008")])])
    _fake_post(monkeypatch, payload)

    items = _make_source().collect(since=SINCE, until=UNTIL)
    normalized = normalize(list(items))

    assert normalized == items  # G7：已 WorkItem 原样放行，不二次归一化


def test_signature_keyword_only_and_satisfies_worksource(monkeypatch) -> None:
    from smart_daily_v2.sources.attendance import FeishuAttendanceSource

    source = _make_source()
    parameters = inspect.signature(FeishuAttendanceSource.collect).parameters

    assert parameters["since"].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters["until"].kind is inspect.Parameter.KEYWORD_ONLY
    assert isinstance(source, WorkSource)
    assert source.name == "feishu_attendance"
    with pytest.raises(TypeError):
        source.collect(SINCE, UNTIL)


def test_parse_member_map_splits_pairs_and_skips_invalid() -> None:
    from smart_daily_v2.sources.attendance import _parse_member_map

    raw = " ou-a: 甲 ,ou-b:乙,invalid-no-colon,ou-c:,:无名,ou-d:丁"
    assert _parse_member_map(raw) == {
        "ou-a": "甲",
        "ou-b": "乙",
        "ou-d": "丁",
    }


def test_from_env_reads_member_map_from_config(monkeypatch) -> None:
    _install_env(monkeypatch)
    monkeypatch.setenv("FEISHU_ATTENDANCE_MEMBER_MAP", "ou-member-a: MemberA ,ou-member-b:memberb")

    from smart_daily_v2.sources.attendance import FeishuAttendanceSource

    source = FeishuAttendanceSource.from_env()
    assert source.member_map == {"ou-member-a": "MemberA", "ou-member-b": "memberb"}
    assert source.feishu_app_id == "fake-app-id"


def test_from_env_empty_map_when_unset(monkeypatch) -> None:
    _install_env(monkeypatch)
    monkeypatch.delenv("FEISHU_ATTENDANCE_MEMBER_MAP", raising=False)

    from smart_daily_v2.sources.attendance import FeishuAttendanceSource

    assert FeishuAttendanceSource.from_env().member_map == {}


def test_scope_registration_and_no_real_credentials() -> None:
    from smart_daily_v2.sources import attendance

    source = Path(attendance.__file__).read_text(encoding="utf-8")

    for forbidden in (
        "ghp_",
        "xoxb-",
        "@qq.com",
        "@gmail.com",
        "open.feishu.cn",
        "from smart_daily import",
        "attendance/v1/user_flows",  # ADR-105：不得真实调用含定位的流水接口
    ):
        assert forbidden not in source
    for anchor in (
        "B#5",
        "B#6",
        "user_tasks/query",
        "feishu_attendance",
        "attendance",
        "未映射",
        "record_id",
    ):
        assert anchor in source
