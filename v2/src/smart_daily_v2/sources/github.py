"""GitHub commit source.

Scope notes (☐ 待确认，组内):
- K4 漂移：tasks.md L292 指定采集器产 RawRecord，并以 104 fallback.py 为
  归一化单点；但 L325、L300 与现有 WorkSource 契约均要求 list[WorkItem]。
  本模块遵循 L325、L300 和 104 现状，直接返回 WorkItem，不改为 RawRecord。
  若组内改选方案乙，需同步修改 L292、104④、Architecture 三处。
- S5 边界：101 提供 normalize_key / normalize_members；本模块只将登录名
  归一为 member 键，不做显示名映射。显示名解析属于 501 编排层，606 以测试桩
  隔离验证，和 606 口径一致。
- 翻页：v1 design L274 提及手动翻页，但 201 验收未列，202③ / 203② 才明确
  翻页。本模块依 G3 只请求单页；如需扩展，待组内确认后处理。
- 多分支并采与按 SHA 去重（☐ 待确认）：为覆盖 main、dev 等分支上的提交并避免重复计入，
  逐分支请求并保留首次出现的 SHA；单分支失败跳过，全部失败才降级。
- G7：归一化单点由 104 fallback.py 持有。本模块返回 WorkItem，不调用
  normalize()；fallback 对全 WorkItem 幂等放行，下游不得再次归一化。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import httpx

from smart_daily_v2.config import load_config
from smart_daily_v2.identity import normalize_key
from smart_daily_v2.models import WorkItem, local_date
from smart_daily_v2.sources.base import SourceUnavailableError, WorkSource


@dataclass(frozen=True)
class GithubSource(WorkSource):
    github_token: str
    github_repo_owner: str
    github_repo_name: str
    github_api: str
    github_branch: str

    name = "github"

    def _branch_list(self) -> list[str]:
        branches = list(
            dict.fromkeys(
                branch.strip() for branch in self.github_branch.split(",") if branch.strip()
            )
        )
        return branches or ["main", "dev"]

    @classmethod
    def from_env(cls) -> GithubSource:
        config = load_config()
        return cls(
            github_token=config.github_token,
            github_repo_owner=config.github_repo_owner,
            github_repo_name=config.github_repo_name,
            github_api=config.github_api,
            github_branch=config.github_branch,
        )

    def collect(
        self,
        *,
        since: datetime,
        until: datetime,
        author: str | None = None,
    ) -> list[WorkItem]:
        missing = [
            name
            for name, value in (
                ("GITHUB_TOKEN", self.github_token),
                ("GITHUB_REPO_OWNER", self.github_repo_owner),
                ("GITHUB_REPO_NAME", self.github_repo_name),
            )
            if not value
        ]
        if missing:
            raise SourceUnavailableError("github", f"凭证未配置：{', '.join(missing)}")

        url = (
            f"{self.github_api.rstrip('/')}/repos/"
            f"{self.github_repo_owner}/{self.github_repo_name}/commits"
        )
        params = {
            "since": since.isoformat(),
            "until": until.isoformat(),
            "per_page": 100,
            "page": 1,
        }
        if author is not None:
            params["author"] = author
        headers = {
            "Authorization": f"Bearer {self.github_token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        reasons = {
            401: "token 凭证无效或权限不足",
            403: "凭证无效或权限不足",
            404: "仓库不存在",
            409: "仓库为空",
            429: "请求限频",
        }
        errors: list[str] = []
        items: list[WorkItem] = []
        seen_shas: set[str] = set()
        successful = False
        for branch in self._branch_list():
            branch_params = {**params, "sha": branch}
            try:
                response = httpx.get(url, params=branch_params, headers=headers, timeout=15)
            except httpx.HTTPError as exc:
                errors.append(f"{branch}: 请求失败：{exc}")
                continue

            if not response.is_success:
                reason = reasons.get(response.status_code, "未预期状态码")
                errors.append(f"{branch}: {reason}（HTTP {response.status_code}）")
                continue

            successful = True
            for commit in response.json():
                sha = commit["sha"]
                if sha in seen_shas:
                    continue
                seen_shas.add(sha)
                message = commit["commit"]["message"]
                occurred_at = datetime.fromisoformat(commit["commit"]["author"]["date"])
                items.append(
                    WorkItem(
                        record_id=sha,
                        source="github",
                        member=normalize_key(
                            commit["author"]["login"]
                            if commit["author"]
                            else commit["commit"]["author"]["name"]
                        ),
                        kind="commit",
                        title=message.splitlines()[0] if message else "",
                        detail=message,
                        occurred_at=occurred_at,
                        local_day=local_date(occurred_at),
                    )
                )
        if not successful:
            raise SourceUnavailableError("github", "; ".join(errors))
        return items
