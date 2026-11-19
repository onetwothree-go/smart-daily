import pytest

import smart_daily_v2.notifiers.dispatch as dispatch_module
from smart_daily_v2.notifiers.dispatch import all_delivered, dispatch


class FakeChannel:
    def __init__(self, outcome=True):
        self.calls = []
        self.outcome = outcome

    def __call__(self, *args):
        self.calls.append(args)
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


@pytest.fixture
def channels(monkeypatch):
    personal = FakeChannel()
    team_group = FakeChannel()
    team_external = FakeChannel()
    monkeypatch.setattr(dispatch_module, "_send_personal", personal)
    monkeypatch.setattr(dispatch_module, "_send_team_group", team_group)
    monkeypatch.setattr(dispatch_module, "_send_team_external", team_external)
    return {
        "personal": personal,
        "team_group": team_group,
        "team_external": team_external,
    }


def test_dispatch_six_channels_and_scopes(channels):
    personal = {
        "member-1": "个人日报：PERSONAL_ONE",
        "member-2": "个人日报：PERSONAL_TWO",
        "member-3": "个人日报：PERSONAL_THREE",
        "member-4": "个人日报：PERSONAL_FOUR",
    }

    results = dispatch(
        personal,
        "团队日报：TEAM_REPORT",
        team_recipients=["ext@example.com"],
    )

    assert set(results) == {
        "personal:member-1",
        "personal:member-2",
        "personal:member-3",
        "personal:member-4",
        "team",
        "team:report_recipients",
    }
    assert len(channels["personal"].calls) == 4
    assert len(channels["team_group"].calls) == 1
    assert len(channels["team_external"].calls) == 1
    team_body = channels["team_group"].calls[0][0]
    assert "团队日报" in team_body
    assert all(body not in team_body for body in personal.values())


def test_team_two_channels_independent_try(channels):
    channels["team_group"].outcome = RuntimeError("team group failed")

    results = dispatch(
        {},
        "团队日报：TEAM_REPORT",
        team_recipients=["ext@example.com"],
    )

    assert results["team"] is False
    assert results["team:report_recipients"] is True
    assert len(channels["team_external"].calls) == 1


def test_no_notify_calls_zero_channels(channels):
    results = dispatch(
        {"member-1": "个人日报：PERSONAL_ONE"},
        "团队日报：TEAM_REPORT",
        no_notify=True,
        team_recipients=["ext@example.com"],
    )

    assert results == {}
    assert sum(len(fake.calls) for fake in channels.values()) == 0


def test_no_external_recipients_falls_back_to_five(channels):
    personal = {
        "member-1": "个人日报：PERSONAL_ONE",
        "member-2": "个人日报：PERSONAL_TWO",
        "member-3": "个人日报：PERSONAL_THREE",
        "member-4": "个人日报：PERSONAL_FOUR",
    }

    results = dispatch(personal, "团队日报：TEAM_REPORT")

    assert "team:report_recipients" not in results
    assert len(results) == len(personal) + 1 == 5
    assert len(channels["team_external"].calls) == 0
    assert all_delivered(set(results), results) is True


def test_all_delivered_partial_is_false():
    expected = {
        "personal:member-1",
        "personal:member-2",
        "personal:member-3",
        "personal:member-4",
        "team",
        "team:report_recipients",
    }
    results = {
        "personal:member-1": True,
        "personal:member-2": True,
        "personal:member-3": True,
        "personal:member-4": False,
        "team": False,
        "team:report_recipients": False,
    }

    assert all_delivered(expected, results) is False


def test_all_delivered_all_true_is_true():
    expected = {
        "personal:member-1",
        "personal:member-2",
        "personal:member-3",
        "personal:member-4",
        "team",
        "team:report_recipients",
    }
    results = {scope: True for scope in expected}

    assert all_delivered(expected, results) is True


def test_all_delivered_empty_expected_is_false():
    assert all_delivered(set(), {}) is False


def test_all_delivered_missing_scope_is_false():
    expected = {"personal:member-1", "team"}
    results = {"personal:member-1": True}

    assert all_delivered(expected, results) is False
