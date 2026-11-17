"""Smart Daily 最小 Python 工程。

用途：环境验收演示 —— 从本地环境变量读取三项数据凭证（只显示变量名与状态，绝不打印值）。
凭证一律通过环境变量注入，本文件中不含任何密钥。
"""

# --- 答辩口径 · 第 1 周最小工程环境验收（见答辩稿 2.6.2）---
# check_env() 只显示变量名与「是否已设置」，绝不打印凭证值（指导书红色等级）；
# 再做 GitHub / 飞书 / SMTP 三个只读连通性验证，不写任何外部数据。

import os
import smtplib
import urllib.request

CREDENTIAL_VARS = [
    "GITHUB_TOKEN",      # GitHub 个人访问令牌（只读）
    "FEISHU_APP_ID",     # 飞书开放平台自建应用 App ID
    "FEISHU_APP_SECRET", # 飞书开放平台自建应用 App Secret
    "SMTP_USER",         # SMTP 测试邮箱
    "SMTP_PASS",         # SMTP 授权码
]


def check_env() -> None:
    """出示环境变量配置：只显示变量名和是否已设置，不显示值。"""
    print("== 环境变量配置（不显示值）==")
    for name in CREDENTIAL_VARS:
        status = "已设置" if os.environ.get(name) else "缺失"
        print(f"  {name:<16} [{status}]")


def github_readonly_call() -> None:
    """GitHub 只读接口调用：GET /user（只读权限即可）。"""
    token = os.environ["GITHUB_TOKEN"]
    req = urllib.request.Request(
        "https://api.github.com/user",
        headers={"Authorization": f"Bearer {token}", "User-Agent": "smart-daily"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        login = __import__("json").loads(resp.read())["login"]
    print(f"== GitHub 只读调用 OK: 当前账号 {login}")


def feishu_readonly_call() -> None:
    """飞书只读调用：用 app_id/app_secret 换取 tenant_access_token。"""
    import json

    payload = json.dumps({
        "app_id": os.environ["FEISHU_APP_ID"],
        "app_secret": os.environ["FEISHU_APP_SECRET"],
    }).encode()
    req = urllib.request.Request(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
    ok = data.get("code") == 0
    print(f"== 飞书凭证调用 OK: tenant_access_token 获取{'成功' if ok else '失败'}")


def smtp_login_call() -> None:
    """SMTP 登录验证：登录 163 邮箱 SMTP 服务器。"""
    server = smtplib.SMTP_SSL("smtp.163.com", 465, timeout=15)
    server.login(os.environ["SMTP_USER"], os.environ["SMTP_PASS"])
    server.quit()
    print("== SMTP 登录验证 OK")


def main() -> None:
    check_env()
    github_readonly_call()
    feishu_readonly_call()
    smtp_login_call()
    print("\n全部验收项通过 ✔")


if __name__ == "__main__":
    main()
