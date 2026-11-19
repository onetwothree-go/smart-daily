"""GitHub 提交记录采集器（采集层 · 真实数据源）

职责：从 GitHub API 读取指定仓库在指定时间窗口内的提交记录，
     转换为日报条目所需的统一数据结构（CommitEntry）。

规范依据：specs/proposal.md「采集（GitHub 提交）」范围条目
设计约束：
  - 凭证只从环境变量读，绝不硬编码（指导书第六部分红色等级）
  - 只读：只用 GET 接口，不做任何写操作
  - 可降级：凭证缺失或接口失败时抛 SourceUnavailableError，
    由 collect_with_fallback 切换到下一个数据源

本模块对应课程第 2 周 tasks.md 中「T-01 GitHub 提交采集模块」的初始骨架，
第 1 周只需确认接口契约正确，不需要实现完整业务逻辑。
"""

# --- 答辩口径 · 采集层 GitHub 源（见答辩稿 2.6.1 / D17）---
# 只读 GET /repos/{owner}/{repo}/commits；401/403/404/409 统一转 SourceUnavailableError。
# 分支口径 S1 / I2：默认 sha=main，GITHUB_BRANCH 仅作应急覆盖；dev/feature 未合并不进日报。
# 窗口 since/until 转 UTC；条目时间取 commit.author.date，由编排层按本地日历二次裁剪。
# 系统证书库 verify=ssl.create_default_context() 避免代理环境下误降级为空日报；
# 显示名统一走 identity.lookup_display_name（design 2.2 收敛到唯一实现，RT-06）。

from __future__ import annotations

import os
import ssl
from datetime import datetime, timezone
from typing import Any, Iterator

import httpx

from ..identity import lookup_display_name
from .base import SourceUnavailableError
from .models import CommitEntry, RawRecord

GITHUB_API = "https://api.github.com"
API_VERSION = "2022-11-28"

# 默认同时采集 main + dev 两个分支（2026-11-19 变更）。
# 背景：团队每日工作常提交到 dev，若合并 main 的动作赶在 22:00 推送前未完成，
# 只读 main 会漏采当天提交（11-19 事故：main 1 条 / dev 26 条）。
# 可用 GITHUB_BRANCH 覆盖：单值如 "main" 退回旧行为；多值逗号分隔如 "main,dev,release"。
DEFAULT_BRANCHES = "main,dev"


def _branch_list() -> list[str]:
    """解析待采集分支列表：GITHUB_BRANCH 逗号分隔，去空去重，默认 main+dev。"""
    raw = os.getenv("GITHUB_BRANCH", DEFAULT_BRANCHES)
    branches: list[str] = []
    for part in raw.split(","):
        name = part.strip()
        if name and name not in branches:
            branches.append(name)
    # 显式设为空串时回落到完整默认值（而非只剩 main），保证空配置不会退化成单分支
    return branches or [b.strip() for b in DEFAULT_BRANCHES.split(",") if b.strip()]


def _display_name(login: str, fallback: str) -> str:
    """把 GitHub 登录名映射为团队显示名（如 yjy120 → 杨佳莹）。

    映射走环境变量 MEMBER_DISPLAY_NAMES（配置管理员维护，
    格式：login:显示名,login:显示名），未配置或未命中时原样返回 fallback。
    新成员提交过代码后，把其登录名补进 .env 即可。

    解析收敛到 ``identity.lookup_display_name``（design.md 2.2【本期约定】）：
    strip + casefold 的匹配口径与实时通道共用同一份实现。
    """
    return lookup_display_name(login) or fallback


