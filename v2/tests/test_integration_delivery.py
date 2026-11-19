import inspect

import pytest

import smart_daily_v2.notifiers.dispatch as dispatch_module
from smart_daily_v2.notifiers.dispatch import all_delivered
from smart_daily_v2.sources.mock import load_fixture_items

SCOPES = (
    "personal:甲",
    "personal:乙",
    "personal:丙",
    "personal:丁",
    "team",
    "team:report_recipients",
)


@pytest.mark.parametrize("scope", SCOPES)
def test_any_single_false_is_not_delivered(delivery_harness, scope):
    outcome = delivery_harness({scope: False})

    assert outcome.pushed is False


def test_six_channels_all_true_is_delivered(delivery_harness):
    outcome = delivery_harness()

    assert set(outcome.results) == set(SCOPES)
    assert all(outcome.results.values())
    assert outcome.pushed is True
    assert len(outcome.calls["personal"]) == 4
    assert len(outcome.calls["team"]) == 1
    assert len(outcome.calls["external"]) == 1


def test_three_of_six_true_is_not_delivered(delivery_harness):
    outcome = delivery_harness({scope: False for scope in SCOPES[:3]})

    assert sum(outcome.results.values()) == 3
    assert outcome.pushed is False


def test_expected_set_is_exactly_six_scopes(delivery_harness):
    outcome = delivery_harness()
    personal_members = {
        scope.removeprefix("personal:")
        for scope in outcome.expected
        if scope.startswith("personal:")
    }

    assert outcome.expected == set(SCOPES)
    assert all(
        "realtime" not in scope and "push" not in scope and "notify_push" not in scope
        for scope in outcome.expected
    )
    assert set(outcome.results) == outcome.expected
    assert personal_members == outcome.members


def test_no_external_recipients_falls_back_to_five_not_failed(delivery_harness):
    outcome = delivery_harness(with_external=False)

    assert len(outcome.results) == 5
    assert "team:report_recipients" not in outcome.results
    assert len(outcome.calls["external"]) == 0
    assert outcome.pushed is True


def test_no_notify_has_no_receipts_and_pushed_false(delivery_harness):
    outcome = delivery_harness(no_notify=True)

    assert outcome.results == {}
    assert outcome.expected == set()
    assert outcome.pushed is False
    assert all(len(calls) == 0 for calls in outcome.calls.values())


def test_channel_exception_records_false_receipt(delivery_harness):
    outcome = delivery_harness({"team": RuntimeError("boom")})

    assert outcome.results["team"] is False
    assert len(outcome.results) == 6
    assert all(outcome.results[scope] is True for scope in SCOPES if scope != "team")
    assert outcome.pushed is False


def test_pushed_derives_from_all_delivered_without_any_builtin(delivery_harness):
    dispatch_source = inspect.getsource(dispatch_module)
    delivery_source = inspect.getsource(dispatch_module.all_delivered)
    first = delivery_harness()
    first_record_ids = tuple(item.record_id for item in load_fixture_items())
    second = delivery_harness()
    second_record_ids = tuple(item.record_id for item in load_fixture_items())

    assert "all(" in delivery_source
    assert "a" + "ny(" not in dispatch_source
    assert first.pushed == all_delivered(first.expected, first.results)
    assert second.pushed == all_delivered(second.expected, second.results)
    assert first_record_ids == second_record_ids
