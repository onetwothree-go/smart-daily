"""TK-V2-902 考勤独立支路合流与 CLI 第五源红测试（第 4 周变更涟漪）。

契约：design 0.7-diff 0.4 §2 / §4-3 / §4-4 / §6 / §8-A、tasks TK-V2-902。
考勤源按 name == "feishu_attendance" 从主链分出，独立 try/except、
失败留痕不中断、成功条目合流进既有 local_date 过滤 → 显示名映射 → group_by_member；
不进 collect_with_fallback 降级链（C8 / ADR-103 语义不变）。
B#5/B#6 未齐（U13），只用桩/夹具验收，不联调真实接口。

红→绿：本文件先于实现落地，pytest 应红；实现后应绿。
"""

from datetime import date, datetime, time, timedelta

import pytest

from smart_daily_v2.models import LOCAL_TZ, WorkItem, local_date
from smart_daily_v2.sources.base import (
    AllSourcesUnavailableError,
    SourceUnavailableError,
)

DAY = date(2026, 11, 25)
SINCE = datetime.combine(DAY, time.min, tzinfo=LOCAL_TZ)
UNTIL = datetime.combine(DAY + timedelta(days=1), time.min, tzinfo=LOCAL_TZ)
MOCK_SINCE = datetime(2026, 11, 18, 0, 0, tzinfo=LOCAL_TZ)
MOCK_UNTIL = datetime(2026, 11, 19, 0, 0, tzinfo=LOCAL_TZ)
ATTENDANCE_NAME = "feishu_attendance"


def _item(
    record_id: str,
    member: str,
    *,
    kind: str = "commit",
    source: str = "github",
    hour: int = 9,
    day: date = DAY,
) -> WorkItem:
    occurred_at = datetime.combine(day, time(hour), tzinfo=LOCAL_TZ)
    return WorkItem(
        record_id=record_id,
        source=source,
        member=member,
        kind=kind,
        title=f"t-{record_id}",
        detail="",
        occurred_at=occurred_at,
        local_day=local_date(occurred_at),
    )


def _attendance_item(record_id: str = "att-1", member: str = "甲") -> WorkItem:
    return _item(record_id, member, kind="attendance", source=ATTENDANCE_NAME, hour=9)


def _source(name: str, items: list[WorkItem], *, raises=None, calls=None):
    class FakeSource:
        def __init__(self) -> None:
            self.name = name

        def collect(self, *, since, until, author=None):
            if calls is not None:
                calls.append(name)
            if raises is not None:
                raise raises
            return list(items)

    return FakeSource()


def _patch_run(monkeypatch, cli):
    """把 orchestrator.run 换成只记录 sources 的桩，隔离 CLI 参数解析。"""
    calls = []

    def fake_run(day, *, sources, notify=True):
        calls.append({"day": day, "sources": sources, "notify": notify})
        return {"source": [], "push_status": "ok", "items": 0}

    monkeypatch.setattr(cli.orchestrator, "run", fake_run)
    return calls


# --- 验收①：考勤独立支路，不进 collect_with_fallback ---


def test_attendance_source_bypasses_fallback(monkeypatch) -> None:
    import smart_daily_v2.orchestrator as orch

    main = _source("github", [_item("main-1", "甲")])
    attendance = _source(ATTENDANCE_NAME, [_attendance_item()])
    seen: list[str] = []
    real_fallback = orch.collect_with_fallback

    def spy(sources, *, since, until, author=None):
        seen.extend(source.name for source in sources)
        return real_fallback(sources, since=since, until=until, author=author)

    monkeypatch.setattr(orch, "collect_with_fallback", spy)

    result = orch.run(DAY, sources=[main, attendance], notify=False)

    assert seen == ["github"], "考勤源不得进入 collect_with_fallback 降级链"
    assert result["items"] == 2, "考勤条目须合流进既有流程"


def test_attendance_items_flow_into_team_report(monkeypatch) -> None:
    import smart_daily_v2.orchestrator as orch

    attendance = _source(ATTENDANCE_NAME, [_attendance_item("att-2", "甲")])
    result = orch.run(DAY, sources=[attendance], notify=False)

    assert "`考勤`" in result["team_report"] or "attendance" in result["team_report"]
    assert result["members"] == 1


# --- 验收②：考勤失败仅留痕，不判整次退出码 1（除非全部失败）---


