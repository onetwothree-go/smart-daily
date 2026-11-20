import inspect
from datetime import date, datetime, time, timedelta
from pathlib import Path

import pytest

from smart_daily_v2.models import LOCAL_TZ, WorkItem, local_date
from smart_daily_v2.sources.base import (
    AllSourcesUnavailableError,
    SourceUnavailableError,
    WorkSource,
)

DAY = date(2026, 11, 19)
SINCE = datetime.combine(DAY, time.min, tzinfo=LOCAL_TZ)
UNTIL = datetime.combine(DAY + timedelta(days=1), time.min, tzinfo=LOCAL_TZ)
MEMBERS = ("甲", "乙", "丙", "丁")
EXPECTED_KEYS = {
    "date",
    "source",
    "members",
    "items",
    "saved_reports",
    "pushed",
    "push_status",
    "push_detail",
    "team_report",
}


def _item(
    record_id: str,
    member: str,
    *,
    day: date = DAY,
    hour: int = 9,
    source: str = "github",
) -> WorkItem:
    occurred_at = datetime.combine(day, time(hour), tzinfo=LOCAL_TZ)
    return WorkItem(
        record_id=record_id,
        source=source,
        member=member,
        kind="commit",
        title=f"t-{record_id}",
        detail="",
        occurred_at=occurred_at,
        local_day=local_date(occurred_at),
    )


def _source(name, items, *, raises=None, order=None):
    class FakeSource:
        def __init__(self):
            self.name = name
            self.calls = []

        def collect(self, *, since, until, author=None):
            self.calls.append({"since": since, "until": until, "author": author})
            if order is not None:
                order.append("collect")
            if raises is not None:
                raise raises
            return items

    return FakeSource()


def _patch_dispatch(monkeypatch, mod, results, *, order=None):
    calls = []

    def fake_dispatch(personal, team, *, no_notify=False, team_recipients=()):
        calls.append(
            {
                "personal": personal,
                "team": team,
                "no_notify": no_notify,
                "team_recipients": team_recipients,
            }
        )
        if order is not None:
            order.append("dispatch")
        return results.copy()

    monkeypatch.setattr(mod, "dispatch", fake_dispatch)
    return calls


def _patch_persist(monkeypatch, mod, calls, *, order=None):
    def fake_persist(member, body, item_count, day, source):
        calls.append(
            {
                "member": member,
                "body": body,
                "item_count": item_count,
                "day": day,
                "source": source,
            }
        )
        if order is not None:
            order.append("persist")

    monkeypatch.setattr(mod, "_persist_report", fake_persist)


def _patch_generators(monkeypatch, mod, *, order=None):
    real_group_by_member = mod.group_by_member
    real_build_team_report = mod.build_team_report
    real_build_personal_report = mod.build_personal_report

    def group_by_member(items):
        if order is not None:
            order.append("group")
        return real_group_by_member(items)

    def build_team_report(groups, day):
        if order is not None:
            order.append("team")
        return real_build_team_report(groups, day)

    def build_personal_report(member, items, day):
        if order is not None:
            order.append("personal")
        return real_build_personal_report(member, items, day)

    monkeypatch.setattr(mod, "group_by_member", group_by_member)
    monkeypatch.setattr(mod, "build_team_report", build_team_report)
    monkeypatch.setattr(mod, "build_personal_report", build_personal_report)


def test_run_returns_nine_keys_and_step_order(monkeypatch) -> None:
    import smart_daily_v2.orchestrator as orch

    order = []
    items = [
        _item("rec-501-001", "甲", hour=9),
        _item("rec-501-002", "甲", hour=10),
        _item("rec-501-003", "甲", hour=11),
        _item("rec-501-004", "乙", hour=9),
        _item("rec-501-005", "乙", hour=10),
    ]
    source = _source("source-placeholder", items, order=order)
    persist_calls = []
    _patch_persist(monkeypatch, orch, persist_calls, order=order)
    dispatch_calls = _patch_dispatch(
        monkeypatch, orch, {"personal:甲": True, "personal:乙": True, "team": True}, order=order
    )
    _patch_generators(monkeypatch, orch, order=order)

    result = orch.run(DAY, sources=[source])

    assert set(result) == EXPECTED_KEYS
    assert result["date"] == DAY.isoformat()
    assert result["source"] == []
    assert result["members"] == 2
    assert result["items"] == 5
    assert result["saved_reports"] == 2
    assert "条目 5 条" in result["team_report"]
    assert len(dispatch_calls) == 1
    assert len(persist_calls) == 2
    assert order[0] == "collect"
    assert order.index("collect") < order.index("group")
    assert order.index("group") < order.index("team")
    assert order.index("team") < order.index("personal")
    assert order.index("personal") < order.index("persist")
    assert order.index("persist") < order.index("dispatch")


def test_day_window_is_local_and_keyword_only(monkeypatch) -> None:
    import smart_daily_v2.orchestrator as orch

    source = _source("source-placeholder", [])
    _patch_dispatch(monkeypatch, orch, {})
    _patch_persist(monkeypatch, orch, [])

    orch.run(DAY, sources=[source], notify=False)

    assert source.calls[0]["since"] == SINCE
    assert source.calls[0]["until"] == UNTIL
    assert source.calls[0]["since"].tzinfo is LOCAL_TZ
    assert source.calls[0]["until"].tzinfo is LOCAL_TZ
    parameters = inspect.signature(orch.run).parameters
    assert parameters["day"].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert parameters["sources"].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters["notify"].kind is inspect.Parameter.KEYWORD_ONLY
    with pytest.raises(TypeError):
        orch.run(DAY, [source])


