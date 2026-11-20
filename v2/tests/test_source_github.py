import inspect
from datetime import datetime
from pathlib import Path

import httpx
import pytest

from smart_daily_v2.identity import normalize_key
from smart_daily_v2.models import LOCAL_TZ, WorkItem, local_date
from smart_daily_v2.sources.base import SourceUnavailableError, WorkSource

SINCE = datetime(2026, 11, 18, 0, 0, tzinfo=LOCAL_TZ)
UNTIL = datetime(2026, 11, 19, 0, 0, tzinfo=LOCAL_TZ)

_GITHUB_COMMITS_FIXTURE = [
    {
        "sha": "sha-201-001",
        "commit": {
            "message": "甲 更新日报逻辑\n保留原始详情",
            "author": {"date": "2026-11-18T09:00:00+08:00"},
        },
        "author": {"login": " MemberA "},
        "html_url": "https://example.com/commit/sha-201-001",
    },
    {
        "sha": "sha-201-002",
        "commit": {
            "message": "乙 整理任务进度\n补充占位说明",
            "author": {"date": "2026-11-18T10:15:00+08:00"},
        },
        "author": {"login": "memberb"},
        "html_url": "https://example.com/commit/sha-201-002",
    },
    {
        "sha": "sha-201-003",
        "commit": {
            "message": "丙 核对采集字段\n确认时间归属",
            "author": {"date": "2026-11-18T11:30:00+08:00"},
        },
        "author": {"login": "MEMBERA"},
        "html_url": "https://example.com/commit/sha-201-003",
    },
]


def _response(status: int, payload: object) -> httpx.Response:
    return httpx.Response(
        status,
        json=payload,
        request=httpx.Request("GET", "https://example.com"),
    )


def _install_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setenv("GITHUB_REPO_OWNER", "owner-placeholder")
    monkeypatch.setenv("GITHUB_REPO_NAME", "repo-placeholder")
    monkeypatch.setenv("GITHUB_API", "https://example.com")
    monkeypatch.setenv("GITHUB_BRANCH", "main")


def _fake_get(
    monkeypatch: pytest.MonkeyPatch,
    responses: list[httpx.Response],
) -> list[dict[str, object]]:
    calls: list[dict[str, object]] = []

    def fake_get(url: str, *, params, headers, timeout):
        calls.append(
            {
                "url": url,
                "params": params,
                "headers": headers,
                "timeout": timeout,
            }
        )
        return responses[len(calls) - 1]

    monkeypatch.setattr(httpx, "get", fake_get)
    return calls


def test_three_commits_map_to_workitems_with_original_sha(monkeypatch, cleared_env) -> None:
    import smart_daily_v2.sources.github as gh

    _install_env(monkeypatch)
    _fake_get(monkeypatch, [_response(200, _GITHUB_COMMITS_FIXTURE)])

    items = gh.GithubSource.from_env().collect(since=SINCE, until=UNTIL)

    assert len(items) == 3
    assert all(isinstance(item, WorkItem) for item in items)
    assert [item.record_id for item in items] == [
        "sha-201-001",
        "sha-201-002",
        "sha-201-003",
    ]
    assert all(item.source == "github" and item.kind == "commit" for item in items)
    assert [item.title for item in items] == [
        "甲 更新日报逻辑",
        "乙 整理任务进度",
        "丙 核对采集字段",
    ]
    assert [item.detail for item in items] == [
        "甲 更新日报逻辑\n保留原始详情",
        "乙 整理任务进度\n补充占位说明",
        "丙 核对采集字段\n确认时间归属",
    ]
    assert all(item.occurred_at.tzinfo is not None for item in items)
    assert all(item.local_day == local_date(item.occurred_at) for item in items)


def test_invalid_token_401_raises_source_unavailable(monkeypatch, cleared_env) -> None:
    import smart_daily_v2.sources.github as gh

    _install_env(monkeypatch)
    _fake_get(monkeypatch, [_response(401, {"message": "Bad credentials"})])

    with pytest.raises(SourceUnavailableError) as exc_info:
        gh.GithubSource.from_env().collect(since=SINCE, until=UNTIL)

    assert "token" in str(exc_info.value).lower()
    assert "401" in str(exc_info.value)


