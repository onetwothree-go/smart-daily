import inspect
from datetime import date, datetime
from pathlib import Path

import httpx
import pytest

from smart_daily_v2.identity import normalize_key
from smart_daily_v2.models import LOCAL_TZ, WorkItem, local_date
from smart_daily_v2.sources.base import SourceUnavailableError, WorkSource

SINCE = datetime(2026, 11, 9, 0, 0, tzinfo=LOCAL_TZ)
UNTIL = datetime(2026, 11, 11, 0, 0, tzinfo=LOCAL_TZ)
DAY_1109_SINCE = datetime(2026, 11, 9, 0, 0, tzinfo=LOCAL_TZ)
DAY_1109_UNTIL = datetime(2026, 11, 10, 0, 0, tzinfo=LOCAL_TZ)
DAY_1110_SINCE = datetime(2026, 11, 10, 0, 0, tzinfo=LOCAL_TZ)
DAY_1110_UNTIL = datetime(2026, 11, 11, 0, 0, tzinfo=LOCAL_TZ)


def _task(
    task_id: str,
    summary: str,
    created_at: str,
    completed_at: str,
    completed: bool,
    creator_name: str = " MemberA ",
) -> dict[str, object]:
    return {
        "task_id": task_id,
        "summary": summary,
        "description": f"{summary} 的描述原文",
        "creator_id": "ou-placeholder",
        "creator_name": creator_name,
        "created_at": created_at,
        "completed_at": completed_at,
        "completed": completed,
        "due": "2026-11-12T18:00:00+08:00",
        "members": ["ou-placeholder"],
    }


def _page(
    items: list[dict[str, object]], has_more: bool = False, page_token: str = ""
) -> dict[str, object]:
    return {
        "code": 0,
        "data": {"items": items, "has_more": has_more, "page_token": page_token},
    }


def _error_page(code: int) -> dict[str, object]:
    return {"code": code, "msg": "placeholder error"}


def _response(status: int, payload: object) -> httpx.Response:
    return httpx.Response(
        status,
        json=payload,
        request=httpx.Request("GET", "https://example.com"),
    )


def _install_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "fake-app-id")
    monkeypatch.setenv("FEISHU_APP_SECRET", "fake-app-secret")
    monkeypatch.setenv("FEISHU_API", "https://example.com")


def _fake_get(
    monkeypatch: pytest.MonkeyPatch,
    pages: list[httpx.Response],
) -> list[dict[str, object]]:
    calls: list[dict[str, object]] = []

    def fake_get(url: str, *, params, headers, timeout):
        calls.append({"url": url, "params": params, "headers": headers, "timeout": timeout})
        return pages[len(calls) - 1]

    monkeypatch.setattr(httpx, "get", fake_get)
    return calls


def _fake_get_by_day(
    monkeypatch: pytest.MonkeyPatch,
    pages_by_day: dict[str, httpx.Response],
) -> list[dict[str, object]]:
    calls: list[dict[str, object]] = []

    def fake_get(url: str, *, params, headers, timeout):
        calls.append({"url": url, "params": params, "headers": headers, "timeout": timeout})
        day = params["created_at_from"][:10]
        return pages_by_day.get(day, _response(200, _page([])))

    monkeypatch.setattr(httpx, "get", fake_get)
    return calls


