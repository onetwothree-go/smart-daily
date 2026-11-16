"""推送层 —— 把生成的日报送到人手里

两种推送通道：
    EmailNotifier    —— SMTP 发邮件（给个人日报）
    FeishuWebhookNotifier —— 飞书自定义机器人 Webhook（给团队日报）

设计要点：
  1. 通道可替换 —— 两种通道实现同一个 Notifier 协议，
     主编排层不关心具体用哪个通道（与采集层同构）。
  2. 失败不阻断 —— 推送失败记录并返回 False，不让日报生成流程整体崩掉。
  3. 凭证只从环境变量读 —— SMTP 授权码、飞书 Webhook 都在 .env 里。
"""

# --- 答辩口径 · 推送层通道（见答辩稿 2.6.1）---
# Notifier 协议由 EmailNotifier / FeishuWebhookNotifier / MultiNotifier 实现。
# gen_sign() 是 HMAC-SHA256 + Base64 飞书签名的单点实现，实时提醒链路复用（RT-07）。
# 失败只返回 False 不抛异常：推送失败不该让已落库的日报丢掉（design 3.4 / C7）；
# 飞书判 code == 0 才算成功，19021 / 19022 / 19024 给中文提示。

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import smtplib
import time
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Protocol, runtime_checkable

import httpx


def gen_sign(timestamp: str, secret: str) -> str:
    """生成飞书自定义机器人的签名。

    官方算法（开放平台「自定义机器人使用指南」）：
        string_to_sign = f"{timestamp}\\n{secret}"
        sign = base64(hmac_sha256(string_to_sign, key=string_to_sign, msg=b""))

    Args:
        timestamp: 秒级时间戳字符串，距当前不超过 1 小时
        secret: 机器人的签名密钥

    Returns:
        Base64 编码后的签名字符串
    """
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(
        string_to_sign.encode("utf-8"), digestmod=hashlib.sha256
    ).digest()
    return base64.b64encode(hmac_code).decode("utf-8")


@runtime_checkable
class Notifier(Protocol):
    """推送通道协议。"""

    name: str

    def send(self, subject: str, body: str, recipients: list[str]) -> bool:
        """发送一条通知。

        Returns:
            True 表示成功，False 表示失败（失败不应中断主流程）。
        """
        ...


@dataclass
class EmailNotifier:
    """SMTP 邮件推送。

    典型用法：发个人日报给本人。
    """

    host: str
    port: int
    user: str
    password: str
    use_ssl: bool = True
    sender: str = ""

    #: 通道名 —— Notifier 协议要求，日志与推送明细里用它标识通道
    name: str = "email"

    @classmethod
    def from_env(cls) -> "EmailNotifier":
        """从环境变量构造。

        Raises:
            ValueError: 凭证缺失
        """
        host = os.getenv("SMTP_HOST", "smtp.qq.com").strip()
        port = int(os.getenv("SMTP_PORT", "465"))
        user = os.getenv("SMTP_USER", "").strip()
        password = os.getenv("SMTP_PASSWORD", "").strip()
        if not user or not password:
            raise ValueError("SMTP_USER / SMTP_PASSWORD 未设置")
        return cls(
            host=host,
            port=port,
            user=user,
            password=password,
            use_ssl=port == 465,
            sender=os.getenv("SMTP_SENDER", user).strip() or user,
        )

    def send(self, subject: str, body: str, recipients: list[str]) -> bool:
        """发送邮件。失败返回 False 并打印原因，不抛出异常。"""
        if not recipients:
            print("[email] 无收件人，跳过")
            return False
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.sender
        msg["To"] = ", ".join(recipients)
        msg.set_content(body)
        try:
            if self.use_ssl:
                with smtplib.SMTP_SSL(self.host, self.port, timeout=20) as server:
                    server.login(self.user, self.password)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(self.host, self.port, timeout=20) as server:
                    server.starttls()
                    server.login(self.user, self.password)
                    server.send_message(msg)
        except Exception as exc:  # noqa: BLE001 - 推送失败不应中断主流程
            print(f"[email] 发送失败：{type(exc).__name__}: {exc}")
            return False
        print(f"[email] 已发送给 {len(recipients)} 人")
        return True


