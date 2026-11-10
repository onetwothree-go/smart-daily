#!/usr/bin/env python3
"""第 1 周 TC-01~TC-08 离线集成验证（测试侧工具，不改任何产品代码）。

用途：
    在不真实打扰飞书群、不改动 src/ 与 scripts/ 的前提下，用打桩 httpx.post
    驱动真实的 scripts/notify_push.py::main()，验证通知链路的可判定行为。

运行（仓库根目录）：
    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe docs/testing/证据/W1-verify-notify-offline.py

纪律：
    - 只从 .github/workflows/notify.yml 读取公开的显示名映射，不读 .env、不读任何凭证值
    - 打桩响应只含飞书错误码，不写 URL / Secret / 邮箱
    - 输出可直接作为证据文本归档
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import re
import sys
import tempfile
import types
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

SPEC = importlib.util.spec_from_file_location(
    "notify_push_under_test", ROOT / "scripts" / "notify_push.py"
)
assert SPEC is not None and SPEC.loader is not None
np = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(np)

WORKFLOW = (ROOT / ".github/workflows/notify.yml").read_text(encoding="utf-8")
MAPPING_MATCH = re.search(r"MEMBER_DISPLAY_NAMES:\s*'([^']+)'", WORKFLOW)
assert MAPPING_MATCH, "workflow 中未找到 MEMBER_DISPLAY_NAMES"
MAPPING = MAPPING_MATCH.group(1)
PAIRS = [tuple(p.split(":", 1)) for p in MAPPING.split(",") if ":" in p]

RESULTS: list[tuple[str, str, str, str]] = []


def record(case: str, name: str, expected: str, actual: str) -> None:
    ok = actual == expected
    RESULTS.append((case, name, "PASS" if ok else "FAIL", f"期望={expected} 实际={actual}"))
    print(f"[{'PASS' if ok else 'FAIL'}] {case} {name} | 期望={expected} 实际={actual}")


class FakeResponse:
    def __init__(self, code: int) -> None:
        self._code = code
        self.status_code = 200
        self.text = json.dumps({"code": code, "msg": "stub"})

    def json(self) -> dict:
        return {"code": self._code, "msg": "stub"}


def event_payload(commits: list[dict], ref: str = "refs/heads/dev") -> dict:
    return {"ref": ref, "commits": commits, "sender": {"login": "fallback-actor"}}


def commit(i: int) -> dict:
    return {
        "id": f"{i:07d}abcdef0123456789",
        "message": f"第 {i} 个测试提交",
        "url": f"https://example.invalid/commit/{i:07d}",
    }


def run_main(
    *,
    actor: str,
    commits: list[dict],
    response_code: int = 0,
    mapping: str = MAPPING,
    ref: str = "refs/heads/dev",
) -> dict:
    """打桩跑一次 main()，返回退出码、输出、被发送的消息文本与调用次数。"""
    calls: list[dict] = []

    def fake_post(url: str, json: dict, timeout: float) -> FakeResponse:  # noqa: A002
        calls.append({"payload": json})
        return FakeResponse(response_code)

    fake_httpx = types.SimpleNamespace(
        post=fake_post, HTTPError=type("HTTPError", (Exception,), {})
    )

    with tempfile.TemporaryDirectory() as tmp:
        event_path = Path(tmp) / "event.json"
        event_path.write_text(
            json.dumps(event_payload(commits, ref), ensure_ascii=False), encoding="utf-8"
        )
        old_env = {k: os.environ.get(k) for k in
                   ("GITHUB_EVENT_PATH", "ACTOR", "MEMBER_DISPLAY_NAMES",
                    "FEISHU_WEBHOOK_URL", "FEISHU_WEBHOOK_SECRET")}
        old_httpx = np.httpx
        os.environ.update({
            "GITHUB_EVENT_PATH": str(event_path),
            "ACTOR": actor,
            "MEMBER_DISPLAY_NAMES": mapping,
            "FEISHU_WEBHOOK_URL": "https://example.invalid/stub",
            "FEISHU_WEBHOOK_SECRET": "stub-secret",
        })
        np.httpx = fake_httpx  # type: ignore[assignment]
        out, err = io.StringIO(), io.StringIO()
        try:
            with redirect_stdout(out), redirect_stderr(err):
                code = np.main()
        finally:
            np.httpx = old_httpx
            for k, v in old_env.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
        db_files = list(Path(tmp).glob("*.db")) + list(Path(tmp).glob("*.sqlite*"))
        return {
            "exit": code,
            "stdout": out.getvalue(),
            "stderr": err.getvalue(),
            "calls": calls,
            "db_files": len(db_files),
        }


def main() -> int:
    print("第 1 周 TC 离线集成验证")
    print("被测脚本：scripts/notify_push.py（原文件，未改动）")
    print("打桩方式：替换模块内 httpx.post，事件文件用临时 JSON，凭证用占位串")
    print(f"映射来源：.github/workflows/notify.yml 的 MEMBER_DISPLAY_NAMES，共 {len(PAIRS)} 条")
    print("-" * 72)

    # TC-02：8 个登录名/别名 -> 4 个中文名，含大小写不敏感
    resolved = {k: np.resolve_display_name(k, MAPPING) for k, _ in PAIRS}
    names = set(resolved.values())
    record("TC-02", "8 条映射全部命中", "True",
           str(all(v != k for k, v in resolved.items())))
    record("TC-02", "归并后中文名个数", "4", str(len(names)))
    record("TC-02", "大小写变体 ZZZZZZZR 归到赵蕊", "赵蕊",
           np.resolve_display_name("ZZZZZZZR", MAPPING))
    print("       映射逐条：" + "，".join(f"{k}→{v}" for k, v in resolved.items()))

    # TC-03：未映射身份回落 + 告警 + 不静默丢记录
    r = run_main(actor="outsider-dev", commits=[commit(1)])
    record("TC-03", "回落显示原始登录名", "True",
           str("outsider-dev 向 dev" in r["stdout"] or "outsider-dev" in r["stdout"].split("推送")[0]))
    record("TC-03", "Actions 告警注解存在", "True",
           str("::warning::身份未映射" in r["stdout"]))
    record("TC-03", "仍然发送（不静默丢记录）", "1", str(len(r["calls"])))
    record("TC-03", "退出码", "0", str(r["exit"]))

    # TC-05：飞书错误码 19024 / 19021 都让 workflow 失败
    for code, hint in ((19024, "关键词不匹配"), (19021, "签名校验不通过")):
        r = run_main(actor="fh0709", commits=[commit(1)], response_code=code)
        record("TC-05", f"code={code} 退出码", "1", str(r["exit"]))
        record("TC-05", f"code={code} 打印对应提示", "True",
               str(hint in r["stderr"]))
    record("TC-05", "正常构造的正文含关键词「日报」", "True",
           str(np.KEYWORD in np.build_text("方赫", "dev", [commit(1)])))

    # TC-07：一次 push 带 5 个 commit 只发 1 条
    r = run_main(actor="fh0709", commits=[commit(i) for i in range(1, 6)])
    text = r["calls"][0]["payload"]["content"]["text"] if r["calls"] else ""
    record("TC-07", "5 个 commit 的 post 次数", "1", str(len(r["calls"])))
    record("TC-07", "正文含 5 个编号提交", "5",
           str(len(re.findall(r"^\d+\. ", text, re.M))))
    record("TC-07", "正文条数口径（一次 push 1 条）", "1", str(len(r["calls"])))

    # TC-08：实时提醒不进 SQLite、不引 orchestrator
    source = (ROOT / "scripts/notify_push.py").read_text(encoding="utf-8")
    record("TC-08", "脚本不 import sqlite3", "True",
           str("import sqlite3" not in source))
    record("TC-08", "脚本不 import orchestrator", "True",
           str("orchestrator" not in source.replace(
               "不改 orchestrator.py", "").replace("不走采集层", "")))
    record("TC-08", "跑完不产生任何 DB 文件", "0", str(r["db_files"]))

    # TC-06：代码里没有按星期几屏蔽
    banned = [r"weekday\s*\(", r"isoweekday", r"strftime\(.*%A", r"周六", r"周日"]
    hits = [p for p in banned if re.search(p, source)]
    record("TC-06", "notify_push.py 无 weekday 类判断", "0", str(len(hits)))
    record("TC-06", "workflow 无 cron/星期过滤", "True",
           str("schedule" not in WORKFLOW and "cron" not in WORKFLOW))

    # TC-01：正常发送链路（打桩）与标题契约
    r = run_main(actor="fh0709", commits=[commit(1)], response_code=0)
    record("TC-01", "code=0 退出码", "0", str(r["exit"]))
    record("TC-01", "飞书返回码打印可查", "True", str("飞书返回：code=0" in r["stdout"]))
    title = np.short_title("很长的标题" * 20)
    record("TC-01", "长标题截断到 60 字", "61", str(len(title)))

    print("-" * 72)
    passed = sum(1 for _, _, s, _ in RESULTS if s == "PASS")
    print(f"合计：{len(RESULTS)} 项断言，PASS {passed} / FAIL {len(RESULTS) - passed}")
    print("结论：全部断言均为离线打桩/静态可复现验证；"
          "真实群内到达时刻、4 人各推 1 次、周末触发不在本脚本判定范围内。")
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
