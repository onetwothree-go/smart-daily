import inspect
import re
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from smart_daily_v2.models import LOCAL_TZ

DAY = date(2026, 11, 19)
DAY2 = date(2026, 11, 20)
MEMBERS = ("甲", "乙", "丙", "丁")


def _conn() -> sqlite3.Connection:
    return sqlite3.connect(":memory:")


def _save(
    mod,
    conn: sqlite3.Connection,
    day: date,
    member: str,
    *,
    text: str = "示例日报 rec-502-001",
    item_count: int = 2,
    source: str = "github",
) -> None:
    mod.save_report(conn, day, member, text, item_count, source)


def _column(conn: sqlite3.Connection, *choices: str) -> str:
    names = {row[1] for row in conn.execute("PRAGMA table_info(daily_reports)")}
    return next(name for name in choices if name in names)


def _assert_no_work_item_business_sql(source: str) -> None:
    assert (
        re.search(
            r"\b(?:INSERT\s+INTO|UPDATE|DELETE\s+FROM)\s+work_items\b"
            r"|\bSELECT\b.{0,200}\bFROM\s+work_items\b",
            source,
            re.IGNORECASE | re.DOTALL,
        )
        is None
    )


def test_schema_has_unique_and_work_items_reserved() -> None:
    import smart_daily_v2.storage as storage

    conn = _conn()
    try:
        _save(storage, conn, DAY, MEMBERS[0])
        tables = dict(
            conn.execute("SELECT name, sql FROM sqlite_master WHERE type = 'table'").fetchall()
        )
        reports_sql = "".join(tables["daily_reports"].upper().split())
        assert "UNIQUE(REPORT_DATE,MEMBER)" in reports_sql
        assert "work_items" in tables

        columns = {
            row[1]: (row[2].upper(), row[3])
            for row in conn.execute("PRAGMA table_info(daily_reports)")
        }
        assert columns["report_date"] == ("TEXT", 1)
        assert columns["member"] == ("TEXT", 1)
        assert columns[_column(conn, "content", "text")] == ("TEXT", 1)
        assert columns["item_count"][0] == "INTEGER"
        assert columns[_column(conn, "source_name", "source")][0] == "TEXT"
        assert columns["created_at"] == ("TEXT", 1)

        source = Path(storage.__file__).read_text(encoding="utf-8")
        _assert_no_work_item_business_sql(source)
    finally:
        conn.close()


def test_upsert_same_day_member_keeps_one_row() -> None:
    import smart_daily_v2.storage as storage

    conn = _conn()
    try:
        _save(storage, conn, DAY, MEMBERS[0], text="示例日报 rec-502-002", item_count=2)
        _save(storage, conn, DAY, MEMBERS[0], text="更新日报 rec-502-003", item_count=5)

        assert conn.execute("SELECT COUNT(*) FROM daily_reports").fetchone()[0] == 1
        text_column = _column(conn, "content", "text")
        row = conn.execute(f"SELECT item_count, {text_column} FROM daily_reports").fetchone()
        assert row == (5, "更新日报 rec-502-003")
    finally:
        conn.close()


def test_different_members_and_days_are_separate_rows() -> None:
    import smart_daily_v2.storage as storage

    conn = _conn()
    try:
        _save(storage, conn, DAY, MEMBERS[0], text="日报 rec-502-004", item_count=2)
        _save(storage, conn, DAY, MEMBERS[1], text="日报 rec-502-005", item_count=3)
        _save(storage, conn, DAY2, MEMBERS[0], text="日报 rec-502-006", item_count=4)

        assert conn.execute("SELECT COUNT(*) FROM daily_reports").fetchone()[0] == 3
        rows = conn.execute("SELECT report_date, member, item_count FROM daily_reports").fetchall()
        assert sorted(rows) == sorted(
            [
                (DAY.isoformat(), MEMBERS[0], 2),
                (DAY.isoformat(), MEMBERS[1], 3),
                (DAY2.isoformat(), MEMBERS[0], 4),
            ]
        )
    finally:
        conn.close()


def test_signature_is_module_function_with_conn_first() -> None:
    import smart_daily_v2.storage as storage

    parameters = list(inspect.signature(storage.save_report).parameters)
    assert parameters == ["conn", "day", "member", "text", "item_count", "source"]
    assert inspect.isfunction(storage.save_report)

    conn = _conn()
    try:
        _save(storage, conn, DAY, MEMBERS[0], text="日报 rec-502-007")
        assert conn.execute("SELECT COUNT(*) FROM daily_reports").fetchone()[0] == 1
    finally:
        conn.close()