@dataclass
class FeishuWebhookNotifier:
    """飞书自定义机器人 Webhook 推送。

    典型用法：把团队日报推到项目群。

    Webhook 地址的获取：飞书群设置 → 添加机器人 → 自定义机器人 → 复制地址。
    这种方式不需要审核、不需要应用能力，是最快的落地路径。

    安全设置（机器人后台「安全设置」区）：
        - 自定义关键词：消息正文须含该关键词。代码推送的标题固定含
          「日报」二字（个人日报 / 团队日报 / 连通性测试），因此推荐
          关键词填「日报」。
        - 签名校验：配置 secret 后自动带上 timestamp + sign 字段。
        - IP 白名单：与代码无关，取决于部署机器的出口 IP。
    """

    webhook_url: str
    timeout: float = 15.0

    #: 签名密钥。为空表示机器人未开启签名校验，请求体不带 sign 字段。
    secret: str = ""

    #: 通道名 —— Notifier 协议要求，日志与推送明细里用它标识通道
    name: str = "feishu-webhook"

    @classmethod
    def from_env(cls) -> "FeishuWebhookNotifier":
        """从环境变量构造。

        Raises:
            ValueError: Webhook 未设置
        """
        url = os.getenv("FEISHU_WEBHOOK_URL", "").strip()
        if not url:
            raise ValueError("FEISHU_WEBHOOK_URL 未设置")
        secret = os.getenv("FEISHU_WEBHOOK_SECRET", "").strip()
        return cls(webhook_url=url, secret=secret)

    def send(self, subject: str, body: str, recipients: list[str] | None = None) -> bool:
        """推送文本消息到群。失败返回 False。"""
        text = f"{subject}\n\n{body}"
        payload: dict[str, object] = {
            "msg_type": "text",
            "content": {"text": text},
        }
        if self.secret:
            # 机器人开启了签名校验 —— 必须带上 timestamp 与 sign，否则返回 19021
            timestamp = str(int(time.time()))
            payload["timestamp"] = timestamp
            payload["sign"] = gen_sign(timestamp, self.secret)
        try:
            resp = httpx.post(self.webhook_url, json=payload, timeout=self.timeout)
        except httpx.HTTPError as exc:
            print(f"[feishu-webhook] 请求失败：{exc}")
            return False
        if resp.status_code != 200:
            print(f"[feishu-webhook] 返回 HTTP {resp.status_code}：{resp.text[:150]}")
            return False
        try:
            data = resp.json()
        except ValueError:
            print("[feishu-webhook] 响应不是合法 JSON")
            return False
        # 飞书 Webhook 成功时返回 code=0，失败时返回非 0 且带 msg
        if data.get("code", 0) != 0:
            code = data.get("code")
            hint = ""
            if code == 19021:
                hint = "（签名校验失败：检查 FEISHU_WEBHOOK_SECRET 是否填对）"
            elif code == 19024:
                hint = "（机器人设了自定义关键词，消息正文必须包含该关键词）"
            elif code == 19022:
                hint = "（机器人设了 IP 白名单，当前出口 IP 不在名单里）"
            print(f"[feishu-webhook] 推送失败：{code} {data.get('msg')}{hint}")
            return False
        print("[feishu-webhook] 已推送")
        return True


@dataclass
class MultiNotifier:
    """组合多个通道，任一成功即视为成功。"""

    notifiers: list[Notifier]

    #: 通道名 —— Notifier 协议要求
    name: str = "multi"

    def send(self, subject: str, body: str, recipients: list[str]) -> bool:
        """依次尝试各通道，返回是否有任一通道成功。"""
        if not self.notifiers:
            print("[notify] 无可用通道")
            return False
        results = []
        for n in self.notifiers:
            try:
                results.append(bool(n.send(subject, body, recipients)))
            except Exception as exc:  # noqa: BLE001
                print(f"[notify] 通道 {n.name} 异常：{exc}")
                results.append(False)
        return any(results)
