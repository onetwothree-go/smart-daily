"""飞书开放平台采集器（采集层 · 真实数据源）

职责：读取飞书任务、群消息、通讯录成员，转为统一数据模型。

规范依据：specs/proposal.md「采集（飞书任务、飞书消息）」范围条目
对应权限（最小权限原则，其余一律不申请）：
    task:task:readonly        查看任务详情
    im:message                获取与发送单聊、群组消息
    contact:user.base         获取用户基本信息

关键设计：
  1. 令牌自动获取与缓存 —— tenant_access_token 有效期约 2 小时，
     每次请求都换会触发限流，这里用「过期前 5 分钟才刷新」策略。
  2. 只读优先 —— 采集接口全部是 GET；发消息是推送层的职责，不在本模块。
  3. 可降级 —— 凭证缺失或权限未开通时抛 SourceUnavailableError，
     由 collect_with_fallback 切到下一个数据源。

重要限制（写进 design.md 的已知约束）：
  用 tenant_access_token 调用任务接口，只能读到「该应用自己创建的任务」，
  读不到其他成员创建的任务。要读全队任务，需要每个成员用
  user_access_token 授权一次 —— 这是第 2 周需要权衡的设计点。
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from .base import SourceUnavailableError
from .models import MessageEntry, RawRecord, TaskEntry

FEISHU_API = "https://open.feishu.cn/open-apis"
# token 剩余不足这个秒数就提前刷新，避免边界失败
_TOKEN_REFRESH_MARGIN = 300


class FeishuCollector:
    """飞书数据采集器。

    用法：
        collector = FeishuCollector.from_env()
        tasks = collector.collect_tasks(since=..., until=...)
        msgs = collector.collect_messages(chat_id="oc_xxx", since=...)
    """

    name = "feishu"

    def __init__(
        self,
        app_id: str,
        app_secret: str,
        timeout: float = 15.0,
    ) -> None:
        if not app_id or not app_secret:
            raise SourceUnavailableError("FEISHU_APP_ID / FEISHU_APP_SECRET 未设置")
        self.app_id = app_id
        self.app_secret = app_secret
        self._token: str | None = None
        self._token_expire_at: float = 0.0
        self._client = httpx.Client(
            base_url=FEISHU_API,
            timeout=timeout,
            headers={"Content-Type": "application/json; charset=utf-8"},
        )

    @classmethod
    def from_env(cls) -> "FeishuCollector":
        """从环境变量构造。

        Raises:
            SourceUnavailableError: 凭证缺失
        """
        app_id = os.getenv("FEISHU_APP_ID", "").strip()
        app_secret = os.getenv("FEISHU_APP_SECRET", "").strip()
        if not app_id or not app_secret:
            raise SourceUnavailableError("FEISHU_APP_ID / FEISHU_APP_SECRET 未设置，无法访问飞书 API")
        return cls(app_id=app_id, app_secret=app_secret)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "FeishuCollector":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ---------- 令牌管理 ----------

    def get_tenant_access_token(self, force_refresh: bool = False) -> str:
        """获取 tenant_access_token，带缓存。

        有效期约 2 小时（7200s），这里提前 5 分钟刷新。
        """
        now = time.time()
        if not force_refresh and self._token and now < self._token_expire_at - _TOKEN_REFRESH_MARGIN:
            return self._token

        resp = self._client.post(
            "/auth/v3/tenant_access_token/internal",
            json={"app_id": self.app_id, "app_secret": self.app_secret},
        )
        if resp.status_code != 200:
            raise SourceUnavailableError(f"获取 tenant_access_token 失败（HTTP {resp.status_code}）")
        data = resp.json()
        code = data.get("code")
        if code != 0:
            msg = data.get("msg", "未知错误")
            hint = ""
            if code in (10003, 99991663, 99991661):
                hint = "（App ID 或 App Secret 不正确）"
            elif code == 99991672:
                hint = "（应用未发布或版本未生效，请到「版本管理与发布」发布）"
            elif code == 21001:
                # 租户身份限制：密钥本身正确，但当前租户不具备 OpenAPI 调用资质。
                # 典型场景是个人版飞书租户 —— 需在飞书客户端创建「免费团队」
                # （创建者角色选「企业或组织负责人」），在新团队下重建自建应用。
                hint = (
                    "（租户身份限制：App ID / Secret 本身正确，但当前租户无 OpenAPI 调用资质。"
                    "个人版租户不支持开发自建应用，请在飞书客户端创建「免费团队」"
                    "（角色选企业或组织负责人），在新团队下重建应用并更换凭证）"
                )
            elif code == 10014:
                hint = "（App Secret 不正确）"
            raise SourceUnavailableError(f"获取 tenant_access_token 失败：{code} {msg}{hint}")
        token = data.get("tenant_access_token", "")
        if not token:
            raise SourceUnavailableError("响应中没有 tenant_access_token")
        self._token = token
        self._token_expire_at = now + float(data.get("expire", 7200))
        return token

    # ---------- 内部请求 ----------

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        token = self.get_tenant_access_token()
        resp = self._client.get(path, params=params, headers={"Authorization": f"Bearer {token}"})
        if resp.status_code == 401:
            # 令牌可能已过期，强制刷新一次再试
            token = self.get_tenant_access_token(force_refresh=True)
            resp = self._client.get(path, params=params, headers={"Authorization": f"Bearer {token}"})
        if resp.status_code == 403:
            raise SourceUnavailableError(f"权限不足（HTTP 403）：{path} —— 检查权限是否已申请并发版生效")
        if resp.status_code >= 400:
            raise SourceUnavailableError(f"飞书 API 返回 {resp.status_code}：{resp.text[:200]}")
        data = resp.json()
        if data.get("code") != 0:
            raise SourceUnavailableError(f"飞书 API 错误 {data.get('code')}：{data.get('msg', '')}")
        return data.get("data", {})

    # ---------- 对外接口 ----------

    def collect_tasks(
        self,
        since: datetime | None = None,
        until: datetime | None = None,
        completed: bool | None = None,
        page_size: int = 100,
        max_pages: int = 20,
    ) -> list[TaskEntry]:
        """采集任务列表。

        注意：用 tenant_access_token 只能读到本应用创建的任务，
        要读其他成员的任务需要 user_access_token 授权（见模块文档说明）。
        """
        out: list[TaskEntry] = []
        page_token: str | None = None
        for _ in range(max_pages):
            params: dict[str, Any] = {"page_size": min(page_size, 100)}
            if page_token:
                params["page_token"] = page_token
            if completed is not None:
                params["completed"] = "true" if completed else "false"
            if since:
                params["created_at_from"] = str(int(since.timestamp()))
            if until:
                params["created_at_to"] = str(int(until.timestamp()))

            data = self._get("/task/v1/tasks", params)
            for item in data.get("items", []):
                out.append(self._to_task(item))
            page_token = data.get("page_token")
            if not data.get("has_more") or not page_token:
                break
        out.sort(key=lambda t: t.created_at, reverse=True)
        return out

    def collect_messages(
        self,
        chat_id: str,
        since: datetime | None = None,
        until: datetime | None = None,
        page_size: int = 50,
        max_pages: int = 20,
    ) -> list[MessageEntry]:
        """采集指定群的历史消息。

        Args:
            chat_id: 群 ID（oc_ 开头），可在飞书客户端群设置里查看
        """
        out: list[MessageEntry] = []
        page_token: str | None = None
        for _ in range(max_pages):
            params: dict[str, Any] = {
                "container_id_type": "chat",
                "container_id": chat_id,
                "page_size": min(page_size, 50),
            }
            if page_token:
                params["page_token"] = page_token
            if since:
                params["start_time"] = str(int(since.timestamp()))
            if until:
                params["end_time"] = str(int(until.timestamp()))

            data = self._get("/im/v1/messages", params)
            for item in data.get("items", []):
                out.append(self._to_message(item, chat_id))
            page_token = data.get("page_token")
            if not data.get("has_more") or not page_token:
                break
        out.sort(key=lambda m: m.timestamp, reverse=True)
        return out

    def list_members(self, department_id: str = "0") -> list[dict[str, str]]:
        """列出通讯录成员（用于确定团队成员名单与 ID 映射）。

        department_id=0 表示从根部门开始取。
        """
        data = self._get("/contact/v3/users", {"department_id": department_id, "page_size": 50})
        members: list[dict[str, str]] = []
        for u in data.get("items", []):
            members.append(
                {
                    "user_id": u.get("user_id", ""),
                    "name": u.get("name", ""),
                    "email": u.get("email", "") or u.get("enterprise_email", ""),
                    "department_ids": ",".join(u.get("department_ids", []) or []),
                }
            )
        return members

    def list_chats(self) -> list[dict[str, str]]:
        """列出应用所在群（用于发现 chat_id）。需要把机器人拉进群才会有结果。"""
        data = self._get("/im/v1/chats", {"page_size": 100})
        return [
            {"chat_id": c.get("chat_id", ""), "name": c.get("name", "")}
            for c in data.get("items", [])
        ]

    # ---------- 转换 ----------

    @staticmethod
    def _parse_ts(value: Any) -> datetime | None:
        """飞书时间戳是秒级字符串或毫秒级数字，统一转 datetime。"""
        if value in (None, "", 0, "0"):
            return None
        try:
            ts = int(value)
        except (TypeError, ValueError):
            return None
        if ts > 10**11:  # 毫秒级
            ts //= 1000
        return datetime.fromtimestamp(ts, tz=timezone.utc)

    @classmethod
    def _to_task(cls, item: dict[str, Any]) -> TaskEntry:
        creator = item.get("creator", {}) or {}
        created = cls._parse_ts(item.get("created_at"))
        completed_at = cls._parse_ts(item.get("completed_at"))
        return TaskEntry(
            task_id=item.get("id", "") or item.get("task_id", ""),
            summary=item.get("summary", "") or item.get("title", ""),
            description=item.get("description", "") or "",
            creator_id=creator.get("id", ""),
            creator_name=creator.get("name", "") or creator.get("en_name", ""),
            created_at=created or datetime.now(timezone.utc),
            completed_at=completed_at,
            completed=bool(item.get("completed", False)),
            members=[m.get("id", "") for m in (item.get("members", []) or [])],
            due=cls._parse_ts(item.get("due", {}).get("timestamp") if isinstance(item.get("due"), dict) else None),
            url=item.get("url", ""),
        )

    @classmethod
    def _to_message(cls, item: dict[str, Any], chat_id: str) -> MessageEntry:
        body = item.get("body", {}) or {}
        content = body.get("content", "")
        text, mentions = cls._flatten_content(content)
        sender = item.get("sender", {}) or {}
        sender_id = (sender.get("id", {}) or {}).get("open_id", "") or sender.get("id", "")
        ts = cls._parse_ts(item.get("create_time"))
        return MessageEntry(
            message_id=item.get("message_id", ""),
            chat_id=item.get("chat_id", chat_id),
            sender_id=sender_id,
            sender_name="",  # 需要用通讯录接口补全，见 resolve_member_names
            timestamp=ts or datetime.now(timezone.utc),
            text=text,
            msg_type=item.get("msg_type", "text"),
            mentions=mentions,
            thread_id=item.get("thread_id") or item.get("root_id"),
        )

    @staticmethod
    def _flatten_content(content: str) -> tuple[str, list[str]]:
        """把飞书消息的 JSON 内容拍平成纯文本，同时提取 @提及。

        飞书不同消息类型的 content 结构不同：
            text   -> {"text": "..."}
            post   -> {"title": "...", "content": [[{"tag":"text","text":"..."}]]}
            其他类型统一取字符串
        """
        import json

        mentions: list[str] = []
        if not content:
            return "", mentions
        try:
            data = json.loads(content)
        except (ValueError, TypeError):
            return str(content), mentions

        if isinstance(data, str):
            return data, mentions
        if not isinstance(data, dict):
            return str(data), mentions

        if "text" in data and isinstance(data["text"], str):
            return data["text"], mentions

        parts: list[str] = []
        if isinstance(data.get("title"), str):
            parts.append(data["title"])

        def walk(node: Any) -> None:
            if isinstance(node, dict):
                tag = node.get("tag")
                if tag == "at":
                    name = node.get("user_name") or node.get("user_id") or ""
                    if name:
                        mentions.append(name)
                    parts.append(f"@{name}")
                    return
                if tag in ("text", "a") and isinstance(node.get("text"), str):
                    parts.append(node["text"])
                    if tag == "a" and node.get("href"):
                        parts.append(f"({node['href']})")
                    return
                for v in node.values():
                    walk(v)
            elif isinstance(node, list):
                for v in node:
                    walk(v)

        walk(data.get("content", []))
        return " ".join(p for p in parts if p), mentions

    def resolve_member_names(self, entries: list[MessageEntry]) -> list[MessageEntry]:
        """用通讯录把消息里的 open_id 补成姓名。

        返回新列表（原 entries 不变，MessageEntry 是冻结的）。
        """
        try:
            members = self.list_members()
        except SourceUnavailableError:
            return entries
        id_to_name = {m["user_id"]: m["name"] for m in members if m["user_id"]}
        if not id_to_name:
            return entries
        from dataclasses import replace

        return [
            replace(e, sender_name=id_to_name.get(e.sender_id, e.sender_name))
            for e in entries
        ]

    # ---------- WorkSource 协议实现 ----------

    def collect(
        self,
        *,
        since: datetime | None = None,
        until: datetime | None = None,
        author: str | None = None,
    ) -> list[RawRecord]:
        """WorkSource 协议方法：采集任务 + 群消息。

        任务与消息合并返回 —— 两者都是「工作痕迹」，
        由 collect_with_fallback 统一归一化成 WorkItem。

        消息采集需要 chat_id：优先从 list_chats() 自动发现（需把机器人拉进群），
        找不到时降级为「只采任务」，不因消息缺失而整体失败。

        重要：若「任务」和「消息」两条通道**全部**不可用，必须抛
        SourceUnavailableError —— 否则降级链会误判本源成功（返回空列表），
        导致排在后面的兜底源被跳过，主流程产出空日报。
        """
        out: list[MessageEntry | TaskEntry] = []
        errors: list[str] = []
        tasks_ok = False

        try:
            out.extend(self.collect_tasks(since=since, until=until))
            tasks_ok = True
        except SourceUnavailableError as exc:
            errors.append(f"任务：{exc}")
            print(f"[feishu] 任务采集不可用：{exc}")

        chat_id = os.getenv("FEISHU_CHAT_ID", "").strip()
        if not chat_id:
            try:
                chats = self.list_chats()
                chat_id = chats[0]["chat_id"] if chats else ""
            except SourceUnavailableError as exc:
                errors.append(f"群列表：{exc}")
                print(f"[feishu] 群列表不可用：{exc}")
        if chat_id:
            try:
                msgs = self.collect_messages(chat_id, since=since, until=until)
                out.extend(self.resolve_member_names(msgs))
            except SourceUnavailableError as exc:
                errors.append(f"消息：{exc}")
                print(f"[feishu] 消息采集不可用：{exc}")
        else:
            print("[feishu] 未找到可用群（需把机器人拉进群），本期只采任务")

        # 两条通道都不可用 → 本源视为不可用，交给降级链处理
        if not tasks_ok and errors:
            raise SourceUnavailableError("飞书数据源全部通道不可用 -> " + " | ".join(errors))

        return out
