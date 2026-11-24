from smart_daily_v2.notifiers.members import load_member_emails, load_report_recipients


def test_load_member_emails_parses_recipients():
    env = {"MEMBER_EMAILS": "甲:a@example.com;b@example.com"}

    assert load_member_emails(env) == {"甲": ["a@example.com", "b@example.com"]}


def test_load_member_emails_multiple_members():
    env = {"MEMBER_EMAILS": "甲:a@example.com,乙:c@example.com"}

    assert load_member_emails(env) == {
        "甲": ["a@example.com"],
        "乙": ["c@example.com"],
    }


def test_load_member_emails_unset_returns_empty():
    assert load_member_emails({}) == {}


def test_load_member_emails_skips_blank_member_name():
    """覆盖率补缺口（第 4 周 / #20）：members.py 空成员名分段须跳过（含全空格名）。"""
    env = {"MEMBER_EMAILS": ":orphan@example.com,   :also-orphan@example.com,乙:c@example.com"}
    assert load_member_emails(env) == {"乙": ["c@example.com"]}


def test_load_report_recipients_strips_whitespace():
    env = {"REPORT_RECIPIENTS": "a@x.com, b@x.com"}

    assert load_report_recipients(env) == ["a@x.com", "b@x.com"]


def test_load_report_recipients_unset_returns_empty():
    assert load_report_recipients({}) == []


def test_two_variables_are_isolated():
    assert load_member_emails({"REPORT_RECIPIENTS": "a@x.com"}) == {}
    assert load_report_recipients({"MEMBER_EMAILS": "甲:a@example.com"}) == []
