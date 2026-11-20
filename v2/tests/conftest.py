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


@pytest.fixture
def identity_harness():
    """S5 真实实现 `identity.lookup_display_name` 属被 104 阻塞的 501 编排层、本期约定待建。

    本周按 601 验收②同款桩隔离验证语义契约，501 落地后由 602/603 端到端复验；未改正式模块。
    """
    from datetime import date, datetime
    from types import SimpleNamespace

    from smart_daily_v2.identity import normalize_key, normalize_members
    from smart_daily_v2.models import LOCAL_TZ, WorkItem
    from smart_daily_v2.reports.generator import (
        build_personal_report,
        build_team_report,
        group_by_member,
    )

    IdentityOutcome = SimpleNamespace

    def run(
        raw_identities: list[str] | None = None,
        *,
        mapping: dict[str, str] | None = None,
        extra_unmapped: tuple[str, ...] = (),
    ) -> IdentityOutcome:
        selected_identities = (
            ["MemberA", " memberA ", "MEMBERA"] if raw_identities is None else raw_identities
        )
        selected_mapping = {"membera": "甲", "memberb": "乙"} if mapping is None else mapping
        groups = normalize_members(selected_identities)
        normalized_keys = [normalize_key(raw) for raw in selected_identities]
        day = date(2026, 11, 18)
        items = [
            WorkItem(
                record_id=f"mock-606-{index:03d}",
                source="github",
                member=normalize_key(raw),
                kind="commit",
                title=f"示例工作条目 {index}",
                detail="示例详情",
                occurred_at=datetime(2026, 11, 18, 9, index, tzinfo=LOCAL_TZ),
                local_day=day,
            )
            for index, raw in enumerate(selected_identities, start=1)
        ]
        member_groups = group_by_member(items)
        personal = {
            member: build_personal_report(member, member_items, day)
            for member, member_items in member_groups.items()
        }
        team = build_team_report(member_groups, day)
        warnings: list[str] = []

        def resolve_display_name(login: str) -> str:
            key = normalize_key(login)
            if key in selected_mapping:
                return selected_mapping[key]
            warnings.append(f"身份未映射: {login}")
            return login

        all_logins = list(selected_identities) + list(extra_unmapped)
        resolved = {login: resolve_display_name(login) for login in all_logins}

        return IdentityOutcome(
            raw_identities=selected_identities,
            groups=groups,
            normalized_keys=normalized_keys,
            items=items,
            record_ids=tuple(item.record_id for item in items),
            member_groups=member_groups,
            personal=personal,
            team=team,
            all_logins=all_logins,
            resolved=resolved,
            warnings=warnings,
            day=day,
            mapping=selected_mapping,
        )

    return run


@pytest.fixture
def fallback_harness(monkeypatch):
    """602 集成胶水，复用 104/201/501，不改正式模块。"""
    from datetime import date
    from types import SimpleNamespace

    import smart_daily_v2.orchestrator as orchestrator_module

    http_calls: list[tuple] = []

    def fake_get(*args, **kwargs):
        http_calls.append((args, kwargs))
        return SimpleNamespace(
            is_success=False,
            status_code=401,
            json=lambda: [],
        )

    monkeypatch.setattr("smart_daily_v2.sources.github.httpx.get", fake_get)

    def factory(
        sources: list,
        *,
        day: date = date(2026, 11, 18),
        notify: bool = False,
    ) -> SimpleNamespace:
        result = orchestrator_module.run(day, sources=sources, notify=notify)
        return SimpleNamespace(result=result, http_calls=http_calls)

    factory.run = factory
    factory.http_calls = http_calls
    return factory
