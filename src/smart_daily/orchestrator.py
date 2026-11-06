"""主编排入口 —— 四层架构的最上层

职责：把「采集 → 生成 → 推送」串成一条可执行的主流程。

对应指导书的第一部分描述：「整个系统按『采集层 → 生成层 → 推送层 → 主编排入口』
四层构建。」

关键行为：
  1. 数据源降级 —— 依次尝试 GitHub / 飞书 / 本地 Git，任一可用即可跑通。
  2. 推送失败不阻断 —— 日报照样生成并落库，推送失败只记日志。
  3. 幂等 —— 同一 (日期, 成员) 重复运行时覆盖而非追加。
"""

from __future__ import annotations

import os
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path

from .collectors.base import SourceUnavailableError, WorkSource, collect_with_fallback
from .collectors.feishu import FeishuCollector
from .collectors.github import GitHubCollector
from .collectors.local_git import LocalGitCollector
from .collectors.models import WorkItem, local_date, normalize
from .push.generator import build_personal_report, build_team_report, group_by_member
from .push.members import load_member_emails, resolve_recipients
from .push.notifiers import EmailNotifier, FeishuWebhookNotifier, Notifier

DB_PATH = os.getenv("DB_PATH", "data/daily_report.db")


class DailyReportOrchestrator:
    """智能日报主编排入口。"""

    def __init__(
        self,
        sources: list[WorkSource] | None = None,
        notifiers: list[Notifier] | None = None,
        db_path: str | Path = DB_PATH,
    ) -> None:
        self.sources = sources if sources is not None else self._default_sources()
        self.notifiers = notifiers if notifiers is not None else self._default_notifiers()
        self.db_path = Path(db_path)

    @staticmethod
    def _default_sources() -> list[WorkSource]:
        """默认数据源列表，按优先级排列。

        三个源实现同一套 WorkSource 协议，因此可以自由替换、任意降级：
          1. GitHub   —— 小组仓库的真实提交记录（首选）
          2. 飞书     —— 任务进展 + 群内消息
          3. 本地 Git —— 前两者凭证未就绪时的兜底，永远排在链尾
        """
        candidates: list[WorkSource] = []
        try:
            candidates.append(GitHubCollector.from_env())
            print("[source] GitHub 数据源已就绪")
        except SourceUnavailableError as exc:
            print(f"[source] GitHub 不可用：{exc}")
        try:
            candidates.append(FeishuCollector.from_env())
            print("[source] 飞书数据源已就绪")
        except SourceUnavailableError as exc:
            print(f"[source] 飞书不可用：{exc}")
        candidates.append(LocalGitCollector(Path.cwd()))
        print("[source] 本地 Git 兜底数据源已挂载")
        return candidates

    @staticmethod
    def _default_notifiers() -> list[Notifier]:
        """默认推送通道列表。

        通道之间互相独立：任一可用即可完成推送，全部不可用也只是打印提示，
        日报照样生成落库（推送失败不阻断主流程）。

        注意飞书 Webhook 通道不受租户资质限制 —— 个人版飞书也能推，
        这让它成为当前唯一能立刻跑通的外部通道。
        """
        candidates: list[Notifier] = []
        try:
            candidates.append(FeishuWebhookNotifier.from_env())
            print("[push] 飞书群机器人 Webhook 通道已就绪")
        except ValueError:
            pass  # 未配置 Webhook，静默跳过
        try:
            candidates.append(EmailNotifier.from_env())
            print("[push] SMTP 邮件通道已就绪")
        except ValueError:
            pass  # 未配置邮箱，静默跳过
        if not candidates:
            print("[push] 未配置任何推送通道，日报只生成不推送")
        return candidates

    # ---------- 存储 ----------

    def _ensure_db(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_reports (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                report_date  TEXT NOT NULL,
                member       TEXT NOT NULL,
                content      TEXT NOT NULL,
                item_count   INTEGER NOT NULL DEFAULT 0,
                source_name  TEXT,
                created_at   TEXT NOT NULL,
                UNIQUE (report_date, member)
            )
            """
        )
        conn.commit()
        return conn

    def save_report(self, member: str, content: str, item_count: int, day: date, source: str) -> None:
        """保存日报（幂等：同日期同成员覆盖）。"""
        conn = self._ensure_db()
        try:
            conn.execute(
                """
                INSERT INTO daily_reports
                    (report_date, member, content, item_count, source_name, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(report_date, member) DO UPDATE SET
                    content     = excluded.content,
                    item_count  = excluded.item_count,
                    source_name = excluded.source_name,
                    created_at  = excluded.created_at
                """,
                (
                    day.isoformat(),
                    member,
                    content,
                    item_count,
                    source,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def list_reports(self, day: date | None = None) -> list[dict]:
        """查询已保存的日报（用于历史查询功能）。"""
        conn = self._ensure_db()
        try:
            if day:
                cur = conn.execute(
                    "SELECT report_date, member, item_count, source_name, created_at "
                    "FROM daily_reports WHERE report_date = ? ORDER BY member",
                    (day.isoformat(),),
                )
            else:
                cur = conn.execute(
                    "SELECT report_date, member, item_count, source_name, created_at "
                    "FROM daily_reports ORDER BY report_date DESC, member"
                )
            return [
                {
                    "report_date": r[0],
                    "member": r[1],
                    "item_count": r[2],
                    "source_name": r[3],
                    "created_at": r[4],
                }
                for r in cur.fetchall()
            ]
        finally:
            conn.close()

    # ---------- 主流程 ----------

    def collect(self, since: datetime | None = None, until: datetime | None = None) -> tuple[list[WorkItem], str]:
        """采集工作痕迹，返回（归一化后的条目, 生效的数据源名）。"""
        sources = self.sources or [LocalGitCollector(Path.cwd())]
        # collect_with_fallback 内部已做 normalize，此处不可二次归一化
        return collect_with_fallback(sources, since=since, until=until)
    def run(
        self,
        since: datetime | None = None,
        until: datetime | None = None,
        day: date | None = None,
        notify: bool = True,
    ) -> dict:
        """跑一次完整的日报生成流程。

        Returns:
            包含生成结果与推送结果的字典。
        """
        items, used = self.collect(since=since, until=until)
        if day is None:
            # 用本地日期归属 —— 采集层拿到的是 UTC 时间戳，
            # 直接取 .date() 在东八区会让日报标题差一天
            day = local_date(items[0].timestamp) if items else date.today()

        groups = group_by_member(items)
        team_text = build_team_report(groups, day=day)

        saved = 0
        for member, member_items in groups.items():
            text = build_personal_report(member, member_items, day=day)
            self.save_report(member, text, len(member_items), day, used)
            saved += 1

        pushed = False
        push_detail: list[dict[str, object]] = []
        if notify and self.notifiers:
            # 个人日报按成员分别发邮件 —— 每个人只收到自己的那份
            email_results = self._push_personal_reports(groups, day)
            # 团队日报走群渠道（飞书机器人 Webhook 等）
            team_results = self._push_team_report(team_text, day)
            push_detail = email_results + team_results
            pushed = any(r["ok"] for r in push_detail)

        return {
            "date": day.isoformat(),
            "source": used,
            "members": len(groups),
            "items": len(items),
            "saved_reports": saved,
            "pushed": pushed,
            "push_detail": push_detail,
            "team_report": team_text,
        }

    def _push_personal_reports(self, groups: dict[str, list[WorkItem]], day: date) -> list[dict[str, object]]:
        """把个人日报分别发给对应成员（邮件通道）。

        成员 -> 邮箱的映射来自 MEMBER_EMAILS 环境变量（配置管理员维护）。
        没有配置映射的成员会被跳过，只记日志不影响其他成员。
        """
        results: list[dict[str, object]] = []
        mapping = load_member_emails()
        if not mapping:
            print("[push] 未配置 MEMBER_EMAILS，跳过个人日报邮件推送")
            return results

        email_notifiers = [n for n in self.notifiers if isinstance(n, EmailNotifier)]
        if not email_notifiers:
            return results

        for member, member_items in groups.items():
            recipients = resolve_recipients(member, mapping)
            if not recipients:
                print(f"[push] 成员 {member} 未配置邮箱，跳过个人日报")
                continue
            text = build_personal_report(member, member_items, day=day)
            for n in email_notifiers:
                try:
                    ok = n.send(f"个人日报 {day.isoformat()}", text, recipients)
                except Exception as exc:  # noqa: BLE001 - 推送失败不阻断
                    print(f"[push] 通道 {n.name} 异常：{exc}")
                    ok = False
                results.append(
                    {"channel": n.name, "scope": f"personal:{member}", "ok": bool(ok)}
                )
        return results

    def _push_team_report(self, team_text: str, day: date) -> list[dict[str, object]]:
        """把团队日报推到群渠道（飞书机器人 Webhook 等）。

        邮件通道不参与团队日报分发 —— 团队日报是给全组看的，
        群机器人才是它的正确载体。
        """
        results: list[dict[str, object]] = []
        for n in self.notifiers:
            if isinstance(n, EmailNotifier):
                continue  # 邮件只发个人日报
            try:
                ok = n.send(f"团队日报 {day.isoformat()}", team_text, [])
            except Exception as exc:  # noqa: BLE001 - 推送失败不阻断
                print(f"[push] 通道 {n.name} 异常：{exc}")
                ok = False
            results.append({"channel": n.name, "scope": "team", "ok": bool(ok)})
        return results


def main() -> None:
    """命令行入口：uv run --env-file .env python -m smart_daily.cli"""
    orch = DailyReportOrchestrator()
    result = orch.run()
    print("\n" + "=" * 60)
    print(f"数据源    : {result['source']}")
    print(f"报告日期  : {result['date']}")
    print(f"成员数    : {result['members']}")
    print(f"条目数    : {result['items']}")
    print(f"已保存    : {result['saved_reports']} 份")
    print(f"已推送    : {result['pushed']}")
    print("=" * 60)
    print(result["team_report"])


if __name__ == "__main__":
    main()
