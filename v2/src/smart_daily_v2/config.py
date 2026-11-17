import os
from collections.abc import Mapping
from dataclasses import dataclass, fields


@dataclass(frozen=True)
class Config:
    github_token: str
    github_repo_owner: str
    github_repo_name: str
    github_api: str
    github_branch: str
    feishu_app_id: str
    feishu_app_secret: str
    feishu_chat_id: str
    feishu_api: str
    feishu_webhook_url: str
    feishu_webhook_secret: str
    smtp_host: str
    smtp_port: str
    smtp_user: str
    smtp_password: str
    smtp_sender: str
    smtp_ssl: str
    member_emails: str
    member_display_names: str
    daily_cutoff: str
    db_path: str


def load_config(env: Mapping[str, str] | None = None) -> Config:
    environment = os.environ if env is None else env
    config_values = {
        field.name: environment.get(field.name.upper(), "") for field in fields(Config)
    }
    return Config(**config_values)


def require_credential(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ValueError(f"Missing required credential: {name}")
    return value
