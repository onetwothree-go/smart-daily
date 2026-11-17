from datetime import datetime
from pathlib import Path


def test_three_sources_satisfy_protocol() -> None:
    from smart_daily_v2.sources.base import WorkSource

    class GitHubLikeSource:
        name = "source-one"

        def collect(
            self,
            *,
            since: datetime,
            until: datetime,
            author: str | None = None,
        ) -> list[object]:
            return []

    class TaskLikeSource:
        name = "source-two"

        def collect(
            self,
            *,
            since: datetime,
            until: datetime,
            author: str | None = None,
        ) -> list[object]:
            return []

    class ChatLikeSource:
        name = "source-three"

        def collect(
            self,
            *,
            since: datetime,
            until: datetime,
            author: str | None = None,
        ) -> list[object]:
            return []

    assert all(
        isinstance(source, WorkSource)
        for source in (GitHubLikeSource(), TaskLikeSource(), ChatLikeSource())
    )


def test_protocol_text_has_no_platform_fields() -> None:
    import smart_daily_v2.sources.base as base_module

    source = Path(base_module.__file__).read_text(encoding="utf-8").lower()

    for platform_field in ("github", "feishu", "commit_sha", "webhook"):
        assert platform_field not in source


def test_all_sources_error_message() -> None:
    from smart_daily_v2.sources.base import (
        AllSourcesUnavailableError,
        SourceUnavailableError,
    )

    errors = [
        SourceUnavailableError("source-one", "first reason"),
        SourceUnavailableError("source-two", "second reason"),
        SourceUnavailableError("source-three", "third reason"),
    ]

    exception = AllSourcesUnavailableError(errors)
    message = str(exception)

    for source, reason in (
        ("source-one", "first reason"),
        ("source-two", "second reason"),
        ("source-three", "third reason"),
    ):
        assert source in message
        assert reason in message
    assert exception.errors == errors


def test_all_sources_error_is_catchable() -> None:
    from smart_daily_v2.sources.base import (
        AllSourcesUnavailableError,
        SourceUnavailableError,
    )

    assert issubclass(AllSourcesUnavailableError, SourceUnavailableError)

    exception = AllSourcesUnavailableError([SourceUnavailableError("source-one", "first reason")])
    try:
        raise exception
    except SourceUnavailableError as caught:
        assert caught is exception
