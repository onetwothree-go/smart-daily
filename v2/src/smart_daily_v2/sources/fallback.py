"""按源顺序执行异常驱动降级。

F2-02：接口把第二返回值定义为降级原因，但验收②要求空列表停止时记录停止点源名，
而验收⑤要求正常成功时返回空列表。本实现按验收字面分别返回 []、累积降级原因或
[停止点源名]；该「降级原因」语义张力待确认，后续交组内确认。

K4：任务规范指定 RawRecord 在此处统一归一化，但已落地 WorkSource 契约返回
WorkItem。此处保留既有协议，并对合并结果调用一次幂等 normalize；该口径漂移待确认。

K8：AllSourcesUnavailableError 是 SourceUnavailableError 子类，捕获时必须先单独重抛。
返回 WorkItem 后，下游不得再次调用 normalize（G7）。
"""

from collections.abc import Sequence  # noqa: I001 (keep standalone normalize import per test contract)
from datetime import datetime

from smart_daily_v2.models import normalize
from smart_daily_v2.models import WorkItem
from smart_daily_v2.sources.base import (
    AllSourcesUnavailableError,
    SourceUnavailableError,
    WorkSource,
)


def collect_with_fallback(
    sources: Sequence[WorkSource],
    *,
    since: datetime,
    until: datetime,
    author: str | None = None,
) -> tuple[list[WorkItem], list[str]]:
    reasons: list[str] = []
    errors: list[SourceUnavailableError] = []

    for source in sources:
        try:
            rows = source.collect(since=since, until=until, author=author)
        except AllSourcesUnavailableError:
            raise
        except SourceUnavailableError as exc:
            reasons.append(f"{source.name}: {exc.reason}")
            errors.append(exc)
            continue

        if not rows:
            return [], [source.name]

        return normalize(rows), reasons

    raise AllSourcesUnavailableError(errors)