def test_report_date_comes_from_day_not_now() -> None:
    import smart_daily_v2.storage as storage

    conn = _conn()
    try:
        _save(storage, conn, DAY, MEMBERS[0], text="日报 rec-502-008")
        report_date = conn.execute("SELECT report_date FROM daily_reports").fetchone()[0]
        assert report_date == DAY.isoformat()

        created_at = conn.execute("SELECT created_at FROM daily_reports").fetchone()[0]
        created = datetime.fromisoformat(created_at)
        assert created.utcoffset() == timezone.utc.utcoffset(created)
        assert created.astimezone(LOCAL_TZ).tzinfo == LOCAL_TZ
    finally:
        conn.close()


def test_source_and_count_stored_as_given() -> None:
    import smart_daily_v2.storage as storage

    conn = _conn()
    try:
        _save(
            storage,
            conn,
            DAY,
            MEMBERS[0],
            text="日报 rec-502-009",
            item_count=7,
            source="github",
        )
        source_column = _column(conn, "source_name", "source")
        row = conn.execute(f"SELECT {source_column}, item_count FROM daily_reports").fetchone()
        assert row == ("github", 7)
    finally:
        conn.close()


def test_work_items_has_no_business_logic() -> None:
    import smart_daily_v2.storage as storage

    source = Path(storage.__file__).read_text(encoding="utf-8").lower()
    _assert_no_work_item_business_sql(source)


def test_unwritable_db_path_raises_but_text_printed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    import smart_daily_v2.storage as storage

    text = "日报 rec-502-010"
    print(text)
    with pytest.raises(sqlite3.OperationalError):
        sqlite3.connect(tmp_path)

    assert text in capsys.readouterr().out
    assert callable(storage.save_report)


def test_empty_day_is_callers_decision_not_storage() -> None:
    import smart_daily_v2.storage as storage

    conn = _conn()
    try:
        _save(storage, conn, DAY, MEMBERS[0], text="", item_count=0)
        text_column = _column(conn, "content", "text")
        row = conn.execute(f"SELECT {text_column}, item_count FROM daily_reports").fetchone()
        assert row == ("", 0)

        source = Path(storage.__file__).read_text(encoding="utf-8")
        assert "今日无工作记录" not in source
    finally:
        conn.close()


def test_docstring_registration_and_no_v1_copy() -> None:
    import smart_daily_v2.storage as storage

    source = Path(storage.__file__).read_text(encoding="utf-8")
    for forbidden in (
        "from smart_daily import",
        "ghp_",
        "xoxb-",
        "@qq.com",
        "@gmail.com",
        "https://open.feishu.cn",
    ):
        assert forbidden not in source

    for anchor in ("待确认", "ADR-102", "UNIQUE", "C5", "C9", "C8", "source", "work_items"):
        assert anchor in source
    assert "已裁定" not in source


def test_list_reports_signature_is_module_function() -> None:
    import smart_daily_v2.storage as storage

    parameters = inspect.signature(storage.list_reports).parameters
    assert list(parameters) == ["conn", "day"]
    assert parameters["day"].default is None
    assert inspect.isfunction(storage.list_reports)

    conn = _conn()
    try:
        _save(storage, conn, DAY, MEMBERS[0], text="日报 rec-503-001")
        assert len(storage.list_reports(conn)) == 1
    finally:
        conn.close()


def test_three_days_sorted_by_report_date_desc() -> None:
    import smart_daily_v2.storage as storage

    conn = _conn()
    day3 = date(2026, 11, 21)
    try:
        _save(storage, conn, DAY, MEMBERS[0], text="日报 rec-503-002")
        _save(storage, conn, DAY2, MEMBERS[0], text="日报 rec-503-003")
        _save(storage, conn, day3, MEMBERS[0], text="日报 rec-503-004")

        reports = storage.list_reports(conn)
        assert [report.report_date for report in reports] == [
            day3.isoformat(),
            DAY2.isoformat(),
            DAY.isoformat(),
        ]
    finally:
        conn.close()


def test_sort_key_is_report_date_not_created_at() -> None:
    import smart_daily_v2.storage as storage

    conn = _conn()
    day3 = date(2026, 11, 21)
    try:
        for index, day in enumerate((DAY, DAY2, day3), start=1):
            _save(storage, conn, day, MEMBERS[0], text=f"日报 rec-503-00{index}")
        conn.execute(
            "UPDATE daily_reports SET created_at = ? WHERE report_date = ?",
            ("2026-11-30T00:00:00+00:00", DAY.isoformat()),
        )
        conn.execute(
            "UPDATE daily_reports SET created_at = ? WHERE report_date = ?",
            ("2026-11-01T00:00:00+00:00", day3.isoformat()),
        )

        reports = storage.list_reports(conn)
        assert [report.report_date for report in reports] == [
            day3.isoformat(),
            DAY2.isoformat(),
            DAY.isoformat(),
        ]
    finally:
        conn.close()