class GitHubCollector:
    """GitHub 提交采集器。

    用法：
        collector = GitHubCollector.from_env()
        entries = collector.collect_commits("owner/repo", since, until)
    """

    name = "github"

    def __init__(self, token: str, owner: str, repo: str, timeout: float = 15.0) -> None:
        self._token = token
        self.owner = owner
        self.repo = repo
        self._client = httpx.Client(
            base_url=GITHUB_API,
            timeout=timeout,
            # 部分本机终端会注入 HTTPS 代理，httpx 默认用 certifi 证书库，
            # 不信任该代理的根证书会报 CERTIFICATE_VERIFY_FAILED 并误判数据源不可用。
            # 改用系统证书库，代理环境与直连环境都能正常校验（两条路径均已实测 200）。
            verify=ssl.create_default_context(),
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": API_VERSION,
                "User-Agent": "smart-daily",
            },
        )

    @classmethod
    def from_env(cls, owner: str | None = None, repo: str | None = None) -> "GitHubCollector":
        """从环境变量构造。

        Raises:
            SourceUnavailableError: 凭证缺失（调用方应据此降级到其他数据源）
        """
        token = os.getenv("GITHUB_TOKEN", "").strip()
        if not token:
            raise SourceUnavailableError("GITHUB_TOKEN 未设置，无法访问 GitHub API")
        owner = owner or os.getenv("GITHUB_REPO_OWNER", "").strip()
        repo = repo or os.getenv("GITHUB_REPO_NAME", "").strip()
        if not owner or not repo:
            raise SourceUnavailableError(
                "小组仓库地址未配置（GITHUB_REPO_OWNER / GITHUB_REPO_NAME 为空）"
            )
        return cls(token=token, owner=owner, repo=repo)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "GitHubCollector":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ---------- 内部方法 ----------

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        try:
            resp = self._client.get(path, params=params)
        except httpx.HTTPError as exc:
            raise SourceUnavailableError(f"网络请求失败：{exc}") from exc
        if resp.status_code == 409:
            raise SourceUnavailableError("仓库为空或尚无提交记录")
        if resp.status_code in (401, 403):
            raise SourceUnavailableError(f"凭证无效或权限不足（HTTP {resp.status_code}）")
        if resp.status_code == 404:
            raise SourceUnavailableError(f"仓库不存在或令牌未授权该仓库（HTTP 404）")
        if resp.status_code >= 400:
            raise SourceUnavailableError(f"GitHub API 返回 {resp.status_code}：{resp.text[:200]}")
        return resp.json()

    # ---------- 对外接口（契约见 specs/design.md 接口契约章节）----------

    def collect_commits(
        self,
        repo: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        author: str | None = None,
        per_page: int = 100,
        sha: str | None = None,
    ) -> list[CommitEntry]:
        """采集单个分支在指定时间窗口内的提交记录。

        Args:
            repo: 仓库全名 owner/name，缺省用构造时的 owner/repo
            since: 起始时间（含），None 表示不限
            until: 截止时间（含），None 表示不限
            author: 只采集某个人的提交（GitHub login），None 表示全部
            per_page: 单页条数，最大 100
            sha: 分支名。None 表示用 GITHUB_BRANCH 的首个分支（默认 main），
                 向后兼容旧调用；collect_commits_multi 会显式逐分支传入。

        Returns:
            按时间倒序排列的提交条目列表。

        Raises:
            SourceUnavailableError: 凭证缺失、权限不足、仓库为空或接口异常
        """
        target = repo or f"{self.owner}/{self.repo}"
        if "/" not in target:
            raise SourceUnavailableError(f"仓库标识不合法：{target!r}，应为 owner/name")
        params: dict[str, Any] = {"per_page": min(per_page, 100)}
        branch = sha or _branch_list()[0]
        params["sha"] = branch
        if since:
            params["since"] = since.astimezone(timezone.utc).isoformat()
        if until:
            params["until"] = until.astimezone(timezone.utc).isoformat()
        if author:
            params["author"] = author

        raw = self._get(f"/repos/{target}/commits", params)
        if not raw:
            # 空列表仍是合法结果（C8），但不能再「静默成功」：留一行可查的原因
            print(
                f"[source] github: {branch} 分支本窗口 0 条提交"
                "（多分支采集由 collect_commits_multi 统一处理）"
            )
        return [self._to_entry(item, target) for item in raw]

    def collect_commits_multi(
        self,
        repo: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        author: str | None = None,
        per_page: int = 100,
        branches: list[str] | None = None,
    ) -> list[CommitEntry]:
        """采集多个分支的提交，按 sha 去重后按时间倒序返回（2026-11-19 新增）。

        动机：团队工作常散落在 main / dev，合并动作可能晚于 22:00 推送时点，
        只读 main 会漏采。多分支并采 + 按 sha 去重可覆盖这种时序差：
          - merge 提交同时出现在两分支 → 去重只留一条；
          - dev 独有提交 → 即使未并入 main 也能被采到。

        容错：某个分支不存在（404）或无权限时跳过该分支；只要有一个分支成功
        就返回结果（含空结果的分支）。全部分支都失败才抛 SourceUnavailableError，
        与降级链「空结果是合法、异常才降级」的语义保持一致。

        Args:
            branches: 待采集分支列表，None 表示取 _branch_list()（GITHUB_BRANCH）。
            其余参数同 collect_commits。

        Returns:
            去重后按 occurred_at 倒序的提交条目列表。
        """
        target = repo or f"{self.owner}/{self.repo}"
        branch_list = list(branches) if branches else _branch_list()
        merged: dict[str, CommitEntry] = {}
        errors: list[str] = []
        any_ok = False

        for branch in branch_list:
            try:
                entries = self.collect_commits(
                    repo=target,
                    since=since,
                    until=until,
                    author=author,
                    per_page=per_page,
                    sha=branch,
                )
            except SourceUnavailableError as exc:
                errors.append(f"{branch}: {exc}")
                print(f"[source] github 分支 {branch} 采集失败，跳过：{exc}")
                continue
            any_ok = True
            for entry in entries:
                key = entry.sha or f"{branch}:{entry.message}:{entry.timestamp.isoformat()}"
                merged.setdefault(key, entry)

        if not any_ok:
            raise SourceUnavailableError(
                "github 所有分支均采集失败 -> " + " | ".join(errors)
            )

        print(
            f"[source] github 多分支采集完成：{','.join(branch_list)} → "
            f"去重后 {len(merged)} 条"
        )
        return sorted(merged.values(), key=lambda e: e.timestamp, reverse=True)

    def list_repo_members(self) -> list[dict[str, str]]:
        """列出仓库协作者（用于日报成员名单）。只读接口。"""
        raw = self._get(f"/repos/{self.owner}/{self.repo}/collaborators")
        return [
            {"login": c.get("login", ""), "name": c.get("name") or c.get("login", "")}
            for c in raw
            if c.get("permissions", {}).get("pull", False)
        ]

    @staticmethod
    def _to_entry(item: dict[str, Any], repo: str) -> CommitEntry:
        """把 GitHub 原始 JSON 转成 CommitEntry。"""
        commit = item.get("commit", {})
        author = commit.get("author", {})
        detail = item.get("stats") or {}
        files = item.get("files") or []
        ts = author.get("date")
        login = (item.get("author") or {}).get("login", "") or author.get("name", "")
        return CommitEntry(
            sha=item.get("sha", "")[:8],
            author_login=login,
            author_name=_display_name(login, author.get("name", "") or login),
            timestamp=(
                datetime.fromisoformat(ts.replace("Z", "+00:00"))
                if ts
                else datetime.now(timezone.utc)
            ),
            message=commit.get("message", "").splitlines()[0] if commit.get("message") else "",
            repo=repo,
            url=item.get("html_url", ""),
            additions=detail.get("additions", 0),
            deletions=detail.get("deletions", 0),
            changed_files=detail.get("total", len(files)),
            files=[f.get("filename", "") for f in files],
        )

    def iter_commits(self, **kwargs: Any) -> Iterator[CommitEntry]:
        """分页迭代器——超过 100 条提交时自动翻页。"""
        page = 1
        while True:
            batch = self.collect_commits(per_page=100, **kwargs)
            if not batch:
                return
            yield from batch
            if len(batch) < 100:
                return
            page += 1

    # ---------- WorkSource 协议实现 ----------

    def collect(
        self,
        *,
        since: datetime | None = None,
        until: datetime | None = None,
        author: str | None = None,
    ) -> list[RawRecord]:
        """WorkSource 协议方法：采集提交记录（默认 main + dev 双分支去重）。

        返回原始记录而非 WorkItem —— 归一化由 collect_with_fallback 统一做，
        这样单个数据源保持「只负责取数」的纯粹性。

        2026-11-19 变更：由单分支改为 collect_commits_multi，覆盖「dev 未及时
        合并进 main」导致的漏采；GITHUB_BRANCH 可覆盖分支集合。
        """
        return self.collect_commits_multi(since=since, until=until, author=author)
