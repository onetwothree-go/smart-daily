"""第 2 周验收用例 —— 运行时级（临时 SQLite + 假推送通道）

与 `test_acceptance_pure.py` 分工：
    那个文件只测纯函数（不碰库、不碰推送），这个文件测「跑一次完整流程」的行为 ——
    C5 幂等（要真写 SQLite）和 C7 五通道 ok 判定（要真走编排层的推送分支）。

两者都只用标准库 unittest，不装新依赖、不改 pyproject.toml。

覆盖范围：
    C5  同日重跑两次：(日期,成员) 记录数不变、内容覆盖更新、不追加
    C7  4 封个人邮件 + 1 条群消息全 ok 才算送达；任一失败即降级为 partial / failed

不支持本文件的（须真实凭证 / 网络 / Actions，另行执行）：
    C2 / G5（假 token 降级）、C10（实时提醒）、G4 的真实送达

运行：
    uv run python -m unittest discover -s tests -v
"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from smart_daily.collectors.models import CommitEntry, TaskEntry
from smart_daily.orchestrator import DailyReportOrchestrator
from smart_daily.push.notifiers import EmailNotifier

TZ8 = timezone(timedelta(hours=8))
DAY = date(2026, 11, 10)
MEMBERS = ["甲", "乙", "丙", "丁"]
EMAILS = {m: f"{i}@example.com" for i, m in enumerate(MEMBERS, start=1)}


def at(hh: int, mm: int = 0) -> datetime:
    return datetime(DAY.year, DAY.month, DAY.day, hh, mm, tzinfo=TZ8)


def commit(sha: str, who: str, hh: int = 9) -> CommitEntry:
    return CommitEntry(
        sha=sha,
        author_login=who,
        author_name=who,
        timestamp=at(hh),
        message=f"feat: 完成 {sha}",
        repo="onetwothree-go/smart-daily",
        url=f"https://github.com/onetwothree-go/smart-daily/commit/{sha}",
        additions=10,
        deletions=2,
        changed_files=1,
    )


def task(tid: str, who: str, hh: int = 10) -> TaskEntry:
    return TaskEntry(
        task_id=tid,
        summary=f"推进 {tid}",
        description=f"{tid} 的说明",
        creator_id=who,
        creator_name=who,
        created_at=at(hh),
        completed=True,
        completed_at=at(hh),
    )


class StubSource:
    """固定数据集数据源 —— 实现 WorkSource 协议即可被编排层接受。"""

    name = "stub"

    def __init__(self, records):
        self.records = records

    def collect(self, *, since=None, until=None, author=None):
        return list(self.records)


class FakeEmail(EmailNotifier):
    """假邮件通道：可指定哪些收件人发送失败。"""

    def __init__(self, fail_recipients: set[str] | None = None) -> None:
        self.host = "smtp.example.com"
        self.port = 465
        self.user = "bot@example.com"
        self.password = "dummy"
        self.use_ssl = True
        self.sender = "bot@example.com"
        self.name = "email"
        self.fail_recipients = fail_recipients or set()
        self.sent: list[tuple[str, list[str]]] = []

    def send(self, subject: str, body: str, recipients: list[str]) -> bool:
        self.sent.append((subject, list(recipients)))
        return not (set(recipients) & self.fail_recipients)


class FakeGroupChannel:
    """假群通道（非邮件），用于团队日报。"""

    name = "feishu-webhook"

    def __init__(self, ok: bool = True) -> None:
        self.ok = ok
        self.sent: list[str] = []

    def send(self, subject: str, body: str, recipients: list[str] | None = None) -> bool:
        self.sent.append(subject)
        return self.ok


def four_members_records(extra_for_jia: int = 0) -> list:
    """四人各 1 条，甲额外 N 条 —— 保证 4 封个人日报 + 1 条团队日报都产生回执。"""
    records = [commit(f"a{i:02d}", "甲", 9) for i in range(1 + extra_for_jia)]
    records += [commit("b01", "乙", 10), commit("c01", "丙", 11), commit("d01", "丁", 12)]
    records += [task("t01", "甲", 13)]
    return records


class TestC5Idempotent(unittest.TestCase):
    """C5：同日重跑两次，SQLite 中 (日期,成员) 记录数不变，内容覆盖更新、不追加。"""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "acceptance.db"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _rows(self, day: date = DAY) -> list[tuple]:
        conn = sqlite3.connect(self.db)
        try:
            return conn.execute(
                "SELECT report_date, member, item_count, content FROM daily_reports "
                "WHERE report_date = ? ORDER BY member",
                (day.isoformat(),),
            ).fetchall()
        finally:
            conn.close()

    def test_同日重跑记录数不变(self) -> None:
        src = StubSource(four_members_records())
        orch = DailyReportOrchestrator(sources=[src], notifiers=[], db_path=self.db)

        first = orch.run(day=DAY, notify=False)
        rows_after_first = self._rows()
        second = orch.run(day=DAY, notify=False)
        rows_after_second = self._rows()

        self.assertEqual(first["members"], 4)
        self.assertEqual(second["members"], 4)
        self.assertEqual(len(rows_after_first), 4, "第一次应为 4 人各 1 行")
        self.assertEqual(len(rows_after_second), 4, "同日重跑不得追加记录，仍应为 4 行")

    def test_内容覆盖更新而非追加(self) -> None:
        orch = DailyReportOrchestrator(
            sources=[StubSource(four_members_records(extra_for_jia=0))],
            notifiers=[],
            db_path=self.db,
        )
        orch.run(day=DAY, notify=False)
        before = {r[1]: r[2] for r in self._rows()}
        self.assertEqual(before["甲"], 2, "甲首轮：2 次提交(1)+1 个任务(1) = 2 条")

        # 第二轮数据变多，同一个 (日期, 成员) 应被覆盖
        orch2 = DailyReportOrchestrator(
            sources=[StubSource(four_members_records(extra_for_jia=3))],
            notifiers=[],
            db_path=self.db,
        )
        orch2.run(day=DAY, notify=False)
        after = {r[1]: r[2] for r in self._rows()}

        self.assertEqual(len(after), 4, "成员数不变，不应出现新行")
        self.assertEqual(after["甲"], 5, f"甲应被覆盖为 5 条，实际 {after['甲']}")
        self.assertIn("共 5 条工作记录", [r[3] for r in self._rows() if r[1] == "甲"][0])

    def test_日期与成员联合唯一约束存在(self) -> None:
        orch = DailyReportOrchestrator(sources=[StubSource(four_members_records())], notifiers=[], db_path=self.db)
        orch.run(day=DAY, notify=False)
        conn = sqlite3.connect(self.db)
        try:
            sql = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='daily_reports'"
            ).fetchone()[0]
        finally:
            conn.close()
        self.assertIn("UNIQUE (report_date, member)", " ".join(sql.split()),
                      "幂等依赖 (report_date, member) 唯一约束，缺失则重跑必然追加")


class TestC7DeliveryFiveChannels(unittest.TestCase):
    """C7：4 封个人邮件 + 1 条飞书群消息全部 ok 才算送达成功。"""

    def _run(self, email_ok: bool = True, group_ok: bool = True,
             notifiers=None, notify: bool = True) -> dict:
        email = FakeEmail() if email_ok else FakeEmail(fail_recipients=set(EMAILS.values()))
        group = FakeGroupChannel(ok=group_ok)
        notes = notifiers if notifiers is not None else [email, group]
        orch = DailyReportOrchestrator(
            sources=[StubSource(four_members_records())],
            notifiers=notes,
            db_path=Path(tempfile.mkdtemp()) / "c7.db",
        )
        with patch("smart_daily.orchestrator.load_member_emails", return_value={m: [e] for m, e in EMAILS.items()}):
            return orch.run(day=DAY, notify=notify)

    def test_五通道全ok判送达成功(self) -> None:
        result = self._run()
        self.assertEqual(result["push_status"], "ok")
        self.assertTrue(result["pushed"])
        self.assertEqual(len(result["push_detail"]), 5,
                         f"应 4 封个人 + 1 条群 = 5 条回执，实际 {result['push_detail']}")

    def test_四封邮件数正确(self) -> None:
        email = FakeEmail()
        group = FakeGroupChannel()
        self._run_with(email, group)
        self.assertEqual(len(email.sent), 4, "应每名成员各 1 封，共 4 封")
        self.assertEqual(
            sorted(r for _, recips in email.sent for r in recips), sorted(EMAILS.values())
        )
        self.assertEqual(len(group.sent), 1, "团队日报应只推 1 条群消息")

    def _run_with(self, email, group) -> None:
        orch = DailyReportOrchestrator(
            sources=[StubSource(four_members_records())],
            notifiers=[email, group],
            db_path=Path(tempfile.mkdtemp()) / "c7b.db",
        )
        with patch("smart_daily.orchestrator.load_member_emails",
                   return_value={m: [e] for m, e in EMAILS.items()}):
            orch.run(day=DAY, notify=True)

    def test_群消息失败不算送达(self) -> None:
        result = self._run(group_ok=False)
        self.assertEqual(result["push_status"], "partial", "4 封邮件 ok 但群消息失败，只能是 partial")
        self.assertFalse(result["pushed"], "全员邮件到了也不算全 ok —— 群消息是应送达集合的一部分")

    def test_一封邮件失败不算送达(self) -> None:
        email = FakeEmail(fail_recipients={EMAILS["乙"]})
        orch = DailyReportOrchestrator(
            sources=[StubSource(four_members_records())],
            notifiers=[email, FakeGroupChannel()],
            db_path=Path(tempfile.mkdtemp()) / "c7c.db",
        )
        with patch("smart_daily.orchestrator.load_member_emails",
                   return_value={m: [e] for m, e in EMAILS.items()}):
            result = orch.run(day=DAY, notify=True)
        self.assertEqual(result["push_status"], "partial")
        self.assertFalse(result["pushed"])
        failed = [r for r in result["push_detail"] if not r["ok"]]
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0]["scope"], "personal:乙")

    def test_全部失败判failed(self) -> None:
        result = self._run(email_ok=False, group_ok=False)
        self.assertEqual(result["push_status"], "failed")
        self.assertFalse(result["pushed"])

    def test_无通道判no_channel(self) -> None:
        result = self._run(notifiers=[])
        self.assertEqual(result["push_status"], "no_channel")
        self.assertFalse(result["pushed"])
        self.assertEqual(result["push_detail"], [], "无通道时不应产生任何回执")

    def test_不推送判skipped(self) -> None:
        result = self._run(notify=False)
        self.assertEqual(result["push_status"], "skipped")
        self.assertFalse(result["pushed"])

    def test_邮件只发个人日报(self) -> None:
        email = FakeEmail()
        group = FakeGroupChannel()
        self._run_with(email, group)
        self.assertTrue(all(s.startswith("个人日报") for s, _ in email.sent),
                        f"邮件通道不应承担团队日报：{email.sent}")
        self.assertTrue(all(s.startswith("团队日报") for s in group.sent),
                        f"群通道应只发团队日报：{group.sent}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
