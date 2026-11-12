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

from __future__ import annotations

import os
import ssl
from datetime import datetime, timezone
from typing import Any, Iterator

import httpx

from .base import SourceUnavailableError
from .models import CommitEntry, RawRecord

GITHUB_API = "https://api.github.com"
API_VERSION = "2022-11-28"


def _display_name(login: str, fallback: str) -> str:
    """把 GitHub 登录名映射为团队显示名（如 yjy120 → 杨佳莹）。

    映射走环境变量 MEMBER_DISPLAY_NAMES（配置管理员维护，
    格式：login:显示名,login:显示名），未配置或未命中时原样返回 fallback。
    新成员提交过代码后，把其登录名补进 .env 即可。
    """
    raw = os.getenv("MEMBER_DISPLAY_NAMES", "")
    for pair in raw.split(","):
        pair = pair.strip()
        if ":" in pair:
            key, value = pair.split(":", 1)
            if key.strip() == login:
                return value.strip()
    return fallback


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
    ) -> list[CommitEntry]:
        """采集指定时间窗口内的提交记录。

        Args:
            repo: 仓库全名 owner/name，缺省用构造时的 owner/repo
            since: 起始时间（含），None 表示不限
            until: 截止时间（含），None 表示不限
            author: 只采集某个人的提交（GitHub login），None 表示全部
            per_page: 单页条数，最大 100

        Returns:
            按时间倒序排列的提交条目列表。

        Raises:
            SourceUnavailableError: 凭证缺失、权限不足、仓库为空或接口异常
        """
        target = repo or f"{self.owner}/{self.repo}"
        if "/" not in target:
            raise SourceUnavailableError(f"仓库标识不合法：{target!r}，应为 owner/name")
        params: dict[str, Any] = {"per_page": min(per_page, 100)}
        # 分支口径（2026-11-12）：proposal.md S1 采集 main 默认分支、I2 规定
        # dev/feature 未合并提交不进日报。发布已把 dev 合并进 main，主分支重新
        # 有数据，回归规范只读 main；GITHUB_BRANCH 仅作应急覆盖。
        params["sha"] = os.getenv("GITHUB_BRANCH", "main")
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
                f"[source] github: {params['sha']} 分支本窗口 0 条提交；"
                "若提交都推在 dev，请确认是否已合并到 main 或设置 GITHUB_BRANCH"
            )
        return [self._to_entry(item, target) for item in raw]

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
        """WorkSource 协议方法：采集提交记录。

        返回原始记录而非 WorkItem —— 归一化由 collect_with_fallback 统一做，
        这样单个数据源保持「只负责取数」的纯粹性。
        """
        return self.collect_commits(since=since, until=until, author=author)