def test_push_failure_still_saved_reports(monkeypatch) -> None:
    import smart_daily_v2.orchestrator as orch

    items = [_item("rec-501-006", "甲"), _item("rec-501-007", "乙")]
    source = _source("source-placeholder", items)
    persist_calls = []
    _patch_persist(monkeypatch, orch, persist_calls)
    _patch_dispatch(monkeypatch, orch, {"personal:甲": False, "team": True})

    result = orch.run(DAY, sources=[source])

    assert result["saved_reports"] == 2
    assert len(persist_calls) == 2


def test_pushed_comes_from_all_delivered_not_any(monkeypatch) -> None:
    import smart_daily_v2.orchestrator as orch

    source = _source("source-placeholder", [_item("rec-501-008", "甲")])
    _patch_persist(monkeypatch, orch, [])
    _patch_dispatch(monkeypatch, orch, {"personal:甲": True, "team": False})

    result = orch.run(DAY, sources=[source])

    assert result["pushed"] is False
    assert result["push_status"] == "partial"
    source_text = Path(orch.__file__).read_text(encoding="utf-8")
    pushed_assignments = [
        line for line in source_text.splitlines() if "pushed" in line and "=" in line
    ]
    assert pushed_assignments
    assert all("any(" not in line for line in pushed_assignments)


def test_all_sources_unavailable_raises_no_empty_report(monkeypatch) -> None:
    import smart_daily_v2.orchestrator as orch

    source = _source(
        "source-placeholder",
        [],
        raises=SourceUnavailableError("source-placeholder", "placeholder failure"),
    )
    persist_calls = []
    _patch_persist(monkeypatch, orch, persist_calls)
    dispatch_calls = _patch_dispatch(monkeypatch, orch, {})

    with pytest.raises(AllSourcesUnavailableError):
        orch.run(DAY, sources=[source])

    assert persist_calls == []
    assert dispatch_calls == []


def test_push_status_ok_when_all_channels_succeed(monkeypatch) -> None:
    import smart_daily_v2.orchestrator as orch

    source = _source("source-placeholder", [_item("rec-501-009", "甲"), _item("rec-501-010", "乙")])
    _patch_persist(monkeypatch, orch, [])
    _patch_dispatch(
        monkeypatch,
        orch,
        {"personal:甲": True, "personal:乙": True, "team": True},
    )

    result = orch.run(DAY, sources=[source])

    assert result["push_status"] == "ok"
    assert result["pushed"] is True
    assert len(result["push_detail"]) == 3
    assert all(detail["ok"] is True for detail in result["push_detail"])
    assert result["pushed"] == (result["push_status"] == "ok")


def test_push_status_partial_and_failed(monkeypatch) -> None:
    import smart_daily_v2.orchestrator as orch

    source = _source("source-placeholder", [_item("rec-501-011", "甲")])
    _patch_persist(monkeypatch, orch, [])
    _patch_dispatch(monkeypatch, orch, {"personal:甲": True, "team": False})

    partial = orch.run(DAY, sources=[source])

    assert partial["push_status"] == "partial"
    assert partial["pushed"] is False

    _patch_dispatch(monkeypatch, orch, {"personal:甲": False, "team": False})

    failed = orch.run(DAY, sources=[source])

    assert failed["push_status"] == "failed"
    assert failed["pushed"] is False


def test_notify_false_skipped_and_no_channel_not_success(monkeypatch) -> None:
    import smart_daily_v2.orchestrator as orch

    source = _source("source-placeholder", [_item("rec-501-012", "甲")])
    _patch_persist(monkeypatch, orch, [])
    dispatch_calls = _patch_dispatch(monkeypatch, orch, {})

    skipped = orch.run(DAY, sources=[source], notify=False)

    assert skipped["push_status"] == "skipped"
    assert skipped["pushed"] is False
    assert dispatch_calls == []

    _patch_dispatch(monkeypatch, orch, {})

    no_channel = orch.run(DAY, sources=[source], notify=True)

    assert no_channel["push_status"] == "no_channel"
    assert no_channel["pushed"] is False


def test_signature_and_protocol_contract(monkeypatch) -> None:
    import smart_daily_v2.orchestrator as orch

    assert callable(orch.run)
    parameters = inspect.signature(orch.run).parameters
    assert parameters["day"].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert parameters["sources"].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters["notify"].kind is inspect.Parameter.KEYWORD_ONLY
    source = _source("source-placeholder", [])
    _patch_persist(monkeypatch, orch, [])
    _patch_dispatch(monkeypatch, orch, {})

    result = orch.run(DAY, sources=[source], notify=False)

    assert isinstance(result, dict)
    assert set(result) == EXPECTED_KEYS
    assert isinstance(source, WorkSource)


def test_scope_registration_docstring_and_no_v1_copy(monkeypatch) -> None:
    import smart_daily_v2.orchestrator as orch

    source = Path(orch.__file__).read_text(encoding="utf-8")

    for forbidden in (
        "sqlite3",
        "storage",
        "save_report",
        "lookup_display_name",
        "from smart_daily import",
        "ghp_",
        "@qq.com",
        "@gmail.com",
        "https://open.feishu.cn",
    ):
        assert forbidden not in source
    for anchor in ("待确认", "RawRecord", "归一化单点"):
        assert anchor in source
    assert "已裁定" not in source
    for registration in ("K2", "502", "S5", "G7", "local_date"):
        assert registration in source