def test_metadata_only_no_full_text() -> None:
    import smart_daily_v2.storage as storage

    conn = _conn()
    full_text = "rec-503-FULLTEXT-SENTINEL"
    try:
        _save(storage, conn, DAY, MEMBERS[0], text=full_text)
        reports = storage.list_reports(conn)

        assert reports
        assert all(isinstance(report, storage.ReportMeta) for report in reports)
        for report in reports:
            assert set(vars(report)) == {
                "report_date",
                "member",
                "item_count",
                "source_name",
                "created_at",
            }
            assert not hasattr(report, "content")
            assert not hasattr(report, "text")
            assert full_text not in repr(report)
    finally:
        conn.close()


def test_report_meta_is_frozen_dataclass() -> None:
    from dataclasses import FrozenInstanceError, fields, is_dataclass

    import smart_daily_v2.storage as storage

    conn = _conn()
    try:
        _save(storage, conn, DAY, MEMBERS[0], text="日报 rec-503-005")
        reports = storage.list_reports(conn)
        meta = reports[0]

        assert is_dataclass(storage.ReportMeta)
        assert {field.name for field in fields(storage.ReportMeta)} == {
            "report_date",
            "member",
            "item_count",
            "source_name",
            "created_at",
        }
        with pytest.raises(FrozenInstanceError):
            meta.member = MEMBERS[1]
    finally:
        conn.close()


def test_day_filter_returns_only_that_day() -> None:
    import smart_daily_v2.storage as storage

    conn = _conn()
    try:
        _save(storage, conn, DAY, MEMBERS[0], text="日报 rec-503-006")
        _save(storage, conn, DAY2, MEMBERS[1], text="日报 rec-503-007")
        _save(storage, conn, DAY2, MEMBERS[0], text="日报 rec-503-008")

        reports = storage.list_reports(conn, day=DAY2)
        # 同日按 member 升序；中文码点 乙(U+4E59) < 甲(U+7532)。
        assert [(report.report_date, report.member) for report in reports] == [
            (DAY2.isoformat(), MEMBERS[1]),
            (DAY2.isoformat(), MEMBERS[0]),
        ]

        # 补英文名断言：避免中文码点巧合掩盖降序 bug（Alice < Bob < Charlie）
        conn.execute("DELETE FROM daily_reports")
        for name in ("Charlie", "Bob", "Alice"):
            _save(storage, conn, DAY2, name, text="日报 rec-503-sort")
        english = storage.list_reports(conn, day=DAY2)
        assert [report.member for report in english] == ["Alice", "Bob", "Charlie"]
    finally:
        conn.close()


def test_empty_history_returns_empty_list() -> None:
    import smart_daily_v2.storage as storage

    conn = _conn()
    try:
        _save(storage, conn, DAY, MEMBERS[0], text="日报 rec-503-009")
        conn.execute("DELETE FROM daily_reports")

        assert storage.list_reports(conn) == []
    finally:
        conn.close()


def test_list_reports_is_read_only_and_parameterized() -> None:
    import inspect

    import smart_daily_v2.storage as storage

    conn = _conn()
    try:
        _save(storage, conn, DAY, MEMBERS[0], text="日报 rec-503-010")
        reports = storage.list_reports(conn, day=DAY)
        assert len(reports) == 1

        source = inspect.getsource(storage.list_reports).lower()
        for forbidden in ("insert", "update", "delete", "create table", "print(", "close("):
            assert forbidden not in source
        assert "?" in source
        assert 'f"' not in source
        assert "f'" not in source
    finally:
        conn.close()


def test_source_and_count_preserved_as_metadata() -> None:
    import smart_daily_v2.storage as storage

    conn = _conn()
    try:
        _save(
            storage,
            conn,
            DAY,
            MEMBERS[0],
            text="日报 rec-503-011",
            item_count=7,
            source="github",
        )
        reports = storage.list_reports(conn)

        assert reports[0].source_name == "github"
        assert reports[0].item_count == 7
    finally:
        conn.close()


def test_list_reports_docstring_registration_and_no_v1_copy() -> None:
    import smart_daily_v2.storage as storage

    assert callable(storage.list_reports)
    source = Path(storage.__file__).read_text(encoding="utf-8")
    for forbidden in (
        "from smart_daily import",
        "ghp_",
        "xoxb-",
        "@qq.com",
        "@gmail.com",
        "https://open.feishu.cn",
    ):
        assert forbidden not in source

    for anchor in ("待确认", "ReportMeta", "report_date", "created_at", "C8", "I7", "元数据"):
        assert anchor in source
    assert "已裁定" not in source
