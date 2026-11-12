#!/usr/bin/env python3
"""push 实时提交通知 —— 把一次 push 合并成 1 条飞书群提醒。

对应规范：
    specs/design.md 3.5「实时提醒通道」、附录 A（C10）
    specs/proposal.md C10 / Q16-Q21

与其他模块的边界（分工单步骤 9「不写」）：
    - 不读 SQLite、不生成日报条目、不走采集层、不改 orchestrator.py
    - 22:00 汇总日报完全独立，本脚本一次都不计入 G1 的 1:1 计数（Q17）

输入全部来自 Actions 注入：
    GITHUB_EVENT_PATH     push 事件 JSON 文件（runner 自动注入，含 commits[] 与 ref）
    ACTOR                 github.actor，触发者登录名（归属键，ADR-104 ③）
    MEMBER_DISPLAY_NAMES  登录名:显示名 映射，明文入库（design 5.2 可入库级）
    FEISHU_WEBHOOK_URL    群机器人地址（Secret）
    FEISHU_WEBHOOK_SECRET 机器人签名密钥（Secret）

退出码：0 = 飞书返回 code 0；1 = 任一环节失败（让 workflow 亮红灯，Q21 要求可查痕迹）
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

# 签名算法单点实现：直接复用推送层的 gen_sign，不复制、不另写（ADR-104 ⑤）
# 只加 sys.path，不需要 pip install 整个包（notifiers.py 的依赖只有标准库 + httpx）
_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from smart_daily.push.notifiers import gen_sign  # noqa: E402

KEYWORD = "日报"          # 飞书自定义机器人关键词，缺了会被 19024 拒收
TITLE_LIMIT = 60          # 单条 message 标题截断长度（Q4：长消息标题取前 60 字）
TIMEOUT = 15.0            # 秒；与 notifiers.py 同层超时
BEIJING = timezone(timedelta(hours=8))


def warn(message: str) -> None:
    """打一条 Actions 告警注解（在运行摘要里高亮，不中断流程）。"""
    print(f"::warning::{message}")


def load_event() -> dict:
    """读取 runner 注入的 push 事件文件（不调 GitHub API）。"""
    path = os.getenv("GITHUB_EVENT_PATH")
    if not path:
        print("错误：缺少 GITHUB_EVENT_PATH（应运行在 GitHub Actions 中）", file=sys.stderr)
        raise SystemExit(1)
    with open(path, encoding="utf-8") as fp:
        event = json.load(fp)
    if not isinstance(event, dict):
        print(f"错误：事件文件不是 JSON 对象：{path}", file=sys.stderr)
        raise SystemExit(1)
    return event


def resolve_display_name(login: str, mapping_raw: str) -> str:
    """登录名 → 中文显示名。

    与 collectors/github.py::_display_name 同款解析逻辑（逗号分隔、冒号分键值），
    另做大小写不敏感匹配：GitHub 登录名本身不区分大小写，
    actor 返回的规范化写法（如 ZzzzzzzR）可能与映射里手写的键不同。
    未命中时**打告警并回落到登录名**，绝不静默丢记录（Q13 / design 3.5 契约 2）。
    """
    target = login.strip().lower()
    for pair in mapping_raw.split(","):
        pair = pair.strip()
        if ":" not in pair:
            continue
        key, value = pair.split(":", 1)
        if key.strip().lower() == target:
            return value.strip()
    warn(f"身份未映射：登录名 {login!r} 不在 MEMBER_DISPLAY_NAMES 中，已回落显示原始登录名")
    return login


def short_title(message: str) -> str:
    """取 commit message 首行作为标题：原文呈现、不改写、不摘要（Q4）。

    超过 TITLE_LIMIT 字时截断并加省略号，完整说明由后面的 commit 链接可查。
    """
    title = message.strip().splitlines()[0].strip() if message.strip() else ""
    if not title:
        return "(无提交说明)"
    return title if len(title) <= TITLE_LIMIT else title[:TITLE_LIMIT] + "…"


def build_text(actor_name: str, branch: str, commits: list[dict]) -> str:
    """拼一条提醒文本：中文名 + 分支 + 条数 + 全部 commit + 提交链接 + 时间。

    必须含「日报」二字，否则被 19024 拒收（C10 / design 3.3 约束 1）。
    """
    now = datetime.now(BEIJING).strftime("%Y-%m-%d %H:%M")
    lines = [f"【日报·提交通知】{actor_name} 向 {branch} 推送了 {len(commits)} 个提交"]

    if not commits:
        lines.append("（本次 push 未包含提交记录，可能是分支删除或强制推送）")
    else:
        for index, commit in enumerate(commits, start=1):
            sha = (commit.get("id") or "")[:7]
            title = short_title(commit.get("message") or "")
            url = commit.get("url") or ""
            lines.append(f"{index}. {sha} {title}")
            if url:
                lines.append(f"   {url}")

    lines.append(f"时间：{now}（北京时间）")
    return "\n".join(lines)


def post_to_feishu(text: str, webhook_url: str, secret: str) -> int:
    """发送文本消息，返回退出码。非 0 或异常一律 exit 1（Q21：不静默、不重试）。"""
    timestamp = str(int(time.time()))
    payload = {
        "msg_type": "text",
        "content": {"text": text},
        "timestamp": timestamp,
        "sign": gen_sign(timestamp, secret),
    }

    started = time.monotonic()
    try:
        response = httpx.post(webhook_url, json=payload, timeout=TIMEOUT)
    except httpx.HTTPError as exc:
        print(f"发送失败：网络异常 {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    elapsed = time.monotonic() - started

    print(f"HTTP 状态码：{response.status_code}｜耗时：{elapsed:.2f}s")
    try:
        body = response.json()
    except ValueError:
        print(f"发送失败：响应不是 JSON：{response.text[:200]}", file=sys.stderr)
        return 1

    code = body.get("code")
    msg = body.get("msg") or body.get("message") or ""
    print(f"飞书返回：code={code} msg={msg}")
    if code == 0:
        return 0

    hints = {
        19021: "签名校验不通过（检查 FEISHU_WEBHOOK_SECRET 与 gen_sign 算法）",
        19022: "IP 白名单限制（机器人安全设置里放行 GitHub Actions 出口 IP）",
        19024: f"关键词不匹配（消息必须含「{KEYWORD}」）",
    }
    print(f"发送失败：{hints.get(code, '未知错误码，查飞书自定义机器人文档')}", file=sys.stderr)
    return 1


def main() -> int:
    webhook_url = os.getenv("FEISHU_WEBHOOK_URL", "").strip()
    secret = os.getenv("FEISHU_WEBHOOK_SECRET", "").strip()
    if not webhook_url or not secret:
        print("错误：缺少 FEISHU_WEBHOOK_URL 或 FEISHU_WEBHOOK_SECRET（应由 Secrets 注入）", file=sys.stderr)
        return 1

    event = load_event()

    actor = os.getenv("ACTOR", "").strip()
    if not actor:
        actor = (event.get("sender") or {}).get("login", "")
        warn(f"缺少 ACTOR 环境变量，已回落到事件 sender.login（{actor or '未知'}）")

    actor_name = resolve_display_name(actor, os.getenv("MEMBER_DISPLAY_NAMES", ""))
    branch = (event.get("ref") or "").rsplit("/", 1)[-1] or "(未知分支)"
    commits = event.get("commits") or []
    if not isinstance(commits, list):
        print("错误：事件里的 commits 不是数组", file=sys.stderr)
        return 1

    text = build_text(actor_name, branch, commits)
    if KEYWORD not in text:
        # 正常构造不会走到这里；保留为最后一道闸门，避免 19024 事后排查
        print(f"错误：提醒文本不含关键词「{KEYWORD}」，已拒发", file=sys.stderr)
        return 1

    print("--- 待发送文本 ---")
    print(text)
    print("----------------")
    return post_to_feishu(text, webhook_url, secret)


if __name__ == "__main__":
    sys.exit(main())
