"""push 实时提交通知（S9 / C10，TK-V2-803 · 范围外新增，状态 ☐ 待确认）。

把一次 push 合并成恰好 1 条飞书群提醒。独立链路：
    - 读 GITHUB_EVENT_PATH 事件文件，不调 GitHub API、不需要 token；
    - 只处理 main / dev（由 workflow 的 branches 过滤，本模块再兜底判一次）；
    - 不写 SQLite、不走采集层、不生成日报条目、不进 G1 计数。

复用 v2 已有能力（零复制：不 import v1、不复制 v1 源码）：
    - identity.display_name() 做登录名→中文名（casefold、未命中回落）；
    - notifiers.webhook.gen_sign() 做飞书签名。

输入（Actions 注入）：GITHUB_EVENT_PATH / ACTOR / MEMBER_DISPLAY_NAMES /
FEISHU_WEBHOOK_URL / FEISHU_WEBHOOK_SECRET。
退出码：0 = 未触发或飞书返回 code 0；1 = 任一环节失败（workflow 亮红灯）。
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import httpx

from smart_daily_v2.identity import display_name, normalize_key
from smart_daily_v2.notifiers.webhook import gen_sign

KEYWORD = "日报"  # 飞书自定义机器人关键词，缺了被 19024 拒收
TITLE_LIMIT = 60
TIMEOUT = 15.0
BEIJING = timezone(timedelta(hours=8))
TARGET_BRANCHES = {"main", "dev"}


def warn(message: str) -> None:
    print(f"::warning::{message}")


def load_event(env: dict[str, str]) -> dict:
    """读取 runner 注入的 push 事件文件（不调 GitHub API）。"""
    path = env.get("GITHUB_EVENT_PATH", "")
    if not path:
        print("错误：缺少 GITHUB_EVENT_PATH（应运行在 GitHub Actions 中）", file=sys.stderr)
        raise ValueError("GITHUB_EVENT_PATH missing")
    with open(path, encoding="utf-8") as fp:
        event = json.load(fp)
    if not isinstance(event, dict):
        raise ValueError("event file is not a JSON object")
    return event


def branch_of(event: dict) -> str:
    return (event.get("ref") or "").rsplit("/", 1)[-1]


def short_title(message: str) -> str:
    title = message.strip().splitlines()[0].strip() if message.strip() else ""
    if not title:
        return "(无提交说明)"
    return title if len(title) <= TITLE_LIMIT else title[:TITLE_LIMIT] + "…"


def build_text(actor_name: str, branch: str, commits: list[dict]) -> str:
    """拼一条提醒文本：中文名 + 分支 + 条数 + 全部 commit 原文 + 链接 + 时间。

    必须含「日报」二字，否则被飞书 19024 拒收。
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


def post_to_feishu(text: str, url: str, secret: str) -> int:
    """发送文本消息；非 0 / 异常一律返回 1（不静默、不重试）。"""
    timestamp = str(int(time.time()))
    payload: dict = {
        "msg_type": "text",
        "content": {"text": text},
        "timestamp": timestamp,
    }
    if secret:
        payload["sign"] = gen_sign(int(timestamp), secret)
    try:
        response = httpx.post(url, json=payload, timeout=TIMEOUT)
    except httpx.HTTPError as exc:
        print(f"发送失败：网络异常 {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    if response.status_code != 200:
        print(f"发送失败：HTTP {response.status_code}", file=sys.stderr)
        return 1
    try:
        body = response.json()
    except ValueError:
        print("发送失败：响应不是 JSON", file=sys.stderr)
        return 1
    code = body.get("code")
    print(f"飞书返回：code={code}")
    return 0 if code == 0 else 1


def run(env: dict[str, str]) -> int:
    """核心逻辑，返回退出码。便于测试注入；CLI 用 os.environ 调。"""
    url = env.get("FEISHU_WEBHOOK_URL", "").strip()
    secret = env.get("FEISHU_WEBHOOK_SECRET", "").strip()
    if not url:
        print("错误：缺少 FEISHU_WEBHOOK_URL（应由 Secrets 注入）", file=sys.stderr)
        return 1

    try:
        event = load_event(env)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"错误：读取事件失败：{exc}", file=sys.stderr)
        return 1

    branch = branch_of(event)
    if branch not in TARGET_BRANCHES:
        print(f"分支 {branch!r} 不在 {sorted(TARGET_BRANCHES)}，跳过提醒（exit 0）")
        return 0

    actor = env.get("ACTOR", "").strip() or (event.get("sender") or {}).get("login", "")
    if not actor:
        warn("缺少 ACTOR 且事件无 sender.login，显示名回落为空")
    actor_name = display_name(actor, env.get("MEMBER_DISPLAY_NAMES", ""))
    if normalize_key(actor_name) == normalize_key(actor or ""):
        warn(f"身份未映射：{actor!r}，回落显示登录名")

    commits = event.get("commits") or []
    if not isinstance(commits, list):
        print("错误：事件里的 commits 不是数组", file=sys.stderr)
        return 1

    text = build_text(actor_name, branch, commits)
    if KEYWORD not in text:
        print(f"错误：提醒文本不含关键词「{KEYWORD}」，已拒发", file=sys.stderr)
        return 1
    print("--- 待发送文本 ---")
    print(text)
    print("----------------")
    return post_to_feishu(text, url, secret)


def main(argv: list[str] | None = None) -> int:
    """CLI 入口：环境变量为主，可用 --event 覆盖事件文件路径。"""
    args = list(sys.argv[1:] if argv is None else argv)
    env = dict(os.environ)
    if "--event" in args:
        idx = args.index("--event")
        if idx + 1 >= len(args):
            print("错误：--event 缺少路径", file=sys.stderr)
            return 1
        env["GITHUB_EVENT_PATH"] = args[idx + 1]
    return run(env)


if __name__ == "__main__":
    sys.exit(main())