def test_two_tasks_map_to_workitems_with_derived_fields(monkeypatch, cleared_env) -> None:
    import smart_daily_v2.sources.feishu_tasks as ft

    _install_env(monkeypatch)
    tasks = [
        _task(
            "task-202-001",
            "甲 任务一",
            "2026-11-09T09:00:00+08:00",
            "2026-11-09T10:00:00+08:00",
            True,
            " MemberA ",
        ),
        _task(
            "task-202-002",
            "乙 任务二",
            "2026-11-09T11:00:00+08:00",
            "2026-11-09T12:00:00+08:00",
            False,
            "MEMBERB",
        ),
    ]
    _fake_get(monkeypatch, [_response(200, _page(tasks))])

    items = ft.FeishuTaskSource.from_env().collect(since=SINCE, until=UNTIL)

    assert len(items) == 2
    assert all(isinstance(item, WorkItem) for item in items)
    assert [item.record_id for item in items] == [task["task_id"] for task in tasks]
    assert all(item.source == "feishu_task" and item.kind == "task" for item in items)
    assert [item.title for item in items] == [task["summary"] for task in tasks]
    for item, task in zip(items, tasks, strict=True):
        assert task["description"] in item.detail
        assert str(task["completed"]) in item.detail
        assert task["completed_at"] in item.detail
        assert item.occurred_at == datetime.fromisoformat(task["created_at"])
        assert item.occurred_at.tzinfo is not None
        assert item.local_day == local_date(item.occurred_at)
        assert item.member == normalize_key(task["creator_name"])


def test_cross_day_task_belongs_to_created_day_only(monkeypatch, cleared_env) -> None:
    import smart_daily_v2.sources.feishu_tasks as ft

    _install_env(monkeypatch)
    task = _task(
        "task-202-003",
        "丙 跨天任务",
        "2026-11-09T22:30:00+08:00",
        "2026-11-10T09:00:00+08:00",
        True,
    )
    _fake_get_by_day(
        monkeypatch,
        {
            "2026-11-09": _response(200, _page([task])),
            "2026-11-10": _response(200, _page([])),
        },
    )
    source = ft.FeishuTaskSource.from_env()

    created_day_items = source.collect(since=DAY_1109_SINCE, until=DAY_1109_UNTIL)
    completed_day_items = source.collect(since=DAY_1110_SINCE, until=DAY_1110_UNTIL)

    assert len(created_day_items) == 1
    assert created_day_items[0].local_day == date(2026, 11, 9)
    assert completed_day_items == []
    assert (
        sum(item.record_id == task["task_id"] for item in created_day_items + completed_day_items)
        == 1
    )
    assert created_day_items[0].local_day != local_date(
        datetime.fromisoformat(task["completed_at"])
    )


def test_completed_at_only_traced_in_detail_never_counted(monkeypatch, cleared_env) -> None:
    import smart_daily_v2.sources.feishu_tasks as ft

    _install_env(monkeypatch)
    task = _task(
        "task-202-004",
        "丁 跨天任务详情",
        "2026-11-09T22:30:00+08:00",
        "2026-11-10T09:00:00+08:00",
        True,
    )
    _fake_get_by_day(
        monkeypatch,
        {"2026-11-09": _response(200, _page([task]))},
    )

    items = ft.FeishuTaskSource.from_env().collect(since=DAY_1109_SINCE, until=DAY_1109_UNTIL)

    created_at = datetime.fromisoformat(task["created_at"])
    assert len(items) == 1
    assert task["completed_at"] in items[0].detail
    assert items[0].occurred_at == created_at
    assert items[0].local_day == local_date(created_at)


def test_pagination_fetches_all_pages_without_loss(monkeypatch, cleared_env) -> None:
    import smart_daily_v2.sources.feishu_tasks as ft

    _install_env(monkeypatch)
    first_page = [
        _task(
            "task-202-005",
            "甲 第一页一",
            "2026-11-09T09:00:00+08:00",
            "2026-11-09T10:00:00+08:00",
            False,
        ),
        _task(
            "task-202-006",
            "乙 第一页二",
            "2026-11-09T10:00:00+08:00",
            "2026-11-09T11:00:00+08:00",
            True,
        ),
    ]
    second_page = [
        _task(
            "task-202-007",
            "丙 第二页一",
            "2026-11-09T11:00:00+08:00",
            "2026-11-09T12:00:00+08:00",
            False,
        )
    ]
    calls = _fake_get(
        monkeypatch,
        [
            _response(200, _page(first_page, True, "page-2-placeholder")),
            _response(200, _page(second_page)),
        ],
    )

    items = ft.FeishuTaskSource.from_env().collect(since=SINCE, until=UNTIL)

    expected_ids = [task["task_id"] for task in first_page + second_page]
    assert len(items) == 3
    assert set(item.record_id for item in items) == set(expected_ids)
    assert len(calls) == 2
    assert calls[1]["params"]["page_token"] == "page-2-placeholder"


