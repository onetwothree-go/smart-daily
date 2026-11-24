from datetime import date, datetime, time
from pathlib import Path

import smart_daily_v2.orchestrator as orch
from smart_daily_v2.models import LOCAL_TZ, WorkItem, local_date

DAY = date(2026, 11, 19)
MEMBERS = ("甲", "乙", "丙", "丁")


def _item(record_id: str, member: str) -> WorkItem:
    occurred_at = datetime.combine(DAY, time(9), tzinfo=LOCAL_TZ)
    return WorkItem(
        record_id=record_id,
        source="github",
        member=member,
        kind="commit",
        title=f"t-{record_id}",
        detail="",
        occurred_at=occurred_at,
        local_day=local_date(occurred_at),
    )


def _source(items: list[WorkItem]):
    class FakeSource:
        name = "def05-test-source"

        def collect(self, *, since, until, author=None):
            return items

    return FakeSource()


def _setup(monkeypatch, results: dict[str, bool], *, recipients=None):
    items = [_item(f"def05-{index}", member) for index, member in enumerate(MEMBERS)]
    monkeypatch.setattr(orch, "_persist_report", lambda *args: None)
    monkeypatch.setattr(orch, "dispatch", lambda *args, **kwargs: results.copy())
    if recipients is not None:
        monkeypatch.setattr(orch, "load_report_recipients", lambda: recipients)
    return _source(items)


def test_def05_missing_receipt_counts_as_failure(monkeypatch):
    results = {
        "personal:甲": True,
        "personal:乙": True,
        "personal:丙": True,
        "team": True,
        "team:report_recipients": True,
    }
    source = _setup(
        monkeypatch,
        results,
        recipients=["teacher@example.invalid"],
    )

    result = orch.run(DAY, sources=[source])

    assert result["pushed"] is False
    assert result["push_status"] == "partial"


def test_def05_expected_independent_of_results(monkeypatch):
    source_text = Path(orch.__file__).read_text(encoding="utf-8")
    from_receipts = "expected = set(" + "results)"
    results = {f"personal:{member}": True for member in MEMBERS}
    results["team"] = True
    source = _setup(monkeypatch, results, recipients=[])

    orch.run(DAY, sources=[source])

    assert from_receipts not in source_text


def test_def05_no_external_recipient_is_five(monkeypatch):
    results = {f"personal:{member}": True for member in MEMBERS}
    results["team"] = True
    source = _setup(monkeypatch, results, recipients=[])

    result = orch.run(DAY, sources=[source])

    assert result["pushed"] is True


def test_def05_missing_scope_in_push_detail(monkeypatch):
    results = {
        "personal:甲": True,
        "personal:乙": True,
        "personal:丙": True,
        "team": True,
        "team:report_recipients": True,
    }
    source = _setup(
        monkeypatch,
        results,
        recipients=["teacher@example.invalid"],
    )

    result = orch.run(DAY, sources=[source])

    missing_scope = next(
        detail for detail in result["push_detail"] if detail["scope"] == "personal:丁"
    )
    assert missing_scope["ok"] is False


def test_def05_no_any_in_delivery_path(monkeypatch):
    source_text = Path(orch.__file__).read_text(encoding="utf-8")
    results = {f"personal:{member}": True for member in MEMBERS}
    results["team"] = True
    source = _setup(monkeypatch, results, recipients=[])

    orch.run(DAY, sources=[source])

    any_call = "a" + "ny("
    delivery_path = source_text[
        source_text.index("expected =") : source_text.index("if not notify:")
    ]
    assert any_call not in delivery_path
