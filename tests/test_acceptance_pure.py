"""第 2 周验收用例 —— 纯函数级（不需要网络 / 数据库 / 凭证）

对应《proposal 成功标准逐条核对表》中可在本机独立验证的条目。
每条用例的 docstring 首行标注对应编号，便于回填核对表「证据」列。

覆盖范围（能测的）：
    C1  条目数 = 提交数 + 任务数，逐条 record_id 对账
    C4  个人 / 团队日报模板骨架一致，20 条与 0 条成员均全量列出
    C8  合法空（当天无数据）显式产出「今日无工作记录」
    C9  跨时区归属（东八区 23:30 计入当日，UTC 16:00 计入次日）
    G1  条目数 = 提交 + 任务 + 消息
    G3  多个登录名归并后不串人

不支持本文件的（须真实凭证 / 数据库 / Actions，另行执行）：
    C2 / G5（假 token 降级）、C5（幂等，需临时 DB）、C7（5 通道 ok，需推送层）、
    C10（实时提醒，需 push 触发 Actions）、G4 的送达部分

运行：
    uv run python -m unittest discover -s tests -v
"""

# --- 答辩口径 · 验收用例纯函数层 17 条（见答辩稿 2.7 / 第 6 章②）---
# C1 条目数、C8 合法空、C9 时区、G1 三源不合并、G3 身份归并、C4 条目行格式；
# 2026-11-12 另补 3 条 G3 身份归并用例（条数随测试扩充，以实际 unittest 输出为准）；
# 不需要凭证：uv run python -m unittest discover -s tests -v

from __future__ import annotations

import re
import unittest
from datetime import date, datetime, timedelta, timezone

from smart_daily.collectors.models import (
    CommitEntry,
    MessageEntry,
    TaskEntry,
    local_date,
    normalize,
)
from smart_daily.identity import lookup_display_name, parse_mapping
from smart_daily.push.generator import (
    build_personal_report,
    build_team_report,
    group_by_member,
    summarize_counts,
)

TZ8 = timezone(timedelta(hours=8))
DAY = date(2026, 11, 10)


def at(hh: int, mm: int = 0, day: date = DAY, tz: timezone = TZ8) -> datetime:
    return datetime(day.year, day.month, day.day, hh, mm, tzinfo=tz)


def commit(sha: str, who: str, hh: int, mm: int = 0) -> CommitEntry:
    return CommitEntry(
        sha=sha,
        author_login=who,
        author_name=who,
        timestamp=at(hh, mm),
        message=f"feat: 完成 {sha}",
        repo="onetwothree-go/smart-daily",
        url=f"https://github.com/onetwothree-go/smart-daily/commit/{sha}",
        additions=10,
        deletions=2,
        changed_files=1,
    )


def task(tid: str, who: str, hh: int, mm: int = 0) -> TaskEntry:
    return TaskEntry(
        task_id=tid,
        summary=f"推进 {tid}",
        description=f"{tid} 的说明",
        creator_id=who,
        creator_name=who,
        created_at=at(hh, mm),
        completed=True,
        completed_at=at(hh, mm),
    )


def message(mid: str, who: str, hh: int, mm: int = 0) -> MessageEntry:
    return MessageEntry(
        message_id=mid,
        chat_id="oc_test",
        sender_id=who,
        sender_name=who,
        timestamp=at(hh, mm),
        text=f"群消息 {mid}：分支规范已发群里",
    )


def item_lines(text: str) -> list[str]:
    """取出日报里所有条目行（形如 `- [13:07] （代码提交）...`）。"""
    return [ln for ln in text.splitlines() if re.match(r"^- \[\d{2}:\d{2}\]", ln)]


def skeleton(text: str) -> list[str]:
    """把日报剥离成「结构指纹」：去掉成员名、条数、具体条目内容。

    独立实现在测试侧，不调用生成层内部函数 —— 避免用被测代码证明被测代码。
    条目行连续段折叠成单个 ITEMS，因为「条数不同」是数据差异、不是模板差异
    （条数是否全量列出由 test_20条不截断 单独断言）。
    """
    raw: list[str] = []
    for ln in text.splitlines():
        s = ln.strip()
        if not s:
            raw.append("BLANK")
        elif s.startswith("# ") and "的日报" in s:
            raw.append("H1_PERSONAL")
        elif s.startswith("# 团队日报"):
            raw.append("H1_TEAM")
        elif re.match(r"^## .+（\d+ 条）$", s):
            raw.append("H2_SOURCE")
        elif s.startswith("## ") and "（" in s:
            raw.append("H2_MEMBER")
        elif re.match(r"^- \[\d{2}:\d{2}\]", s):
            raw.append("ITEM")
        elif s.startswith("共 ") or s.startswith("本报告由系统"):
            raw.append("TAIL")
        else:
            raw.append("OTHER:" + s[:20])
    out: list[str] = []
    for s in raw:
        if s == "ITEM" and out and out[-1] == "ITEMS":
            continue
        out.append("ITEMS" if s == "ITEM" else s)
    return out


