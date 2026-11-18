import smtplib

import pytest

import smart_daily_v2.notifiers.email as email_module
from smart_daily_v2.notifiers.email import EmailNotifier


@pytest.fixture
def fake_smtp(monkeypatch):
    class FakeSMTP:
        constructions = 0
        sent_messages = []
        login_error = None

        def __init__(self, host, port):
            type(self).constructions += 1
            self.host = host
            self.port = port

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def login(self, user, password):
            if type(self).login_error is not None:
                raise type(self).login_error

        def send_message(self, message):
            type(self).sent_messages.append(message)

    monkeypatch.setattr(email_module.smtplib, "SMTP", FakeSMTP)
    return FakeSMTP


def smtp_env(**overrides):
    env = {
        "SMTP_HOST": "smtp.example.com",
        "SMTP_PORT": "587",
        "SMTP_USER": "user@example.com",
        "SMTP_PASSWORD": "replace-me",
        "SMTP_SENDER": "sender@example.com",
        "SMTP_SSL": "false",
    }
    env.update(overrides)
    return env


@pytest.mark.parametrize("missing", ["SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD"])
def test_from_env_missing_credential_raises_value_error(missing, fake_smtp):
    env = smtp_env()
    del env[missing]

    with pytest.raises(ValueError):
        EmailNotifier.from_env(env)

    assert fake_smtp.constructions == 0


def test_from_env_full_builds_notifier(fake_smtp):
    notifier = EmailNotifier.from_env(smtp_env())

    assert isinstance(notifier, EmailNotifier)
    assert notifier.host == "smtp.example.com"
    assert notifier.port == 587
    assert notifier.user == "user@example.com"
    assert notifier.password == "replace-me"
    assert notifier.sender == "sender@example.com"
    assert notifier.use_ssl is False
    assert fake_smtp.constructions == 0


def test_send_success_returns_true_and_delivers_exact(fake_smtp):
    notifier = EmailNotifier.from_env(smtp_env())

    assert notifier.send("日报 A", "正文-A", ["a@example.com"]) is True

    assert len(fake_smtp.sent_messages) == 1
    message = fake_smtp.sent_messages[0]
    assert message["To"] == "a@example.com"
    assert "正文-A" in message.get_content()
    assert "日报" in message["Subject"]


def test_four_members_each_only_own_report(fake_smtp):
    notifier = EmailNotifier.from_env(smtp_env())
    members = [
        ("a@example.com", "成员标记-A"),
        ("b@example.com", "成员标记-B"),
        ("c@example.com", "成员标记-C"),
        ("d@example.com", "成员标记-D"),
    ]

    for recipient, marker in members:
        assert notifier.send("日报", f"本人正文 {marker}", [recipient]) is True

    assert len(fake_smtp.sent_messages) == 4
    for message, (recipient, own_marker) in zip(fake_smtp.sent_messages, members, strict=True):
        body = message.get_content()
        assert message["To"] == recipient
        assert own_marker in body
        assert all(
            other_marker not in body for _, other_marker in members if other_marker != own_marker
        )


@pytest.mark.parametrize(
    "error",
    [
        smtplib.SMTPAuthenticationError(535, b"authentication failed"),
        TimeoutError("connection timed out"),
        OSError("connection failed"),
    ],
)
def test_send_failures_return_false_without_raising(error, fake_smtp, caplog):
    fake_smtp.login_error = error
    notifier = EmailNotifier.from_env(smtp_env())

    assert notifier.send("日报", "正文", ["a@example.com"]) is False

    assert str(error) in caplog.text


def test_failure_does_not_retry(fake_smtp):
    fake_smtp.login_error = OSError("connection failed")
    notifier = EmailNotifier.from_env(smtp_env())

    assert notifier.send("日报", "正文", ["a@example.com"]) is False

    assert fake_smtp.constructions == 1
