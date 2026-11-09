"""阶段 A · 最小连通性测试脚本（第 1 周分工单 · 赵蕊）

只做三件事（分工单步骤 3）：
1. 往飞书 Webhook 发一条固定文本「连通性测试日报」（含「日报」二字，避开 19024 关键词拒收）。
2. 签名直接复用 src/smart_daily/push/notifiers.py 的 gen_sign()，不另写一套算法。
3. 把 HTTP 状态码与飞书返回 code 打到 Actions 日志（0=成功；19021 签名 / 19022 IP 白名单 / 19024 关键词）。

本脚本不做任何业务逻辑，不读采集层，不写库。
凭证只从环境变量读，绝不打印 URL 与密钥原文。
"""

from __future__ import annotations

import os
import sys
import time

import httpx

# 复用推送层已有的签名实现（分工单要求：不要另写一套算法）
from smart_daily.push.notifiers import gen_sign


def main() -> int:
    url = os.getenv("FEISHU_WEBHOOK_URL", "").strip()
    secret = os.getenv("FEISHU_WEBHOOK_SECRET", "").strip()

    if not url or not secret:
        print("[test] 失败：FEISHU_WEBHOOK_URL / FEISHU_WEBHOOK_SECRET 未配置（Secrets 缺失）")
        return 1

    text = "连通性测试日报"
    timestamp = str(int(time.time()))
    sign = gen_sign(timestamp, secret)

    payload = {
        "msg_type": "text",
        "content": {"text": text},
        "timestamp": timestamp,
        "sign": sign,
    }

    start = time.monotonic()
    try:
        resp = httpx.post(url, json=payload, timeout=15)
    except Exception as exc:  # 网络层失败：境外 runner 连不上飞书
        elapsed = time.monotonic() - start
        print(f"[test] HTTP 请求异常（耗时 {elapsed:.2f}s）：{type(exc).__name__}: {exc}")
        return 1
    elapsed = time.monotonic() - start

    print(f"[test] HTTP 状态码: {resp.status_code}")
    print(f"[test] 耗时: {elapsed:.2f}s")
    try:
        body = resp.json()
    except Exception:
        print(f"[test] 响应体非 JSON: {resp.text[:200]}")
        return 1

    code = body.get("code")
    msg = body.get("msg", "")
    print(f"[test] 飞书返回 code: {code}  msg: {msg}")

    if code == 0:
        print("[test] 连通性测试通过：境外 runner 可直达飞书 Webhook，签名与关键词均放行")
        return 0

    hints = {
        19021: "签名校验失败（检查 FEISHU_WEBHOOK_SECRET 与 gen_sign 用法）",
        19022: "IP 白名单拦截（机器人开了 IP 白名单，需放行 GitHub runner 出口或关闭白名单）",
        19024: "关键词不匹配（消息未含机器人设置的关键词）",
    }
    print(f"[test] 连通性测试未通过：{hints.get(code, '见飞书开放平台错误码文档')}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
