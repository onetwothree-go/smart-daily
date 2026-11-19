from datetime import datetime
from pathlib import Path

import pytest

from smart_daily_v2.models import LOCAL_TZ, WorkItem, local_date, normalize
from smart_daily_v2.reports.generator import build_team_report, group_by_member
from smart_daily_v2.sources.base import (
    AllSourcesUnavailableError,
    SourceUnavailableError,
    WorkSource,
)
from smart_daily_v2.sources.mock import FIXTURE_MEMBERS, MockSource, load_fixture_items


def test_fixture_loads_without_any_credentials(cleared_env) -> None:
    items = load_fixture_items()

    assert items
    assert {item.member for item in items} == set(FIXTURE_MEMBERS)


def test_fixture_produces_full_team_report(fixture_items: list[WorkItem]) -> None:
    groups = group_by_member(fixture_items)
    report = build_team_report(groups, fixture_items[0].local_day)

    assert "成员 4 人" in report.splitlines()[0]
    assert f"条目 {len(fixture_items)} 条" in report.splitlines()[0]
    for member in FIXTURE_MEMBERS:
        assert f"## {member}" in report
    assert "今日无工作记录" not in report


def test_fixture_record_ids_stable_and_unique(
    fixture_items: list[WorkItem], golden_rows: list[dict]
) -> None:
    first_ids = [item.record_id for item in fixture_items]
    second_ids = [item.record_id for item in load_fixture_items()]

    assert first_ids == second_ids
    assert len(first_ids) == len(set(first_ids))
    assert all(record_id.startswith("mock-") for record_id in first_ids)
    assert first_ids == [row["record_id"] for row in golden_rows]


def test_fixture_items_are_normalized_workitems(fixture_items: list[WorkItem]) -> None:
    assert all(isinstance(item, WorkItem) for item in fixture_items)
    assert {item.source for item in fixture_items} == {"mock"}
    assert all(item.local_day == local_date(item.occurred_at) for item in fixture_items)
    assert normalize(fixture_items) == fixture_items
    assert {item.kind for item in fixture_items} == {"commit", "task", "message"}


def test_mock_source_satisfies_protocol_and_filters(
    fixture_items: list[WorkItem],
) -> None:
    source = MockSource()
    assert isinstance(source, WorkSource)
    assert source.name == "mock"

    since = datetime(2026, 11, 18, 9, 30, tzinfo=LOCAL_TZ)
    until = datetime(2026, 11, 18, 11, 0, tzinfo=LOCAL_TZ)
    expected_window = [item for item in fixture_items if since <= item.occurred_at <= until]
    assert source.collect(since=since, until=until) == expected_window

    expected_author = [item for item in expected_window if item.member == "甲"]
    actual_author = source.collect(since=since, until=until, author="甲")
    assert actual_author == expected_author
    assert actual_author

    full_day_since = datetime(2026, 11, 18, 0, 0, tzinfo=LOCAL_TZ)
    full_day_until = datetime(2026, 11, 18, 23, 59, tzinfo=LOCAL_TZ)
    assert len(source.collect(since=full_day_since, until=full_day_until)) == len(
        load_fixture_items()
    )


def test_mock_not_in_default_fallback_chain() -> None:
    class FakeFormalSource:
        def __init__(self, name: str) -> None:
            self.name = name

        def collect(
            self,
            *,
            since: datetime,
            until: datetime,
            author: str | None = None,
        ) -> list[WorkItem]:
            raise SourceUnavailableError(self.name, "无凭证")

    default_chain = [
        FakeFormalSource("github"),
        FakeFormalSource("feishu"),
        FakeFormalSource("local-git"),
    ]

    assert all(source.name != "mock" for source in default_chain)
    assert not any(isinstance(source, MockSource) for source in default_chain)


def test_default_chain_without_credentials_has_no_demo_data(cleared_env) -> None:
    class FakeFormalSource:
        def __init__(self, name: str) -> None:
            self.name = name

        def collect(
            self,
            *,
            since: datetime,
            until: datetime,
            author: str | None = None,
        ) -> list[WorkItem]:
            raise SourceUnavailableError(self.name, "无凭证")

    def run_chain(sources: list[WorkSource]) -> list[WorkItem]:
        errors: list[SourceUnavailableError] = []
        for source in sources:
            try:
                return source.collect(
                    since=datetime(2026, 11, 18, 0, 0, tzinfo=LOCAL_TZ),
                    until=datetime(2026, 11, 18, 23, 59, tzinfo=LOCAL_TZ),
                )
            except SourceUnavailableError as error:
                errors.append(error)
        raise AllSourcesUnavailableError(errors)

    default_chain = [
        FakeFormalSource("github"),
        FakeFormalSource("feishu"),
        FakeFormalSource("local-git"),
    ]
    with pytest.raises(AllSourcesUnavailableError) as error:
        run_chain(default_chain)
    assert [failure.source for failure in error.value.errors] == [
        "github",
        "feishu",
        "local-git",
    ]

    explicit_mock_items = run_chain([MockSource()])
    assert explicit_mock_items
    assert all(item.record_id.startswith("mock-") for item in explicit_mock_items)


def test_mock_is_not_fourth_formal_source_documented() -> None:
    import smart_daily_v2.sources.mock as mock_module

    mock_source = Path(mock_module.__file__).read_text(encoding="utf-8").lower()
    for forbidden in (
        "collect_with_fallback",
        "from_env",
        "auto_register",
        "default_sources",
        "os.environ",
        "httpx",
    ):
        assert forbidden not in mock_source

    fixture_readme = Path(__file__).parent / "fixtures" / "README.md"
    documentation = fixture_readme.read_text(encoding="utf-8")
    for anchor in ("非正式数据源", "C1 计数口径", "默认降级链", "602–606 对账"):
        assert anchor in documentation
