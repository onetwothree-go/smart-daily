import importlib
from collections.abc import Mapping

import httpx
import pytest

CONFIG_ENV = {
    "GITHUB_TOKEN": "placeholder-token",
    "GITHUB_REPO_OWNER": "example-owner",
    "GITHUB_REPO_NAME": "example-repo",
    "GITHUB_API": "https://example.com/github-api",
    "GITHUB_BRANCH": "example-branch",
    "FEISHU_APP_ID": "placeholder-app-id",
    "FEISHU_APP_SECRET": "placeholder-app-secret",
    "FEISHU_CHAT_ID": "placeholder-chat-id",
    "FEISHU_API": "https://example.com/feishu-api",
    "FEISHU_WEBHOOK_URL": "https://example.com/webhook",
    "FEISHU_WEBHOOK_SECRET": "placeholder-webhook-secret",
    "SMTP_HOST": "smtp.example.com",
    "SMTP_PORT": "587",
    "SMTP_USER": "user@example.com",
    "SMTP_PASSWORD": "placeholder-password",
    "SMTP_SENDER": "sender@example.com",
    "SMTP_SSL": "false",
    "MEMBER_EMAILS": "member:user@example.com",
    "MEMBER_DISPLAY_NAMES": "example-login:Example Member",
    "DAILY_CUTOFF": "22:00",
    "DB_PATH": "./data/example.db",
}


def _config_module():
    try:
        config = importlib.import_module("smart_daily_v2.config")
    except ModuleNotFoundError:
        pytest.fail("smart_daily_v2.config module does not exist", pytrace=False)
    return config


def _http_calls(monkeypatch):
    calls = []
    monkeypatch.setattr(httpx.Client, "request", lambda *args, **kwargs: calls.append(args))
    monkeypatch.setattr(httpx, "request", lambda *args, **kwargs: calls.append(args))
    return calls


def test_missing_github_token_raises_without_http_request(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    calls = _http_calls(monkeypatch)
    config = _config_module()

    with pytest.raises(ValueError, match="GITHUB_TOKEN"):
        config.require_credential("GITHUB_TOKEN")

    assert calls == []


def test_missing_smtp_credential_raises_value_error(monkeypatch):
    monkeypatch.delenv("SMTP_PASSWORD", raising=False)
    config = _config_module()

    with pytest.raises(ValueError, match="SMTP_PASSWORD"):
        config.require_credential("SMTP_PASSWORD")


def test_env_example_lists_all_variables_as_placeholders():
    from pathlib import Path

    env_example = Path(__file__).parents[1] / ".env.example"
    contents = env_example.read_text()

    assert set(CONFIG_ENV).issubset(
        {line.split("=", maxsplit=1)[0] for line in contents.splitlines() if "=" in line}
    )
    assert "user@example.com" in contents
    assert "sender@example.com" in contents
    assert "member:user@example.com" in contents


def test_env_file_is_ignored_by_git():
    import subprocess
    from pathlib import Path

    repo_root = Path(__file__).parents[2]
    result = subprocess.run(
        ["git", "check-ignore", "-v", "v2/.env"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )

    assert ".env" in result.stdout


def test_load_config_maps_environment_variables():
    config = _config_module()
    env: Mapping[str, str] = CONFIG_ENV

    result = config.load_config(env)

    assert {key.lower(): getattr(result, key.lower()) for key in CONFIG_ENV} == {
        key.lower(): value for key, value in CONFIG_ENV.items()
    }
