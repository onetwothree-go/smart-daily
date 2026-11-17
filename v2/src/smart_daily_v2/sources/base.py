from datetime import datetime
from typing import Protocol, runtime_checkable

from smart_daily_v2.models import WorkItem


@runtime_checkable
class WorkSource(Protocol):
    name: str

    def collect(
        self,
        *,
        since: datetime,
        until: datetime,
        author: str | None = None,
    ) -> list[WorkItem]: ...


class SourceUnavailableError(Exception):
    def __init__(self, source: str, reason: str) -> None:
        self.source = source
        self.reason = reason
        super().__init__(f"{source}: {reason}")


class AllSourcesUnavailableError(SourceUnavailableError):
    def __init__(self, errors: list[SourceUnavailableError]) -> None:
        self.errors = errors
        reason = "; ".join(f"{error.source}: {error.reason}" for error in errors)
        super().__init__("all_sources", reason)