def test_missing_app_credentials_sends_no_request(monkeypatch, cleared_env) -> None:
    import smart_daily_v2.sources.feishu_tasks as ft

    calls: list[object] = []
    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: calls.append(args))

    with pytest.raises(SourceUnavailableError):
        ft.FeishuTaskSource.from_env().collect(since=SINCE, until=UNTIL)

    assert calls == []


def test_missing_app_id_alone_sends_no_request(monkeypatch, cleared_env) -> None:
    import smart_daily_v2.sources.feishu_tasks as ft

    monkeypatch.setenv("FEISHU_APP_SECRET", "fake-app-secret")
    calls: list[object] = []
    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: calls.append(args))

    with pytest.raises(SourceUnavailableError):
        ft.FeishuTaskSource.from_env().collect(since=SINCE, until=UNTIL)

    assert calls == []


def test_feishu_error_code_raises_source_unavailable(monkeypatch, cleared_env) -> None:
    import smart_daily_v2.sources.feishu_tasks as ft

    _install_env(monkeypatch)
    _fake_get(monkeypatch, [_response(200, _error_page(19021))])

    with pytest.raises(SourceUnavailableError) as exc_info:
        ft.FeishuTaskSource.from_env().collect(since=SINCE, until=UNTIL)

    assert "19021" in str(exc_info.value)
    assert "placeholder error" in str(exc_info.value)


def test_collect_signature_is_keyword_only_and_satisfies_worksource(
    monkeypatch, cleared_env
) -> None:
    import smart_daily_v2.sources.feishu_tasks as ft

    _install_env(monkeypatch)
    source = ft.FeishuTaskSource.from_env()
    parameters = inspect.signature(ft.FeishuTaskSource.collect).parameters

    assert parameters["since"].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters["until"].kind is inspect.Parameter.KEYWORD_ONLY
    with pytest.raises(TypeError):
        source.collect(SINCE, UNTIL)
    assert isinstance(source, WorkSource)


def test_request_params_include_time_window_pagination_and_author(monkeypatch, cleared_env) -> None:
    import smart_daily_v2.sources.feishu_tasks as ft

    _install_env(monkeypatch)
    calls = _fake_get(monkeypatch, [_response(200, _page([]))])
    author = " MemberA "

    ft.FeishuTaskSource.from_env().collect(since=SINCE, until=UNTIL, author=author)

    assert len(calls) == 1
    request = calls[0]
    params = request["params"]
    headers = request["headers"]
    assert params["created_at_from"] == SINCE.isoformat()
    assert params["created_at_to"] == UNTIL.isoformat()
    assert "page_size" in params and "page_token" in params
    assert "completed" in params
    assert params["author"] == author
    assert "fake-app-id" in str(headers)
    assert "fake-app-secret" in str(headers)
    assert request["url"].endswith("/task/v1/tasks")
    assert "open.feishu.cn" not in request["url"]
    assert "https://example.com" in request["url"]


def test_scope_registration_docstring_and_no_real_credentials(monkeypatch, cleared_env) -> None:
    import smart_daily_v2.sources.feishu_tasks as ft

    source = Path(ft.__file__).read_text(encoding="utf-8")

    for forbidden in (
        "ghp_",
        "xoxb-",
        "@qq.com",
        "@gmail.com",
        "open.feishu.cn",
        "from smart_daily import",
    ):
        assert forbidden not in source
    for anchor in ("待确认", "RawRecord", "归一化单点"):
        assert anchor in source
    assert "已裁定" not in source
    for registration in (
        "L292",
        "L332",
        "L300",
        "created_at",
        "completed_at",
        "page_token",
        "--day",
    ):
        assert registration in source