def test_empty_repo_409_raises_with_empty_repo_message(monkeypatch, cleared_env) -> None:
    import smart_daily_v2.sources.github as gh

    _install_env(monkeypatch)
    _fake_get(monkeypatch, [_response(409, {"message": "Git Repository is empty."})])

    with pytest.raises(SourceUnavailableError) as exc_info:
        gh.GithubSource.from_env().collect(since=SINCE, until=UNTIL)

    assert "仓库为空" in str(exc_info.value)


def test_missing_repo_config_sends_no_request(monkeypatch, cleared_env) -> None:
    import smart_daily_v2.sources.github as gh

    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    calls = _fake_get(monkeypatch, [])

    with pytest.raises(SourceUnavailableError):
        gh.GithubSource.from_env().collect(since=SINCE, until=UNTIL)

    assert calls == []


def test_missing_token_sends_no_request(monkeypatch, cleared_env) -> None:
    import smart_daily_v2.sources.github as gh

    monkeypatch.setenv("GITHUB_REPO_OWNER", "owner-placeholder")
    monkeypatch.setenv("GITHUB_REPO_NAME", "repo-placeholder")
    calls = _fake_get(monkeypatch, [])

    with pytest.raises(SourceUnavailableError):
        gh.GithubSource.from_env().collect(since=SINCE, until=UNTIL)

    assert calls == []


def test_request_params_include_main_branch_time_window_and_author(
    monkeypatch, cleared_env
) -> None:
    import smart_daily_v2.sources.github as gh

    _install_env(monkeypatch)
    calls = _fake_get(monkeypatch, [_response(200, [])])
    author = "MemberA"

    gh.GithubSource.from_env().collect(since=SINCE, until=UNTIL, author=author)

    assert len(calls) == 1
    request = calls[0]
    params = request["params"]
    headers = request["headers"]
    assert isinstance(params, dict)
    assert params["sha"] == "main"
    assert params["since"] == SINCE.isoformat()
    assert params["until"] == UNTIL.isoformat()
    assert params["author"] == author
    assert "per_page" in params and "page" in params
    assert isinstance(headers, dict)
    assert "fake-token" in str(headers.get("Authorization", ""))
    assert headers.get("X-GitHub-Api-Version") == "2022-11-28"


def test_collect_signature_is_keyword_only_and_satisfies_worksource(
    monkeypatch, cleared_env
) -> None:
    import smart_daily_v2.sources.github as gh

    _install_env(monkeypatch)
    source = gh.GithubSource.from_env()
    parameters = inspect.signature(gh.GithubSource.collect).parameters

    assert parameters["since"].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters["until"].kind is inspect.Parameter.KEYWORD_ONLY
    with pytest.raises(TypeError):
        source.collect(SINCE, UNTIL)
    assert isinstance(source, WorkSource)


def test_login_normalized_via_identity_key(monkeypatch, cleared_env) -> None:
    import smart_daily_v2.sources.github as gh

    _install_env(monkeypatch)
    _fake_get(monkeypatch, [_response(200, _GITHUB_COMMITS_FIXTURE)])

    items = gh.GithubSource.from_env().collect(since=SINCE, until=UNTIL)

    assert [item.member for item in items] == [
        normalize_key(commit["author"]["login"]) for commit in _GITHUB_COMMITS_FIXTURE
    ]
    source = Path(gh.__file__).read_text(encoding="utf-8")
    assert "lookup_display_name" not in source


def test_no_real_credentials_or_v1_import_in_source(monkeypatch, cleared_env) -> None:
    import smart_daily_v2.sources.github as gh

    _install_env(monkeypatch)
    source = Path(gh.__file__).read_text(encoding="utf-8")

    for forbidden in ("ghp_", "xoxb-", "@qq.com", "@gmail.com", "from smart_daily import"):
        assert forbidden not in source
    assert "https://api.github.com" not in source
    assert "api.github.com" not in source


def test_k4_scope_registration_docstring(monkeypatch, cleared_env) -> None:
    import smart_daily_v2.sources.github as gh

    _install_env(monkeypatch)
    source = Path(gh.__file__).read_text(encoding="utf-8")

    for anchor in ("待确认", "RawRecord", "归一化单点"):
        assert anchor in source
    assert "已裁定" not in source
    for registration in (
        "L292",
        "L325",
        "L300",
        "S5",
        "翻页",
        "201 验收未列",
    ):
        assert registration in source
