import inspect
from unittest.mock import MagicMock

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


def test_member_without_email_still_records_false_receipt_and_fails_delivery(monkeypatch):
    """DEF-05 / issue #19：无邮箱成员必须仍产生 ok=False 回执记录，整体不得判成功。

    按 `赵蕊-缺陷清单与根因记录.md` DEF-05 验证方式原文：
    「构造 1 个无邮箱成员 → 断言其仍有记录且 ok=False, error="no_recipient"，
    且整体 push_status != "ok"」。
    丁在 MEMBER_EMAILS 中被故意缺席，其余 3 邮件 + 群 + 教师邮箱通道全发成功。
    """
    import smart_daily_v2.notifiers.dispatch as dispatch_module
    import smart_daily_v2.orchestrator as orch

    monkeypatch.setenv("MEMBER_EMAILS", "甲:a@example.com,乙:b@example.com,丙:c@example.com")
    monkeypatch.setenv("REPORT_RECIPIENTS", "teacher@example.com")

    fake_notifier = MagicMock()
    fake_notifier.send.return_value = True
    monkeypatch.setattr(dispatch_module.EmailNotifier, "from_env", lambda: fake_notifier)
    monkeypatch.setattr(dispatch_module.FeishuWebhookNotifier, "from_env", lambda: fake_notifier)
    monkeypatch.setattr(orch, "_persist_report", lambda *args, **kwargs: None)

    class MockOnlySource:
        name = "mock"

        def collect(self, *, since, until, author=None):
            return load_fixture_items()

    items = load_fixture_items()
    day = items[0].local_day
    result = orch.run(day, sources=[MockOnlySource()])

    details = {d["scope"]: d for d in result["push_detail"]}

    # ① 无邮箱成员（丁）必须仍有回执记录，而不是根本没有记录
    assert "personal:丁" in details, "无邮箱成员没有产生回执记录（DEF-05 分母缺失）"
    assert details["personal:丁"]["ok"] is False

    # ② DEF-05 官方口径：缺收件人的记录必须带 error="no_recipient" 标记
    assert details["personal:丁"]["error"] == "no_recipient", (
        f"无邮箱成员回执缺 no_recipient 标记，实际 error={details['personal:丁']['error']!r}"
    )

    # ③ 分母完整：4 名成员 + 团队群 + 教师邮箱全部进 push_detail
    assert set(details) == set(SCOPES)

    # ④ 整体不得判成功
    assert result["pushed"] is False
    assert result["push_status"] == "partial"
