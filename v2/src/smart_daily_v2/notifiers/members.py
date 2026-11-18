import os
from collections.abc import Mapping


def load_member_emails(env: Mapping[str, str] | None = None) -> dict[str, list[str]]:
    environment = os.environ if env is None else env
    configured = environment.get("MEMBER_EMAILS", "")
    members: dict[str, list[str]] = {}

    for segment in configured.split(","):
        if ":" not in segment:
            continue
        member, emails = segment.split(":", 1)
        member = member.strip()
        if not member:
            continue
        recipients = [email.strip() for email in emails.split(";") if email.strip()]
        members[member] = recipients

    return members


def load_report_recipients(env: Mapping[str, str] | None = None) -> list[str]:
    environment = os.environ if env is None else env
    configured = environment.get("REPORT_RECIPIENTS", "")
    return [recipient.strip() for recipient in configured.split(",") if recipient.strip()]
