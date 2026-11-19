from collections.abc import Mapping, Sequence

from smart_daily_v2.notifiers.email import EmailNotifier
from smart_daily_v2.notifiers.members import load_member_emails
from smart_daily_v2.notifiers.webhook import FeishuWebhookNotifier


def _send_personal(member: str, body: str) -> bool:
    try:
        recipients = load_member_emails().get(member, [])
        if not recipients:
            return False
        return EmailNotifier.from_env().send(f"{member}日报", body, recipients)
    except Exception:
        return False


def _send_team_group(body: str) -> bool:
    try:
        return FeishuWebhookNotifier.from_env().send("团队日报", body, [])
    except Exception:
        return False


def _send_team_external(body: str, recipients: Sequence[str]) -> bool:
    try:
        return EmailNotifier.from_env().send("团队日报", body, list(recipients))
    except Exception:
        return False


def dispatch(
    personal: Mapping[str, str],
    team: str,
    *,
    no_notify: bool = False,
    team_recipients: Sequence[str] = (),
) -> dict[str, bool]:
    if no_notify:
        return {}

    results: dict[str, bool] = {}
    for member, body in personal.items():
        try:
            results[f"personal:{member}"] = bool(_send_personal(member, body))
        except Exception:
            results[f"personal:{member}"] = False

    try:
        results["team"] = bool(_send_team_group(team))
    except Exception:
        results["team"] = False

    if team_recipients:
        try:
            results["team:report_recipients"] = bool(_send_team_external(team, team_recipients))
        except Exception:
            results["team:report_recipients"] = False

    return results


def all_delivered(expected: set[str], results: Mapping[str, bool]) -> bool:
    return bool(expected) and all(results.get(scope, False) for scope in expected)
