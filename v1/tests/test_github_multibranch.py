"""GitHub 采集器双分支采集单元测试（2026-11-19 新增）。

覆盖 collect_commits_multi 的核心行为：
    - 多分支提交合并 + 按 sha 去重（merge 提交只留一条）
    - 单个分支失败（如仓库无 dev 分支）时跳过、其余分支照常返回
    - 所有分支失败时才抛 SourceUnavailableError（保持降级链语义）
    - GITHUB_BRANCH 解析：默认 main+dev、单值覆盖、多值逗号分隔、空值回落

不依赖网络 / 凭证 / 数据库：通过替换实例的 collect_commits 方法注入模拟数据。
运行：uv run python -m unittest discover -s tests -v
"""

from __future__ import annotations

import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from smart_daily.collectors.base import SourceUnavailableError
from smart_daily.collectors.github import GitHubCollector, _branch_list
from smart_daily.collectors.models import CommitEntry

TZ8 = timezone(timedelta(hours=8))


def _entry(sha: str, hh: int, who: str = "someone") -> CommitEntry:
    return CommitEntry(
        sha=sha,
        author_login=who,
        author_name=who,
        timestamp=datetime(2026, 11, 19, hh, 0, tzinfo=TZ8),
        message=f"feat: {sha}",
        repo="onetwothree-go/smart-daily",
        url=f"https://github.com/onetwothree-go/smart-daily/commit/{sha}",
    )


class BranchListTests(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = os.environ.get("GITHUB_BRANCH")

    def tearDown(self) -> None:
        if self._saved is None:
            os.environ.pop("GITHUB_BRANCH", None)
        else:
            os.environ["GITHUB_BRANCH"] = self._saved

    def test_default_is_main_plus_dev(self) -> None:
        os.environ.pop("GITHUB_BRANCH", None)
        self.assertEqual(_branch_list(), ["main", "dev"])

    def test_empty_value_falls_back_to_default(self) -> None:
        os.environ["GITHUB_BRANCH"] = ""
        self.assertEqual(_branch_list(), ["main", "dev"])

    def test_single_override(self) -> None:
        os.environ["GITHUB_BRANCH"] = "dev"
        self.assertEqual(_branch_list(), ["dev"])

    def test_multi_override_dedup_and_strip(self) -> None:
        os.environ["GITHUB_BRANCH"] = " main , dev , release , main "
        self.assertEqual(_branch_list(), ["main", "dev", "release"])


class MultiBranchCollectTests(unittest.TestCase):
    """用 patch 替换 collect_commits，按分支返回可控的模拟提交。"""

    def _collector(self) -> GitHubCollector:
        # token 随便给，不会真的发请求（collect_commits 已被替换）
        return GitHubCollector(token="fake", owner="o", repo="r")

    def test_merge_and_dedup_by_sha(self) -> None:
        """两分支的提交合并，merge 提交（同 sha）只保留一条。"""
        c = self._collector()
        main_entries = [_entry("aaa", 9), _entry("mmm", 10)]  # mmm = merge 提交
        dev_entries = [_entry("mmm", 10), _entry("bbb", 21)]  # 同 sha 重复

        def fake_collect(*, sha: str, **kwargs):
            return {"main": main_entries, "dev": dev_entries}[sha]

        with patch.object(c, "collect_commits", side_effect=fake_collect):
            got = c.collect_commits_multi(branches=["main", "dev"])

        shas = [e.sha for e in got]
        self.assertEqual(len(got), 3)
        self.assertEqual(set(shas), {"aaa", "mmm", "bbb"})
        # 按时间倒序：21 点在前，9 点在最后
        self.assertEqual(shas[0], "bbb")
        self.assertEqual(shas[-1], "aaa")

    def test_one_branch_failure_is_skipped(self) -> None:
        """dev 分支不存在（404 → SourceUnavailableError）时跳过，main 照常返回。"""
        c = self._collector()
        main_entries = [_entry("aaa", 9)]

        def fake_collect(*, sha: str, **kwargs):
            if sha == "dev":
                raise SourceUnavailableError("仓库不存在或令牌未授权该仓库（HTTP 404）")
            return main_entries

        with patch.object(c, "collect_commits", side_effect=fake_collect):
            got = c.collect_commits_multi(branches=["main", "dev"])

        self.assertEqual([e.sha for e in got], ["aaa"])

    def test_all_branches_fail_raises(self) -> None:
        """所有分支都失败才抛异常，交回降级链处理。"""
        c = self._collector()

        def fake_collect(*, sha: str, **kwargs):
            raise SourceUnavailableError("网络请求失败")

        with patch.object(c, "collect_commits", side_effect=fake_collect):
            with self.assertRaises(SourceUnavailableError):
                c.collect_commits_multi(branches=["main", "dev"])

    def test_empty_branch_results_are_valid(self) -> None:
        """某分支当天 0 条是合法结果，不应因此降级。"""
        c = self._collector()

        def fake_collect(*, sha: str, **kwargs):
            return [_entry("dev1", 20)] if sha == "dev" else []

        with patch.object(c, "collect_commits", side_effect=fake_collect):
            got = c.collect_commits_multi(branches=["main", "dev"])

        self.assertEqual([e.sha for e in got], ["dev1"])

    def test_collect_protocol_uses_multibranch(self) -> None:
        """WorkSource 协议方法 collect() 必须走双分支采集。"""
        c = self._collector()

        def fake_multi(*, since=None, until=None, author=None):
            return [_entry("x1", 10), _entry("x2", 20)]

        with patch.object(c, "collect_commits_multi", side_effect=fake_multi) as m:
            got = c.collect()
        m.assert_called_once()
        self.assertEqual(len(got), 2)


if __name__ == "__main__":
    unittest.main()
