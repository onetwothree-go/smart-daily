"""SQLite persistence for completed daily report snapshots.

Scope registrations (☐ 待确认):
- ADR-102 uses UNIQUE for idempotent report replacement; repeated writes update the
  existing (report_date, member) row (C5). ☐ 待组内确认
- The caller supplies the report day; UTC created_at is metadata only (C9). ☐ 待组内确认
- Empty report handling remains the caller's decision (C8). ☐ 待组内确认
- save_report source is a data-source name, distinct from WorkItem.source. ☐ 待组内确认
- work_items is schema-only in this phase. ☐ 待组内确认
- Acceptance item ④ spans connection setup and output in orchestration/CLI. ☐ 待组内确认
- save_report creates the schema; report columns follow report_date/member/content/
  item_count/source_name/created_at. ☐ 待组内确认
- ReportMeta fields and their definition in this module supply 元数据 without content. ☐ 待组内确认
- list_reports filters by report_date and orders by report_date DESC, then member. ☐ 待组内确认
- No matching history returns []; C8's source-failure behavior remains outside storage. ☐ 待组内确认
- I7 query relies on the schema created by save_report; list_reports does not create it.
  ☐ 待组内确认
- list_reports is read-only and uses parameterized SQL. ☐ 待组内确认
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timezone


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS daily_reports (
            report_date TEXT NOT NULL,
            member TEXT NOT NULL,
            content TEXT NOT NULL,
            item_count INTEGER NOT NULL,
            source_name TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(report_date, member)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS work_items (
            record_id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            member TEXT NOT NULL,
            kind TEXT NOT NULL,
            title TEXT NOT NULL,
            detail TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            local_day TEXT NOT NULL
        )
        """
    )


def save_report(
    conn: sqlite3.Connection,
    day: date,
    member: str,
    text: str,
    item_count: int,
    source: str,
) -> None:
    _create_schema(conn)
    conn.execute(
        """
        INSERT INTO daily_reports (
            report_date, member, content, item_count, source_name, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(report_date, member) DO UPDATE SET
            content = excluded.content,
            item_count = excluded.item_count,
            source_name = excluded.source_name,
            created_at = excluded.created_at
        """,
        (
            day.isoformat(),
            member,
            text,
            item_count,
            source,
            datetime.now(timezone.utc).isoformat(),
        ),
    )


@dataclass(frozen=True)
class ReportMeta:
    report_date: str
    member: str
    item_count: int
    source_name: str | None
    created_at: str


def list_reports(
    conn: sqlite3.Connection,
    day: date | None = None,
) -> list[ReportMeta]:
    if day is None:
        rows = conn.execute(
            """
            SELECT report_date, member, item_count, source_name, created_at
            FROM daily_reports
            ORDER BY report_date DESC, member
            """
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT report_date, member, item_count, source_name, created_at
            FROM daily_reports
            WHERE report_date = ?
            ORDER BY report_date DESC, member
            """,
            (day.isoformat(),),
        ).fetchall()
    return [ReportMeta(*row) for row in rows]
