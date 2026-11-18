import logging
import os
import smtplib
from collections.abc import Mapping
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@runtime_checkable
class Notifier(Protocol):
    def send(self, subject: str, body: str, recipients: list[str]) -> bool: ...


@dataclass(frozen=True)
class EmailNotifier:
    host: str
    port: int
    user: str
    password: str
    sender: str
    use_ssl: bool

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "EmailNotifier":
        environment = os.environ if env is None else env
        host = environment.get("SMTP_HOST", "")
        user = environment.get("SMTP_USER", "")
        password = environment.get("SMTP_PASSWORD", "")
        if not host or not user or not password:
            raise ValueError("SMTP_HOST, SMTP_USER, and SMTP_PASSWORD are required")

        return cls(
            host=host,
            port=int(environment.get("SMTP_PORT", "587")),
            user=user,
            password=password,
            sender=environment.get("SMTP_SENDER", ""),
            use_ssl=environment.get("SMTP_SSL", "false").lower() in {"true", "1"},
        )

    def send(self, subject: str, body: str, recipients: list[str]) -> bool:
        message = EmailMessage()
        message["From"] = self.sender
        message["To"] = ", ".join(recipients)
        message["Subject"] = subject
        message.set_content(body)

        try:
            with smtplib.SMTP(self.host, self.port) as smtp:
                if self.use_ssl:
                    smtp.starttls()
                smtp.login(self.user, self.password)
                smtp.send_message(message)
            return True
        except Exception as error:
            logger.error("Email send failed (%s): %s", type(error).__name__, error)
            return False
