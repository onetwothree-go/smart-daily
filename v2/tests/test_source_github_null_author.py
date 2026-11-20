from datetime import datetime
from pathlib import Path

import httpx

from smart_daily_v2.identity import normalize_key
from smart_daily_v2.models import LOCAL_TZ

SINCE = datetime(2026, 11, 18, 0, 0, tzinfo=LOCAL_TZ)
UNTIL = datetime(2026, 11, 19, 0, 0, tzinfo=LOCAL_TZ)


def _install_github(monkeypatch, commits: list[dict[str, object]]):
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setenv("GITHUB_REPO_OWNER", "fake-owner")
    monkeypatch.setenv("GITHUB_REPO_NAME", "fake-repo")
    monkeypatch.setenv("GITHUB_API", "https://example.com")
    monkeypatch.setenv("GITHUB_BRANCH", "main")
    monkeypatch.setattr(
        httpx,
        "get",
        lambda url, **kwargs: httpx.Response(
            200,
            json=commits,
            request=httpx.Request("GET", url),
        ),
    )


def _commit(sha: str, login: str | None, name: str, index: int) -> dict[str, object]:
    author = None if login is None else {"login": login}
    return {
        "sha": sha,
        "author": author,
        "commit": {
            "message": f"placeholder commit {sha}",
            "author": {
                "name": name,
                "date": f"2026-11-18T10:{index:02d}:00+08:00",
            },
        },
    }


def test_null_author_falls_back_to_git_name(monkeypatch, cleared_env) -> None:
    import smart_daily_v2.sources.github as gh

    _install_github(monkeypatch, [_commit("fake-sha-1", None, " fh0709 ", 0)])

    items = gh.GithubSource.from_env().collect(since=SINCE, until=UNTIL)

    assert len(items) == 1
    assert items[0].member == normalize_key("fh0709") == "fh0709"


def test_null_author_mixed_with_normal(monkeypatch, cleared_env) -> None:
    import smart_daily_v2.sources.github as gh

    _install_github(
        monkeypatch,
        [
            _commit("fake-sha-2", "Alice", "Alice Commit", 1),
            _commit("fake-sha-3", None, "fh0709", 2),
        ],
    )

    items = gh.GithubSource.from_env().collect(since=SINCE, until=UNTIL)

    assert len(items) == 2
    assert {item.member for item in items} == {"alice", "fh0709"}


def test_null_author_scope_no_real_credentials() -> None:
    import smart_daily_v2.sources.github as gh

    source = Path(gh.__file__).read_text(encoding="utf-8")
    login_access = "commit[" + '"author"' + "][" + '"login"' + "]"
    fallback_name = "commit[" + '"commit"' + "][" + '"author"' + "][" + '"name"' + "]"
    forbidden = (
        "gh" + "p_",
        "xox" + "b-",
        "@" + "qq.com",
        "@gmail" + ".com",
        "open.feishu" + ".cn",
    )

    assert login_access in source
    assert fallback_name in source
    assert "待确认" in (gh.__doc__ or "")
    assert "已裁定" not in source
    for value in forbidden:
        assert value not in source


def test_null_author_guard_normal_login_unchanged(monkeypatch, cleared_env) -> None:
    import smart_daily_v2.sources.github as gh

    _install_github(monkeypatch, [_commit("fake-sha-4", " NormalUser ", "Other Name", 3)])

    items = gh.GithubSource.from_env().collect(since=SINCE, until=UNTIL)

    assert len(items) == 1
    assert items[0].member == "normaluser"