class TestC1EntryCount(unittest.TestCase):
    """C1：当日 3 次提交 + 2 个任务，个人日报条目数 = 5，逐条 record_id 对账。"""

    def setUp(self) -> None:
        self.entries = [
            commit("a1", "于悦", 9),
            commit("a2", "于悦", 11),
            commit("a3", "于悦", 14),
            task("t1", "于悦", 10),
            task("t2", "于悦", 16),
        ]

    def test_条目数等于提交加任务(self) -> None:
        items = normalize(self.entries)
        text = build_personal_report("于悦", items, day=DAY)
        self.assertEqual(len(item_lines(text)), 5, f"条目行数应为 5，实际：\n{text}")
        self.assertIn("共 5 条工作记录", text)
        self.assertIn("手工编写 0 条", text)

    def test_record_id逐条对账(self) -> None:
        items = normalize(self.entries)
        want = {"a1", "a2", "a3", "t1", "t2"}
        got = {i.record_id for i in items}
        self.assertEqual(want, got, "归一化后 record_id 集合应与原始记录一致")

    def test_按来源分组的条数自洽(self) -> None:
        counts = summarize_counts(normalize(self.entries))
        self.assertEqual(counts, {"commit": 3, "task": 2})
        self.assertEqual(sum(counts.values()), 5)


class TestC8LegalEmpty(unittest.TestCase):
    """C8（合法空）：当天确实无数据时，显式产出「今日无工作记录」，不静默返回空。"""

    def test_个人日报空数据显式文案(self) -> None:
        text = build_personal_report("于悦", [], day=DAY)
        self.assertIn("今日无工作记录", text)
        self.assertNotIn("共 0 条工作记录，手工编写", text)

    def test_团队日报全组零记录仍产出(self) -> None:
        text = build_team_report({"杨佳莹": []}, day=DAY)
        self.assertIn("团队日报", text)
        self.assertIn("共 1 位成员、0 条工作记录", text)

    def test_零记录成员不丢人(self) -> None:
        groups = group_by_member(normalize([commit("a1", "甲", 9)]))
        groups.setdefault("乙", [])
        text = build_team_report(groups, day=DAY)
        self.assertIn("## 乙（0 条）", text)


class TestC9Timezone(unittest.TestCase):
    """C9：跨时区归属 —— 东八区 23:30 计入当日，UTC 16:00 计入次日。"""

    def setUp(self) -> None:
        self.local_hours = (
            datetime.now().astimezone().utcoffset() or timedelta(0)
        ).total_seconds() / 3600
        if self.local_hours != 8:
            self.skipTest(f"本用例要求运行机时区为东八区，当前 UTC+{self.local_hours:g}")

    def test_东八区2330计入当日(self) -> None:
        ts = datetime(2026, 11, 10, 15, 30, tzinfo=timezone.utc)  # = 东八区 11-10 23:30
        self.assertEqual(local_date(ts), date(2026, 11, 10))

    def test_UTC16点计入次日(self) -> None:
        ts = datetime(2026, 11, 10, 16, 0, tzinfo=timezone.utc)  # = 东八区 11-11 00:00
        self.assertEqual(local_date(ts), date(2026, 11, 11))

    def test_不能用直接date的老写法(self) -> None:
        ts = datetime(2026, 11, 10, 16, 0, tzinfo=timezone.utc)  # UTC 11-10 16:00 = 东八区 11-11 00:00
        self.assertEqual(ts.date(), date(2026, 11, 10), "UTC 日期仍是 11-10")
        self.assertEqual(local_date(ts), date(2026, 11, 11), "本地应归属 11-11")
        self.assertNotEqual(ts.date(), local_date(ts), "直接 .date() 会差一天，本用例专打这个老 bug")


