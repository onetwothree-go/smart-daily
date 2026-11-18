import json
import os
from pathlib import Path

import pytest


@pytest.fixture
def cleared_env(monkeypatch: pytest.MonkeyPatch) -> None:
    prefixes = ("GITHUB_", "FEISHU_", "SMTP_", "DAILY_", "DB_")
    names = {"MEMBER_EMAILS", "REPORT_RECIPIENTS", "MEMBER_DISPLAY_NAMES"}
    for key in list(os.environ):
        if key.startswith(prefixes) or key in names:
            monkeypatch.delenv(key, raising=False)


@pytest.fixture
def fixture_items():
    from smart_daily_v2.sources.mock import load_fixture_items

    return load_fixture_items()


@pytest.fixture
def golden_rows() -> list[dict]:
    fixture_path = Path(__file__).parent / "fixtures" / "mock_work_items.json"
    return json.loads(fixture_path.read_text(encoding="utf-8"))
