"""Feishu task source.

Scope notes (☐ 待确认，组内):
- K4 口径漂移：tasks.md L292 要求采集器只产 RawRecord，并指定 104 fallback.py
  为归一化单点；但 L332、L300、base.py、201 github.py、601 mock.py 与 104
  现状使用 list[WorkItem]。本模块遵循 L332、L300 和已落地接口返回 WorkItem，
  不调用 normalize()。若改选方案乙，需同步改 L292、104④、Architecture 三处。
- S5 身份边界：101 只提供 normalize_key / normalize_members；lookup_display_name
  和显示名映射属于 501 编排层，606 以测试桩隔离。本模块只用 normalize_key
  生成 member 键，不做显示名映射，不新建 identity 模块或编排层。
- 跨天与 --day：--day 属 CLI（504），202 只以 since/until 时间窗映射
  created_at_from/to；v1 design L148、L154 规定按 created_at 的 local_date
  归属，completed_at 只用于追溯、不参与归属或计数。本模块不实现 CLI。
- TaskEntry 字段张力：v1 design L146 的字段多于 v2 TaskEntry / WorkItem。
  将 task_id、summary、created_at 派生到 WorkItem 通用字段，description 保留在
  detail，completed 与 completed_at 作为追溯文本；不扩充 models.py。
- 翻页形状：按 v1 design L479 的 code/data/items/has_more/page_token 约定翻页；
  响应各字段形状待组内确认。
- G7：只返回 WorkItem，不调 normalize()；归一化单点仍为 104 fallback.py。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import httpx

from smart_daily_v2.config import load_config
from smart_daily_v2.identity import normalize_key
from smart_daily_v2.models import WorkItem, local_date
from smart_daily_v2.sources.base import SourceUnavailableError, WorkSource


@dataclass(frozen=True)
class FeishuTaskSource(WorkSource):
    feishu_app_id: str
    feishu_app_secret: str
    feishu_api: str

    name = "feishu_task"

    @classmethod
    def from_env(cls) -> FeishuTaskSource:
        config = load_config()
        return cls(
            feishu_app_id=config.feishu_app_id,
            feishu_app_secret=config.feishu_app_secret,
            feishu_api=config.feishu_api,
        )

    def collect(
        self,
        *,
        since: datetime,
        until: datetime,
        author: str | None = None,
    ) -> list[WorkItem]:
        missing = [
            name
            for name, value in (
                ("FEISHU_APP_ID", self.feishu_app_id),
                ("FEISHU_APP_SECRET", self.feishu_app_secret),
            )
            if not value
        ]
        if missing:
            raise SourceUnavailableError("feishu_task", f"凭证未配置：{', '.join(missing)}")

        url = f"{self.feishu_api.rstrip('/')}/task/v1/tasks"
        headers = {
            "X-Application-Id": self.feishu_app_id,
            "X-Application-Secret": self.feishu_app_secret,
        }
        params = {
            "page_size": 100,
            "page_token": "",
            "completed": None,
            "created_at_from": since.isoformat(),
            "created_at_to": until.isoformat(),
            "author": author,
        }

        tasks: list[dict[str, object]] = []
        while True:
            try:
                response = httpx.get(url, params=params, headers=headers, timeout=15)
            except httpx.HTTPError as exc:
                raise SourceUnavailableError("feishu_task", f"请求失败：{exc}") from exc

            if not response.is_success:
                raise SourceUnavailableError(
                    "feishu_task", f"请求失败（HTTP {response.status_code}）"
                )

            payload = response.json()
            if payload["code"] != 0:
                raise SourceUnavailableError(
                    "feishu_task",
                    f"飞书任务接口错误 code={payload['code']}：{payload.get('msg', '')}",
                )

            data = payload["data"]
            tasks.extend(data["items"])
            if not data["has_more"]:
                break
            params["page_token"] = data["page_token"]

        items: list[WorkItem] = []
        for task in tasks:
            occurred_at = datetime.fromisoformat(task["created_at"])
            items.append(
                WorkItem(
                    record_id=task["task_id"],
                    source=self.name,
                    member=normalize_key(task["creator_name"]),
                    kind="task",
                    title=task["summary"],
                    detail=(
                        f"{task['description']}\n"
                        f"completed: {task['completed']}\n"
                        f"completed_at: {task['completed_at']}"
                    ),
                    occurred_at=occurred_at,
                    local_day=local_date(occurred_at),
                )
            )
        return items
