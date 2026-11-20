"""Feishu group message source.

Scope notes (☐ 待确认，组内):
- K4 口径漂移：tasks.md L292（102 K4 方案甲）要求 201–203 只产 RawRecord
  （CommitEntry / TaskEntry / MessageEntry），normalize() 的归一化单点在
  104 fallback.py；但 L339（203 Interfaces）、L300（103 协议）、base.py L17、
  201 github.py、202 feishu_tasks.py、601 mock.py 与 104 fallback.py 均为
  list[WorkItem]。本模块遵循 L339、L300 和已落地现状返回 WorkItem，不调用
  normalize()，未改 base.py / models.py / fallback.py / config.py，也未改回
  RawRecord。改选方案乙需同步改 L292、104④、Architecture 三处；此冲突待确认。
- S5 身份映射边界：101 只提供 normalize_key / normalize_members；v2 尚无显示名
  查询函数，显示名映射属于 501 编排层，606 已用测试内桩隔离。本模块只用
  normalize_key(sender_name) 作 member 键，不做显示名映射、不新建 identity 模块或编排层。
- 单群范围过滤：proposal S3 L61 / I12 L197 限定 FEISHU_CHAT_ID 指定单一团队群，
  不抓私聊或其他群；proposal N7 L79 排除自动内容过滤、字段级脱敏和跨源去重。
  本模块请求带 container_id，并按 chat_id 匹配且 chat_type != p2p 做范围过滤；
  这不等同内容过滤。本模块不对正文过滤、脱敏或摘要，不跨源去重（C1 1:1），
  mentions 只作追溯线索、不拆多人条目。
- 正文原样与截断边界：S4 / I8（proposal L193）要求原文原样，I8 提及长文本前
  60 字截断，v1 design L162 写 title 为消息前 60 字；tasks.md L356 将相关验收
  放在生成层 302。本模块 detail 保留 text 逐字原样，title 暂取原文；是否由采集器
  截断 title 属待确认，不擅自确定落点、不改 tasks.md。
- MessageEntry 字段张力：v1 design L145 列出 message_id、chat_id、sender_id、
  sender_name、text、msg_type、mentions、thread_id；v2 MessageEntry / WorkItem
  只有通用字段。本模块将 message_id、sender_name、text、create_time 派生到
  record_id、member、title/detail、occurred_at/local_day；chat_id / chat_type 仅用于
  范围过滤，msg_type 不进入 WorkItem，mentions 只作追溯线索，不扩充模型字段。
- 时间与响应形状：v1 design L480 列 start_time / end_time、message_id、sender、
  text、msg_type，未明确单位或响应时间字段名。按桩约定用 ISO create_time 解析，
  since / until 转秒时间戳作为查询参数；字段形状与单位仍待组内确认。
- G7：采集器返回 WorkItem，不调用 normalize()；归一化单点仍是 104 fallback.py，
  下游不得二次归一化。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import httpx

from smart_daily_v2.config import load_config
from smart_daily_v2.identity import normalize_key
from smart_daily_v2.models import WorkItem, local_date
from smart_daily_v2.sources.base import SourceUnavailableError, WorkSource


def _fetch_tenant_access_token(app_id: str, app_secret: str, api_base: str) -> str:
    url = f"{api_base.rstrip('/')}/auth/v3/tenant_access_token/internal"
    try:
        response = httpx.post(
            url,
            json={"app_id": app_id, "app_secret": app_secret},
            timeout=15,
        )
    except httpx.HTTPError as exc:
        raise SourceUnavailableError("feishu_chat", f"token 请求失败：{exc}") from exc
    if not response.is_success:
        raise SourceUnavailableError(
            "feishu_chat", f"token 请求失败（HTTP {response.status_code}）"
        )
    payload = response.json()
    if payload.get("code") != 0:
        raise SourceUnavailableError(
            "feishu_chat",
            f"token 接口错误 code={payload.get('code')}：{payload.get('msg', '')}",
        )
    token = payload.get("tenant_access_token", "")
    if not token:
        raise SourceUnavailableError("feishu_chat", "token 响应缺少 tenant_access_token")
    return token


@dataclass(frozen=True)
class FeishuChatSource(WorkSource):
    feishu_app_id: str
    feishu_app_secret: str
    feishu_chat_id: str
    feishu_api: str

    name = "feishu_chat"

    @classmethod
    def from_env(cls) -> FeishuChatSource:
        config = load_config()
        return cls(
            feishu_app_id=config.feishu_app_id,
            feishu_app_secret=config.feishu_app_secret,
            feishu_chat_id=config.feishu_chat_id,
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
                ("FEISHU_CHAT_ID", self.feishu_chat_id),
            )
            if not value
        ]
        if missing:
            raise SourceUnavailableError(self.name, f"凭证未配置：{', '.join(missing)}")

        token = _fetch_tenant_access_token(
            self.feishu_app_id, self.feishu_app_secret, self.feishu_api
        )
        url = f"{self.feishu_api.rstrip('/')}/im/v1/messages"
        headers = {
            "X-Application-Id": self.feishu_app_id,
            "X-Application-Secret": self.feishu_app_secret,
            "Authorization": f"Bearer {token}",
        }
        params = {
            "container_id": self.feishu_chat_id,
            "start_time": int(since.timestamp()),
            "end_time": int(until.timestamp()),
            "page_size": 100,
            "page_token": "",
            "author": author,
        }

        messages: list[dict[str, object]] = []
        while True:
            try:
                response = httpx.get(url, params=params, headers=headers, timeout=15)
            except httpx.HTTPError as exc:
                raise SourceUnavailableError(self.name, f"请求失败：{exc}") from exc

            if not response.is_success:
                raise SourceUnavailableError(self.name, f"请求失败（HTTP {response.status_code}）")

            payload = response.json()
            if payload["code"] != 0:
                raise SourceUnavailableError(
                    self.name,
                    f"飞书群消息接口错误 code={payload['code']}：{payload.get('msg', '')}",
                )

            data = payload["data"]
            messages.extend(data.get("items", []))
            if not data["has_more"]:
                break
            params["page_token"] = data["page_token"]

        items: list[WorkItem] = []
        for message in messages:
            if message.get("chat_id") != self.feishu_chat_id or message.get("chat_type") == "p2p":
                continue

            sender = message.get("sender", {})
            sender_name = sender.get("sender_name", message.get("sender_name"))
            text = message["text"]
            occurred_at = datetime.fromisoformat(message["create_time"])
            items.append(
                WorkItem(
                    record_id=message["message_id"],
                    source=self.name,
                    member=normalize_key(sender_name),
                    kind="message",
                    title=text,
                    detail=text,
                    occurred_at=occurred_at,
                    local_day=local_date(occurred_at),
                )
            )
        return items
