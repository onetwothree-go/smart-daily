import inspect
from datetime import datetime
from pathlib import Path

import pytest

from smart_daily_v2.models import LOCAL_TZ, WorkItem, local_date
from smart_daily_v2.sources.base import (
    AllSourcesUnavailableError,
    SourceUnavailableError,
)

SINCE = datetime(2026, 11, 18, 0, 0, tzinfo=LOCAL_TZ)
UNTIL = datetime(2026, 11, 18, 23, 59, tzinfo=LOCAL_TZ)


class _FakeSource:
    def __init__(self, name, *, result=None, error=None):
        self.name = name
        self.result = result
        self.error = error
        self.calls = []

    def collect(self, *, since, until, author=None):
        self.calls.append((since, until, author))
        if self.error is not None:
            raise self.error
        return [] if self.result is None else self.result


def _make_items(n, prefix="104"):
    items = []
    members = ("甲", "乙", "丙", "丁")
    for index in range(1, n + 1):
        occurred_at = datetime(2026, 11, 18, 9, index, tzinfo=LOCAL_TZ)
        items.append(
            WorkItem(
                record_id=f"{prefix}-{index:03d}",
                source="source-two",
                member=members[(index - 1) % len(members)],
                kind="commit",
                title=f"示例工作条目 {index}",
                detail="示例详情",
                occurred_at=occurred_at,
                local_day=local_date(occurred_at),
            )
        )
    return items


def test_exception_source_falls_back_to_next():
    import smart_daily_v2.sources.fallback as fb

    first = _FakeSource(
        "source-one",
        error=SourceUnavailableError("source-one", "first reason"),
    )
    second = _FakeSource("source-two", result=_make_items(3))
    third = _FakeSource("source-three", result=_make_items(1, "third"))

    items, reasons = fb.collect_with_fallback([first, second, third], since=SINCE, until=UNTIL)

    assert len(items) == 3
    assert all(isinstance(item, WorkItem) for item in items)
    assert len(reasons) == 1
    assert "source-one" in reasons[0]
    assert "first reason" in reasons[0]
    assert len(second.calls) == 1
    assert third.calls == []


def test_empty_first_source_stops_without_switching():
    import smart_daily_v2.sources.fallback as fb

    first = _FakeSource("source-one", result=[])
    second = _FakeSource("source-two", result=_make_items(3))

    items, reasons = fb.collect_with_fallback([first, second], since=SINCE, until=UNTIL)

    assert items == []
    assert reasons == ["source-one"]
    assert len(first.calls) == 1
    assert second.calls == []


def test_all_sources_fail_raises():
    import smart_daily_v2.sources.fallback as fb

    sources = [
        _FakeSource(
            "source-one",
            error=SourceUnavailableError("source-one", "first reason"),
        ),
        _FakeSource(
            "source-two",
            error=SourceUnavailableError("source-two", "second reason"),
        ),
        _FakeSource(
            "source-three",
            error=SourceUnavailableError("source-three", "third reason"),
        ),
    ]

    with pytest.raises(AllSourcesUnavailableError) as exc:
        fb.collect_with_fallback(sources, since=SINCE, until=UNTIL)

    message = str(exc.value)
    for source, reason in (
        ("source-one", "first reason"),
        ("source-two", "second reason"),
        ("source-three", "third reason"),
    ):
        assert source in message
        assert reason in message
    assert len(exc.value.errors) == 3


def test_normalize_called_exactly_once(monkeypatch):
    import smart_daily_v2.sources.fallback as fb

    expected_items = _make_items(3)
    source = _FakeSource("source-one", result=expected_items)
    original_normalize = fb.normalize
    calls = []

    def normalize_spy(entries):
        calls.append(entries)
        return original_normalize(entries)

    monkeypatch.setattr(fb, "normalize", normalize_spy)

    items, _ = fb.collect_with_fallback([source], since=SINCE, until=UNTIL)

    assert len(calls) == 1
    assert all(isinstance(item, WorkItem) for item in items)
    assert [item.record_id for item in items] == [item.record_id for item in expected_items]


def test_no_fallback_returns_empty_reasons():
    import smart_daily_v2.sources.fallback as fb

    expected_items = _make_items(3)
    source = _FakeSource("source-one", result=expected_items)

    items, reasons = fb.collect_with_fallback([source], since=SINCE, until=UNTIL)

    assert len(items) == 3
    assert reasons == []


def test_all_sources_error_not_swallowed_as_single_failure():
    import smart_daily_v2.sources.fallback as fb

    nested_error = AllSourcesUnavailableError([SourceUnavailableError("source-one", "nested")])
    first = _FakeSource("source-one", error=nested_error)
    second = _FakeSource("source-two", result=_make_items(3))

    with pytest.raises(AllSourcesUnavailableError):
        fb.collect_with_fallback([first, second], since=SINCE, until=UNTIL)

    assert second.calls == []


def test_since_until_are_keyword_only():
    import smart_daily_v2.sources.fallback as fb

    parameters = inspect.signature(fb.collect_with_fallback).parameters

    assert parameters["since"].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters["until"].kind is inspect.Parameter.KEYWORD_ONLY
    with pytest.raises(TypeError):
        fb.collect_with_fallback([_FakeSource("source-one")], SINCE, UNTIL)


def test_params_forwarded_verbatim_to_each_source():
    import smart_daily_v2.sources.fallback as fb

    first = _FakeSource(
        "source-one",
        error=SourceUnavailableError("source-one", "first reason"),
    )
    second = _FakeSource("source-two", result=_make_items(3))

    fb.collect_with_fallback([first, second], since=SINCE, until=UNTIL, author="甲")

    assert first.calls == [(SINCE, UNTIL, "甲")]
    assert second.calls == [(SINCE, UNTIL, "甲")]


def test_multiple_fallbacks_accumulate_reasons_in_order():
    import smart_daily_v2.sources.fallback as fb

    first = _FakeSource(
        "source-one",
        error=SourceUnavailableError("source-one", "first reason"),
    )
    second = _FakeSource(
        "source-two",
        error=SourceUnavailableError("source-two", "second reason"),
    )
    third = _FakeSource("source-three", result=_make_items(2))

    items, reasons = fb.collect_with_fallback([first, second, third], since=SINCE, until=UNTIL)

    assert len(items) == 2
    assert len(reasons) == 2
    assert "source-one" in reasons[0]
    assert "source-two" in reasons[1]
    assert all("source-three" not in reason for reason in reasons)

    empty_source = _FakeSource("source-one", result=[])
    later_error = _FakeSource(
        "source-two",
        error=SourceUnavailableError("source-two", "second reason"),
    )
    empty_items, empty_reasons = fb.collect_with_fallback(
        [empty_source, later_error], since=SINCE, until=UNTIL
    )

    assert empty_items == []
    assert empty_reasons == ["source-one"]
    assert later_error.calls == []


def test_scope_registration_static_assertions():
    import smart_daily_v2.sources.fallback as fb

    source = Path(fb.__file__).read_text(encoding="utf-8")

    assert "待确认" in source
    assert "停止点" in source
    assert "降级原因" in source
    assert source.index("except AllSourcesUnavailableError") < source.index(
        "except SourceUnavailableError"
    )
    assert "from smart_daily_v2.models import normalize" in source
