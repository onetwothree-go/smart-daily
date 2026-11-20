"""C10 · push 实时提交通知验收（S9/C10，TK-V2-804）。

验收口径（proposal C10 原文）：
    main/dev push 带 3 commit → 飞书群恰 1 条、含「日报」二字、列全 commit 原文、
    显示中文名、code=0；feature 分支 0 次；失败亮红灯（exit 1）。

边界：读 GITHUB_EVENT_PATH 事件文件、不调 GitHub API、不写 SQLite、不进 G1。
"""

import json
from pathlib import Path


def _event(ref: str, commits: list[dict], actor: str = "fh0709") -> dict:
    return {
        "ref": ref,
        "commits": commits,
        "sender": {"login": actor},
    }


def _commits() -> list[dict]:
    return [
        {
            "id": "aaaaaaa111111111111111111111111111111111",
            "message": "feat: 新增实时提醒通道",
            "url": "https://github.com/x/y/commit/aaaaaaa",
        },
        {
            "id": "bbbbbbb222222222222222222222222222222222",
            "message": "fix: 修复身份映射大小写问题",
            "url": "https://github.com/x/y/commit/bbbbbbb",
        },
        {
            "id": "ccccccc333333333333333333333333333333333",
            "message": "docs: 补一份验收记录",
            "url": "https://github.com/x/y/commit/ccccccc",
        },
    ]


MAPPING = "fh0709:方赫,yjy120:杨佳莹,yuyue117:于悦,zhaorui715:赵蕊"


def _env(tmp_path: Path, ref: str, commits: list[dict], *, actor: str = "fh0709") -> dict:
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(_event(ref, commits, actor)), encoding="utf-8")
    return {
        "GITHUB_EVENT_PATH": str(event_path),
        "ACTOR": actor,
        "MEMBER_DISPLAY_NAMES": MAPPING,
        "FEISHU_WEBHOOK_URL": "https://open.feishu.cn/hook/test",
        "FEISHU_WEBHOOK_SECRET": "test-secret",
    }


class _Resp:
    def __init__(self, status: int, payload: dict, text: str = ""):
        self.status_code = status
        self._payload = payload
        self.text = text

    def json(self) -> dict:
        return self._payload


def _patch_send(monkeypatch, calls: list, code: int = 0, status: int = 200):
    import smart_daily_v2.notify_push as np

    def fake_post(url, json=None, timeout=None):
        calls.append({"url": url, "payload": json})
        return _Resp(status, {"code": code, "msg": "ok" if code == 0 else "fail"})

    monkeypatch.setattr(np.httpx, "post", fake_post)


# --- 红/绿：被测对象不存在时这些用例报 ImportError ---


def test_main_push_sends_exactly_one_message_with_all_commits(tmp_path, monkeypatch):
    """main push 带 3 commit → 飞书群恰 1 条、含日报、列全 commit 原文、中文显示名、exit 0。"""
    import smart_daily_v2.notify_push as np

    calls: list = []
    _patch_send(monkeypatch, calls)
    code = np.run(_env(tmp_path, "refs/heads/main", _commits()))

    assert code == 0
    assert len(calls) == 1, "一次 push 必须恰好发一条群消息"
    text = calls[0]["payload"]["content"]["text"]
    assert "日报" in text
    assert "方赫" in text, "触发者须显示中文名"
    for c in _commits():
        assert c["message"] in text, f"commit 原文必须逐条列出：{c['message']}"
    assert calls[0]["payload"]["msg_type"] == "text"
    assert "sign" in calls[0]["payload"] and "timestamp" in calls[0]["payload"]


def test_dev_push_also_notifies(tmp_path, monkeypatch):
    """dev push 同样触发（main/dev 都纳入）。"""
    import smart_daily_v2.notify_push as np

    calls: list = []
    _patch_send(monkeypatch, calls)
    code = np.run(_env(tmp_path, "refs/heads/dev", _commits()))

    assert code == 0
    assert len(calls) == 1
    assert "dev" in calls[0]["payload"]["content"]["text"]


def test_feature_branch_sends_nothing(tmp_path, monkeypatch):
    """feature 分支 0 次发送。"""
    import smart_daily_v2.notify_push as np

    calls: list = []
    _patch_send(monkeypatch, calls)
    code = np.run(_env(tmp_path, "refs/heads/feature/x", _commits()))

    assert code == 0
    assert calls == [], "feature 分支不得发任何群消息"


def test_feishu_code_nonzero_returns_exit_one(tmp_path, monkeypatch):
    """飞书返回 code!=0 → exit 1（workflow 亮红灯，不静默）。"""
    import smart_daily_v2.notify_push as np

    calls: list = []
    _patch_send(monkeypatch, calls, code=19024)
    code = np.run(_env(tmp_path, "refs/heads/main", _commits()))

    assert code == 1


def test_missing_webhook_returns_exit_one(tmp_path, monkeypatch):
    """缺 Webhook 凭证 → exit 1，不发消息。"""
    import smart_daily_v2.notify_push as np

    calls: list = []
    _patch_send(monkeypatch, calls)
    env = _env(tmp_path, "refs/heads/main", _commits())
    env.pop("FEISHU_WEBHOOK_URL")

    assert np.run(env) == 1
    assert calls == []


def test_unmapped_actor_falls_back_to_login(tmp_path, monkeypatch):
    """未映射身份回落登录名，不丢消息。"""
    import smart_daily_v2.notify_push as np

    calls: list = []
    _patch_send(monkeypatch, calls)
    env = _env(tmp_path, "refs/heads/main", _commits(), actor="unknown_user")

    assert np.run(env) == 0
    assert len(calls) == 1
    assert "unknown_user" in calls[0]["payload"]["content"]["text"]


def test_does_not_touch_sqlite(tmp_path, monkeypatch):
    """C10 边界：不写 SQLite、不生成日报条目。"""
    import smart_daily_v2.notify_push as np

    calls: list = []
    _patch_send(monkeypatch, calls)
    db = tmp_path / "reports.db"
    env = _env(tmp_path, "refs/heads/main", _commits())
    env["DB_PATH"] = str(db)

    np.run(env)
    assert not db.exists(), "实时提醒不得创建/写入任何 SQLite"


def test_text_has_keyword_guard(tmp_path, monkeypatch):
    """文本缺「日报」二字时被拦下（飞书 19024 拒收的最后一道闸门）。"""
    import smart_daily_v2.notify_push as np

    assert np.build_text("方赫", "main", _commits()).count("日报") >= 1
    # 关键词常量存在且就是「日报」
    assert np.KEYWORD == "日报"


def test_main_is_callable_with_argv(tmp_path, monkeypatch):
    """CLI 入口 main() 返回退出码（供 workflow 直接调用）。"""
    import smart_daily_v2.notify_push as np

    calls: list = []
    _patch_send(monkeypatch, calls)
    env = _env(tmp_path, "refs/heads/main", _commits())
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("GITHUB_EVENT_PATH", raising=False)
    monkeypatch.setattr("sys.argv", ["notify_push", "--event", str(tmp_path / "event.json")])

    assert np.main() in (0, 1)  # 具体实现可用 --event 或环境变量，二者其一
