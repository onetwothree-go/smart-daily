"""Integration tests for fallback behavior at the orchestration boundary.

Scope registration (☐ 待确认): C2 / R2 / R5 / K1 are covered without changing
production modules or copying v1 implementation code.
"""

import inspect
from datetime import date, datetime, time, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from smart_daily_v2 import orchestrator
from smart_daily_v2.models import LOCAL_TZ
from smart_daily_v2.sources import github as github_module
from smart_daily_v2.sources.base import (
    AllSourcesUnavailableError,
    SourceUnavailableError,
)
from smart_daily_v2.sources.fallback import collect_with_fallback
from smart_daily_v2.sources.github import GithubSource
from smart_daily_v2.sources.mock import FIXTURE_MEMBERS, load_fixture_items

DAY = date(2026, 11, 18)
SINCE = datetime.combine(DAY, time.min, tzinfo=LOCAL_TZ)
UNTIL = datetime.combine(DAY + timedelta(days=1), time.min, tzinfo=LOCAL_TZ)


def FakeResponse(status_code: int) -> SimpleNamespace:
    return SimpleNamespace(
        is_success=200 <= status_code < 300,
        status_code=status_code,
        json=lambda: [],
    )


def fake_source(name: str, behavior: str, *, calls: dict) -> SimpleNamespace:
    def collect(*, since, until, author=None):
        calls[name] = calls.get(name, 0) + 1
        if behavior == "ok":
            return load_fixture_items()
        if behavior == "unavailable":
            raise SourceUnavailableError(name, f"测试注入 {name} 不可用")
        if behavior == "empty":
            return []
        raise AssertionError(f"unknown test behavior: {behavior}")

    return SimpleNamespace(name=name, collect=collect)


def make_github_401() -> GithubSource:
    return GithubSource(
        github_token="fake-token-only-for-test",
        github_repo_owner="example",
        github_repo_name="demo",
        github_api="https://example.invalid",
        github_branch="main",
    )


def test_integration_first_source_401_falls_back_and_run_completes(fallback_harness, monkeypatch):
    response = FakeResponse(401)
    monkeypatch.setattr(github_module.httpx, "get", lambda *args, **kwargs: response)
    calls = {}
    sources = [make_github_401(), fake_source("fixture_b", "ok", calls=calls)]

    outcome = fallback_harness.run(sources, day=DAY)

    assert outcome.result["items"] > 0
    assert outcome.result["members"] > 0


def test_integration_downgrade_reason_recorded_in_source_field(fallback_harness, monkeypatch):
    monkeypatch.setattr(
        github_module.httpx,
        "get",
        lambda *args, **kwargs: FakeResponse(401),
    )
    calls = {}
    sources = [make_github_401(), fake_source("fixture_b", "ok", calls=calls)]

    outcome = fallback_harness.run(sources, day=DAY)

    assert outcome.result["source"]
    assert any("github" in reason and "401" in reason for reason in outcome.result["source"])


def test_integration_next_source_actually_called(fallback_harness, monkeypatch):
    monkeypatch.setattr(
        github_module.httpx,
        "get",
        lambda *args, **kwargs: FakeResponse(401),
    )
    calls = {}
    sources = [make_github_401(), fake_source("fixture_b", "ok", calls=calls)]

    fallback_harness.run(sources, day=DAY)

    assert calls["fixture_b"] >= 1


def test_integration_three_sources_all_fail_raises_aggregated(fallback_harness):
    calls = {}
    sources = [
        fake_source("s1", "unavailable", calls=calls),
        fake_source("s2", "unavailable", calls=calls),
        fake_source("s3", "unavailable", calls=calls),
    ]

    with pytest.raises(AllSourcesUnavailableError) as exc_info:
        fallback_harness.run(sources, day=DAY)

    message = str(exc_info.value)
    for name in ("s1", "s2", "s3"):
        assert name in message
    assert len(exc_info.value.errors) == 3


def test_integration_all_fail_stdout_has_no_empty_day_banner(fallback_harness, capsys):
    calls = {}
    sources = [
        fake_source("s1", "unavailable", calls=calls),
        fake_source("s2", "unavailable", calls=calls),
        fake_source("s3", "unavailable", calls=calls),
    ]

    with pytest.raises(AllSourcesUnavailableError):
        fallback_harness.run(sources, day=DAY)

    assert "今日无工作记录" not in capsys.readouterr().out


def test_integration_all_fail_error_inherits_source_unavailable(fallback_harness):
    assert issubclass(AllSourcesUnavailableError, SourceUnavailableError)
    calls = {}
    sources = [fake_source("s1", "unavailable", calls=calls)]

    with pytest.raises(SourceUnavailableError):
        fallback_harness.run(sources, day=DAY)


def test_integration_missing_credentials_makes_zero_http_calls(
    fallback_harness, cleared_env, monkeypatch
):
    http_calls = []
    monkeypatch.setattr(
        github_module.httpx,
        "get",
        lambda *args, **kwargs: http_calls.append((args, kwargs)),
    )
    source = GithubSource.from_env()

    with pytest.raises(SourceUnavailableError):
        source.collect(since=SINCE, until=UNTIL)

    assert len(http_calls) == 0


def test_integration_partial_missing_credentials_zero_http_calls(
    fallback_harness, cleared_env, monkeypatch
):
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token-only-for-test")
    monkeypatch.setenv("GITHUB_API", "https://example.invalid")
    http_calls = []
    monkeypatch.setattr(
        github_module.httpx,
        "get",
        lambda *args, **kwargs: http_calls.append((args, kwargs)),
    )
    source = GithubSource.from_env()

    with pytest.raises(SourceUnavailableError):
        source.collect(since=SINCE, until=UNTIL)

    assert len(http_calls) == 0


def test_integration_empty_first_source_stops_no_switch(fallback_harness):
    calls = {}
    sources = [
        fake_source("s1", "empty", calls=calls),
        fake_source("s2", "ok", calls=calls),
    ]

    outcome = fallback_harness.run(sources, day=DAY)

    assert outcome.result["items"] == 0
    assert calls["s1"] == 1
    assert "s2" not in calls


def test_integration_scope_registration_and_no_v1_copy(fallback_harness):
    orchestrator_source = inspect.getsource(orchestrator.run)
    github_source = inspect.getsource(GithubSource.collect)
    test_source = Path(__file__).read_text(encoding="utf-8")

    assert "collect_with_fallback(" in orchestrator_source
    assert "401:" in github_source
    assert "v1" + "/src" not in test_source
    assert "smart_daily" + " import" not in test_source
    module_docstring = __doc__ or ""
    for anchor in ("C2", "R2", "R5", "K1", "待确认"):
        assert anchor in module_docstring
    assert "已裁定" not in module_docstring
    assert set(FIXTURE_MEMBERS) == {"甲", "乙", "丙", "丁"}
    assert callable(collect_with_fallback)
