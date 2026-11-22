from datetime import datetime
from pathlib import Path

import httpx
import pytest

from smart_daily_v2.models import LOCAL_TZ
from smart_daily_v2.sources.base import SourceUnavailableError

SINCE = datetime(2026, 11, 18, 0, 0, tzinfo=LOCAL_TZ)
UNTIL = datetime(2026, 11, 19, 0, 0, tzinfo=LOCAL_TZ)


def _commit(sha: str, login: str, index: int) -> dict[str, object]:
    return {
        "sha": sha,
        "author": {"login": login},
        "commit": {
            "message": f"placeholder commit {sha}",
            "author": {"date": f"2026-11-18T10:{index:02d}:00+08:00"},
        },
    }


def _install_github(
    monkeypatch,
    branches: str,
    responses: list[httpx.Response],
) -> list[dict[str, object]]:
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setenv("GITHUB_REPO_OWNER", "fake-owner")
    monkeypatch.setenv("GITHUB_REPO_NAME", "fake-repo")
    monkeypatch.setenv("GITHUB_API", "https://example.com")
    monkeypatch.setenv("GITHUB_BRANCH", branches)
    calls: list[dict[str, object]] = []

    def fake_get(url, *, params, headers, timeout):
        calls.append({"url": url, "params": params, "headers": headers, "timeout": timeout})
        return responses[len(calls) - 1]

    monkeypatch.setattr(httpx, "get", fake_get)
    return calls


def _response(status: int, payload: object) -> httpx.Response:
    return httpx.Response(
        status,
        json=payload,
        request=httpx.Request("GET", "https://example.com"),
    )


def test_multibranch_two_branches_dedup_by_sha(monkeypatch, cleared_env) -> None:
    import smart_daily_v2.sources.github as gh

    calls = _install_github(
        monkeypatch,
        "main,dev",
        [
            _response(200, [_commit("sha-A", "alice", 1), _commit("sha-M", "merge", 2)]),
            _response(200, [_commit("sha-M", "merge", 2), _commit("sha-B", "bob", 3)]),
        ],
    )

    items = gh.GithubSource.from_env().collect(since=SINCE, until=UNTIL)

    assert len(calls) == 2
    assert [call["params"]["sha"] for call in calls] == ["main", "dev"]
    assert len(items) == 3
    assert [item.record_id for item in items] == ["sha-A", "sha-M", "sha-B"]


def test_multibranch_single_branch_regression(monkeypatch, cleared_env) -> None:
    import smart_daily_v2.sources.github as gh

    calls = _install_github(
        monkeypatch,
        "main",
        [_response(200, [_commit("sha-A", "alice", 1), _commit("sha-B", "bob", 2)])],
    )

    items = gh.GithubSource.from_env().collect(since=SINCE, until=UNTIL)

    assert len(calls) == 1
    assert calls[0]["params"]["sha"] == "main"
    assert len(items) == 2


def test_multibranch_empty_value_falls_back_default(monkeypatch, cleared_env) -> None:
    import smart_daily_v2.sources.github as gh

    calls = _install_github(
        monkeypatch,
        "",
        [_response(200, []), _response(200, [])],
    )

    gh.GithubSource.from_env().collect(since=SINCE, until=UNTIL)

    assert len(calls) == 2
    assert [call["params"]["sha"] for call in calls] == ["main", "dev"]


def test_multibranch_failed_branch_skipped(monkeypatch, cleared_env) -> None:
    import smart_daily_v2.sources.github as gh

    calls = _install_github(
        monkeypatch,
        "main,dev",
        [
            _response(404, {"message": "not found"}),
            _response(200, [_commit("sha-A", "alice", 1), _commit("sha-B", "bob", 2)]),
        ],
    )

    items = gh.GithubSource.from_env().collect(since=SINCE, until=UNTIL)

    assert len(calls) == 2
    assert len(items) == 2
    assert [item.record_id for item in items] == ["sha-A", "sha-B"]


def test_multibranch_all_fail_raises_after_all_branches(monkeypatch, cleared_env) -> None:
    import smart_daily_v2.sources.github as gh

    calls = _install_github(
        monkeypatch,
        "main,dev",
        [_response(404, {"message": "not found"}), _response(404, {"message": "not found"})],
    )

    with pytest.raises(SourceUnavailableError):
        gh.GithubSource.from_env().collect(since=SINCE, until=UNTIL)

    assert len(calls) == 2


def test_multibranch_scope_guard() -> None:
    import smart_daily_v2.sources.github as gh

    source = Path(gh.__file__).read_text(encoding="utf-8")
    forbidden = (
        "gh" + "p_",
        "xox" + "b-",
        "@" + "qq.com",
        "open.feishu" + ".cn",
    )
    test_source = Path(__file__).read_text(encoding="utf-8")
    v1_import_prefixes = ("from " + "v1", "import " + "v1")

    for value in forbidden:
        assert value not in source
    assert "待确认" in (gh.__doc__ or "")
    assert "已裁定" not in source
    assert not any(
        line.lstrip().startswith(prefix)
        for line in test_source.splitlines()
        for prefix in v1_import_prefixes
    )
