import json
import os
from pathlib import Path

import pytest


@pytest.fixture
def cleared_env(monkeypatch: pytest.MonkeyPatch) -> None:
    prefixes = ("GITHUB_", "FEISHU_", "SMTP_", "DAILY_", "DB_")
    names = {"MEMBER_EMAILS", "REPORT_RECIPIENTS", "MEMBER_DISPLAY_NAMES"}
    for key in list(os.environ):
        if key.startswith(prefixes) or key in names:
            monkeypatch.delenv(key, raising=False)


@pytest.fixture
def fixture_items():
    from smart_daily_v2.sources.mock import load_fixture_items

    return load_fixture_items()


@pytest.fixture
def golden_rows() -> list[dict]:
    fixture_path = Path(__file__).parent / "fixtures" / "mock_work_items.json"
    return json.loads(fixture_path.read_text(encoding="utf-8"))


@pytest.fixture
def delivery_harness(monkeypatch, fixture_items):
    """SQLite 落库与实时提醒通道属被阻塞的编排层，本周按 605 验收③只登记口径。"""
    from collections.abc import Mapping
    from types import SimpleNamespace

    import smart_daily_v2.notifiers.dispatch as dispatch_module
    from smart_daily_v2.notifiers.dispatch import all_delivered, dispatch
    from smart_daily_v2.reports.generator import (
        build_personal_report,
        build_team_report,
        group_by_member,
    )
    from smart_daily_v2.sources.mock import FIXTURE_MEMBERS, load_fixture_items

    def run(
        outcomes: Mapping[str, bool | BaseException] | None = None,
        *,
        no_notify: bool = False,
        with_external: bool = True,
    ):
        items = load_fixture_items()
        groups = group_by_member(items)
        day = fixture_items[0].local_day
        personal = {
            member: build_personal_report(member, member_items, day)
            for member, member_items in groups.items()
        }
        team = build_team_report(groups, day)
        selected_outcomes = {} if outcomes is None else outcomes
        calls = {"personal": [], "team": [], "external": []}

        def result_for(scope: str) -> bool:
            result = selected_outcomes.get(scope, True)
            if isinstance(result, BaseException):
                raise result
            return result

        def send_personal(member: str, body: str) -> bool:
            calls["personal"].append((member, body))
            return result_for(f"personal:{member}")

        def send_team_group(body: str) -> bool:
            calls["team"].append((body,))
            return result_for("team")

        def send_team_external(body: str, recipients) -> bool:
            calls["external"].append((body, tuple(recipients)))
            return result_for("team:report_recipients")

        monkeypatch.setattr(dispatch_module, "_send_personal", send_personal)
        monkeypatch.setattr(dispatch_module, "_send_team_group", send_team_group)
        monkeypatch.setattr(dispatch_module, "_send_team_external", send_team_external)

        results = dispatch(
            personal,
            team,
            no_notify=no_notify,
            team_recipients=["ext@example.com"] if with_external else (),
        )
        expected = set(results)
        pushed = all_delivered(expected, results)

        return SimpleNamespace(
            results=results,
            pushed=pushed,
            expected=expected,
            calls=calls,
            members=set(FIXTURE_MEMBERS),
            day=day,
        )

    return run


@pytest.fixture
def format_harness():
    """604 集成胶水，复用 601 夹具 + 304 生成层，不改正式模块。"""
    from datetime import date
    from types import SimpleNamespace

    from smart_daily_v2.models import WorkItem
    from smart_daily_v2.reports.generator import (
        build_personal_report,
        build_team_report,
        group_by_member,
    )
    from smart_daily_v2.sources.mock import load_fixture_items

    FormatOutcome = SimpleNamespace

    def run(
        items: list[WorkItem] | None = None,
        *,
        empty_members: tuple[str, ...] = (),
    ) -> FormatOutcome:
        selected_items = load_fixture_items() if items is None else items
        day = selected_items[0].local_day if selected_items else date(2026, 11, 18)
        groups = group_by_member(selected_items)
        for member in empty_members:
            groups.setdefault(member, [])
        personal = {
            member: build_personal_report(member, member_items, day)
            for member, member_items in groups.items()
        }
        team = build_team_report(groups, day)

        return FormatOutcome(
            items=selected_items,
            groups=groups,
            personal=personal,
            team=team,
            day=day,
            members=sorted(groups),
            record_ids=tuple(item.record_id for item in selected_items),
        )

    return run