def test_attendance_failure_only_traced(monkeypatch) -> None:
    import smart_daily_v2.orchestrator as orch

    main = _source("github", [_item("main-1", "甲")])
    bad = _source(
        ATTENDANCE_NAME,
        [],
        raises=SourceUnavailableError(ATTENDANCE_NAME, "权限未开通"),
    )

    result = orch.run(DAY, sources=[main, bad], notify=False)

    assert result["items"] == 1
    assert any("权限未开通" in reason for reason in result["source"]), "考勤失败须留痕"


def test_main_failure_but_attendance_ok_no_raise(monkeypatch) -> None:
    import smart_daily_v2.orchestrator as orch

    main = _source("github", [], raises=SourceUnavailableError("github", "无凭证"))
    attendance = _source(ATTENDANCE_NAME, [_attendance_item()])

    result = orch.run(DAY, sources=[main, attendance], notify=False)

    assert result["items"] == 1, "主链全失败但考勤成功时不应判整次失败"


def test_all_sources_failed_still_raises(monkeypatch) -> None:
    import smart_daily_v2.orchestrator as orch

    main = _source("github", [], raises=SourceUnavailableError("github", "无凭证"))
    bad = _source(
        ATTENDANCE_NAME,
        [],
        raises=SourceUnavailableError(ATTENDANCE_NAME, "权限未开通"),
    )

    with pytest.raises(AllSourcesUnavailableError):
        orch.run(DAY, sources=[main, bad], notify=False)


def test_only_attendance_failed_raises(monkeypatch) -> None:
    import smart_daily_v2.orchestrator as orch

    bad = _source(
        ATTENDANCE_NAME,
        [],
        raises=SourceUnavailableError(ATTENDANCE_NAME, "权限未开通"),
    )

    with pytest.raises(AllSourcesUnavailableError):
        orch.run(DAY, sources=[bad], notify=False)


def test_attendance_window_is_keyword_only_and_local(monkeypatch) -> None:
    import smart_daily_v2.orchestrator as orch

    calls: list[str] = []
    attendance = _source(ATTENDANCE_NAME, [_attendance_item()], calls=calls)
    orch.run(DAY, sources=[attendance], notify=False)

    assert calls == [ATTENDANCE_NAME]


# --- 验收③：SOURCE_TYPES 第五源，--source 可单独跑考勤 ---


def test_cli_source_types_includes_attendance() -> None:
    import smart_daily_v2.cli as cli

    assert ATTENDANCE_NAME in cli.SOURCE_TYPES
    assert cli.SOURCE_TYPES[ATTENDANCE_NAME].__name__ == "FeishuAttendanceSource"


def test_cli_source_selects_attendance(monkeypatch) -> None:
    import smart_daily_v2.cli as cli

    calls = _patch_run(monkeypatch, cli)
    assert cli.main(["--source", ATTENDANCE_NAME, "--no-notify"]) == 0
    assert [source.name for source in calls[0]["sources"]] == [ATTENDANCE_NAME]


# --- 验收④：--mock 样例含考勤条目 ---


def test_mock_source_can_include_attendance(cleared_env) -> None:
    from smart_daily_v2.sources.mock import MockSource

    source = MockSource(include_attendance=True)
    items = source.collect(since=MOCK_SINCE, until=MOCK_UNTIL)

    assert any(item.kind == "attendance" for item in items)
    assert any(item.source == ATTENDANCE_NAME for item in items)


def test_cli_mock_requests_attendance_fixture(monkeypatch) -> None:
    import smart_daily_v2.cli as cli

    calls = _patch_run(monkeypatch, cli)
    assert cli.main(["--mock", "--no-notify"]) == 0
    source = calls[0]["sources"][0]
    assert source.name == "mock"
    items = source.collect(since=MOCK_SINCE, until=MOCK_UNTIL)
    assert any(item.kind == "attendance" for item in items)


# --- 验收⑤：实时提醒边界不变（不新增推送 scope / exit table 不动）---


def test_exit_code_table_and_scope_unchanged() -> None:
    import smart_daily_v2.cli as cli

    for anchor in ("0 | 成功", "1 | 采集或落库失败", "2 | 参数错误", "3 | 推送存在失败项"):
        assert anchor in cli.EXIT_CODE_TABLE
    assert cli.EXIT_CODE_TABLE.count("\n") == 4
