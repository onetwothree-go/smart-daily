"""本地 Git 仓库采集器 —— 小组仓库建好前的过渡数据源

定位：
    小组 GitHub 仓库还没创建、或令牌权限还没就绪时，用本地 Git 仓库先把主流程跑通。
    指导书 FAQ 明确允许这种做法：「先接 GitHub 数据源与模拟数据源（mock 数据源），
    保证主流程可跑；凭证就绪后再切换真实接口。」

    本地采集器与 GitHub 采集器产出完全相同的 CommitEntry，
    因此上层编排代码一行都不用改 —— 这就是「数据源可替换」的含义。

依赖：
    只用标准库 subprocess 调 git 命令，无需额外依赖。

安全：
    只读操作（git log），不修改仓库任何内容。
"""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .base import SourceUnavailableError
from .models import CommitEntry, RawRecord
# git log 的分隔符，用不可能出现在提交信息里的单元分隔符
_FIELD_SEP = "\x1f"
_RECORD_SEP = "\x1e"

_LOG_FORMAT = _FIELD_SEP.join(["%H", "%an", "%ae", "%aI", "%s"]) + _RECORD_SEP


class LocalGitCollector:
    """从本地 Git 仓库读取提交记录。"""

    name = "local-git"

    def __init__(self, repo_path: str | Path, repo_name: str | None = None) -> None:
        self.repo_path = Path(repo_path)
        self.repo_name = repo_name or self.repo_path.name

    def _run(self, args: list[str]) -> str:
        """执行 git 命令并返回 stdout。"""
        try:
            proc = subprocess.run(
                ["git", "-C", str(self.repo_path), *args],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )
        except FileNotFoundError as exc:
            raise SourceUnavailableError(f"未找到 git 命令：{exc}") from exc
        except subprocess.TimeoutExpired as exc:
            raise SourceUnavailableError(f"git 命令超时：{exc}") from exc
        if proc.returncode != 0:
            raise SourceUnavailableError(
                f"git 命令失败（{proc.returncode}）：{proc.stderr.strip()[:200]}"
            )
        return proc.stdout

    def collect_commits(
        self,
        *,
        since: datetime | None = None,
        until: datetime | None = None,
        author: str | None = None,
    ) -> list[CommitEntry]:
        """采集本地仓库提交记录，行为与 GitHubCollector 一致。"""
        # 先确认这是个 git 仓库
        try:
            self._run(["rev-parse", "--git-dir"])
        except SourceUnavailableError as exc:
            raise SourceUnavailableError(f"{self.repo_path} 不是有效的 Git 仓库：{exc}") from exc

        args = [f"--format={_LOG_FORMAT}"]
        if since:
            args.append(f"--since={since.astimezone(timezone.utc).isoformat()}")
        if until:
            args.append(f"--until={until.astimezone(timezone.utc).isoformat()}")
        if author:
            args.append(f"--author={author}")
        args.append("--all")

        raw = self._run(["log", *args])
        entries: list[CommitEntry] = []
        for record in raw.split(_RECORD_SEP):
            record = record.strip("\n")
            if not record.strip():
                continue
            fields = record.split(_FIELD_SEP)
            if len(fields) < 5:
                continue
            sha, an, ae, aI, subject = fields[:5]
            entries.append(
                CommitEntry(
                    sha=sha[:8],
                    author_login=ae,
                    author_name=an,
                    timestamp=datetime.fromisoformat(aI),
                    message=subject,
                    repo=self.repo_name,
                    url=f"file://{self.repo_path}/commit/{sha}",
                )
            )
        # 按时间倒序（git log 本身就是倒序，这里再排一次保证契约一致）
        entries.sort(key=lambda e: e.timestamp, reverse=True)
        return entries

    def list_repo_members(self) -> list[dict[str, str]]:
        """列出仓库贡献者（等价于 GitHub 的协作者列表）。"""
        raw = self._run(["shortlog", "-sne", "--all"])
        members: list[dict[str, str]] = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t", 1)
            if len(parts) != 2:
                continue
            count, ident = parts
            name, _, email = ident.partition(" <")
            email = email.rstrip(">")
            members.append({"name": name, "email": email, "commits": count.strip()})
        return members

    # ---------- WorkSource 协议实现 ----------

    def collect(
        self,
        *,
        since: datetime | None = None,
        until: datetime | None = None,
        author: str | None = None,
    ) -> list[RawRecord]:
        """WorkSource 协议方法：采集本地仓库提交记录。"""
        return self.collect_commits(since=since, until=until, author=author)
