import base64
import hashlib
import hmac

import httpx
import pytest

from smart_daily_v2.notifiers.webhook import FeishuWebhookNotifier, gen_sign


class FakeResponse:
    def __init__(self, code=0, msg="ok"):
        self.status_code = 200
        self._data = {"code": code, "msg": msg}
        self.text = str(self._data)

    def json(self):
        return self._data


def _stub_http_post(monkeypatch, *, code=0, error=None):
    calls = []

    def fake_post(url, *, json, timeout):
        calls.append({"url": url, "payload": json, "timeout": timeout})
        if error is not None:
            raise error
        return FakeResponse(code=code)

    monkeypatch.setattr("smart_daily_v2.notifiers.webhook.httpx.post", fake_post)
    return calls


def test_gen_sign_matches_reference_and_deterministic():
    ts = 1700000000
    secret = "test-secret"
    string_to_sign = f"{ts}\n{secret}"
    expected = base64.b64encode(
        hmac.new(
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
    ).decode("utf-8")

    actual = gen_sign(ts, secret)

    assert actual == expected
    assert gen_sign(ts, secret) == actual
    assert actual
    assert base64.b64decode(actual, validate=True)


def test_from_env_missing_url_raises_value_error(monkeypatch):
    calls = _stub_http_post(monkeypatch)

    with pytest.raises(ValueError):
        FeishuWebhookNotifier.from_env({"FEISHU_WEBHOOK_SECRET": "test-secret"})

    assert calls == []


def test_from_env_full_builds_notifier_without_http(monkeypatch):
    calls = _stub_http_post(monkeypatch)

    notifier = FeishuWebhookNotifier.from_env(
        {
            "FEISHU_WEBHOOK_URL": "https://example.com/webhook",
            "FEISHU_WEBHOOK_SECRET": "test-secret",
        }
    )

    assert notifier.webhook_url == "https://example.com/webhook"
    assert notifier.secret == "test-secret"
    assert calls == []


def test_send_rejects_text_without_keyword_no_http(monkeypatch):
    calls = _stub_http_post(monkeypatch)
    notifier = FeishuWebhookNotifier.from_env(
        {
            "FEISHU_WEBHOOK_URL": "https://example.com/webhook",
            "FEISHU_WEBHOOK_SECRET": "test-secret",
        }
    )

    assert notifier.send("普通通知", "内容与工作无关的纯文本", []) is False
    assert len(calls) == 0


def test_send_success_returns_true_with_sign_and_keyword(monkeypatch):
    calls = _stub_http_post(monkeypatch, code=0)
    notifier = FeishuWebhookNotifier.from_env(
        {
            "FEISHU_WEBHOOK_URL": "https://example.com/webhook",
            "FEISHU_WEBHOOK_SECRET": "test-secret",
        }
    )

    assert notifier.send("团队日报 2026-11-18", "正文", []) is True

    assert len(calls) == 1
    payload = calls[0]["payload"]
    assert payload["msg_type"] == "text"
    assert "日报" in payload["content"]["text"]
    assert "timestamp" in payload
    assert "sign" in payload
    assert payload["sign"] == gen_sign(int(payload["timestamp"]), "test-secret")


@pytest.mark.parametrize("code", (19021, 19022, 19024))
def test_send_error_codes_return_false(monkeypatch, capsys, code):
    calls = _stub_http_post(monkeypatch, code=code)
    notifier = FeishuWebhookNotifier.from_env(
        {
            "FEISHU_WEBHOOK_URL": "https://example.com/webhook",
            "FEISHU_WEBHOOK_SECRET": "test-secret",
        }
    )

    assert notifier.send("团队日报 2026-11-18", "正文", []) is False
    output = capsys.readouterr()
    assert str(code) in output.out + output.err
    assert len(calls) == 1


def test_send_http_error_returns_false(monkeypatch):
    calls = _stub_http_post(monkeypatch, error=httpx.HTTPError("network failed"))
    notifier = FeishuWebhookNotifier.from_env(
        {
            "FEISHU_WEBHOOK_URL": "https://example.com/webhook",
            "FEISHU_WEBHOOK_SECRET": "test-secret",
        }
    )

    assert notifier.send("团队日报 2026-11-18", "正文", []) is False
    assert len(calls) == 1