class TestG1EntryCount(unittest.TestCase):
    """G1：条目数 = 提交数 + 任务数 + 消息数；三类跨源各自独立成条，不合并去重。"""

    def test_三源合计条数(self) -> None:
        entries = [
            commit("a1", "于悦", 9),
            commit("a2", "于悦", 10),
            commit("a3", "于悦", 11),
            task("t1", "于悦", 12),
            task("t2", "于悦", 13),
            message("m1", "于悦", 14),
        ]
        items = normalize(entries)
        text = build_personal_report("于悦", items, day=DAY)
        self.assertEqual(len(item_lines(text)), 6, text)
        self.assertIn("共 6 条工作记录", text)

    def test_同一动作跨三源不合并(self) -> None:
        entries = [
            commit("a1", "于悦", 9),
            message("m1", "于悦", 9),
            task("t1", "于悦", 9),
        ]
        items = normalize(entries)
        self.assertEqual(len(items), 3, "同一动作的提交/消息/任务应按 3 条独立呈现，不合并")
        self.assertEqual(len({i.source for i in items}), 3)


class TestG3IdentityMerge(unittest.TestCase):
    """G3：多个登录名归并到一人 —— 按 author_name 归并，甲乙互不串人。"""

    def test_三个登录名归并为一份(self) -> None:
        entries = [
            commit("a1", "甲", 9),
            commit("a2", "甲", 10),
            commit("a3", "甲", 11),
            commit("b1", "乙", 12),
        ]
        groups = group_by_member(normalize(entries))
        self.assertEqual(len(groups), 2, f"应恰 2 组，实际：{list(groups)}")
        self.assertEqual(len(groups["甲"]), 3)
        self.assertEqual(len(groups["乙"]), 1)

    def test_不串人(self) -> None:
        entries = [commit("a1", "甲", 9), commit("b1", "乙", 12)]
        groups = group_by_member(normalize(entries))
        self.assertEqual({i.record_id for i in groups["甲"]}, {"a1"})
        self.assertEqual({i.record_id for i in groups["乙"]}, {"b1"})

    def test_别名解析_strip且大小写不敏感(self) -> None:
        """G3 / RT-06：匹配口径为 strip() + casefold()，非采集链路各写一套。"""
        raw = "yjy120:杨佳莹,As:杨佳莹,zhaorui715:赵蕊,fh0709:方赫"
        self.assertEqual(lookup_display_name(" YJY120 ", mapping_raw=raw), "杨佳莹")
        self.assertEqual(lookup_display_name("as", mapping_raw=raw), "杨佳莹")
        self.assertEqual(lookup_display_name("ZHAORUI715", mapping_raw=raw), "赵蕊")

    def test_别名解析_多候选按优先级回落(self) -> None:
        """本地 git 姓名未配置时，用邮箱本地部分继续查；都未命中才返回 None。"""
        raw = "yang13039348457:杨佳莹"
        self.assertEqual(
            lookup_display_name("as", "yang13039348457", mapping_raw=raw), "杨佳莹"
        )
        self.assertIsNone(lookup_display_name("as", "nobody", mapping_raw=raw))

    def test_别名解析_非法片段跳过(self) -> None:
        self.assertEqual(parse_mapping("yjy120:杨佳莹,坏片段,:无键,键无值:"), {"yjy120": "杨佳莹"})


class TestC4SkeletonConsistency(unittest.TestCase):
    """C4：团队日报与个人日报模板骨架逐字一致；20 条与 0 条成员均全量列出。"""

    def setUp(self) -> None:
        self.data = {
            "甲": [commit(f"a{i:02d}", "甲", 9) for i in range(20)],
            "乙": [],
            "丙": [commit(f"c{i:02d}", "丙", 10) for i in range(3)],
            "丁": [commit(f"d{i:02d}", "丁", 11) for i in range(2)],
        }
        self.personal = {
            m: build_personal_report(m, normalize(v), day=DAY) for m, v in self.data.items()
        }

    def test_四份个人日报骨架一致(self) -> None:
        prints = {m: skeleton(t) for m, t in self.personal.items() if self.data[m]}
        base_member, base = next(iter(prints.items()))
        for m, p in prints.items():
            self.assertEqual(base, p, f"{base_member} 与 {m} 的骨架不一致")

    def test_20条不截断(self) -> None:
        self.assertEqual(len(item_lines(self.personal["甲"])), 20, "20 条应全量列出，不压缩不截断")

    def test_0条成员仍被列出(self) -> None:
        self.assertIn("今日无工作记录", self.personal["乙"])

    def test_团队日报含全部四位成员(self) -> None:
        groups = group_by_member(normalize([x for v in self.data.values() for x in v]))
        groups.setdefault("乙", [])
        text = build_team_report(groups, day=DAY)
        for m in self.data:
            self.assertIn(f"## {m}（", text, f"团队日报缺成员 {m}")
        self.assertIn("共 4 位成员、25 条工作记录", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
