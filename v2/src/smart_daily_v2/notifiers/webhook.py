import base64
import hashlib
import hmac as _h
import os
import time
from collections.abc import Mapping
from dataclasses import dataclass

import httpx


def gen_sign(timestamp: int, secret: str) -> str:
    string_to_sign = f"{timestamp}\n{secret}"
    return base64.b64encode(
        _h.new(
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
    ).decode("utf-8")


@dataclass(frozen=True)
class FeishuWebhookNotifier:
    webhook_url: str
    secret: str = ""
    timeout: float = 15.0

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "FeishuWebhookNotifier":
        environment = os.environ if env is None else env
        webhook_url = environment.get("FEISHU_WEBHOOK_URL", "")
        if not webhook_url:
            raise ValueError("FEISHU_WEBHOOK_URL is required")
        return cls(
            webhook_url=webhook_url,
            secret=environment.get("FEISHU_WEBHOOK_SECRET", ""),
        )

    def send(self, subject: str, body: str, recipients: list[str]) -> bool:
        text = f"{subject}\n\n{body}"
        if "日报" not in text:
            return False

        try:
            payload = {"msg_type": "text", "content": {"text": text}}
            if self.secret:
                timestamp = int(time.time())
                payload["timestamp"] = str(timestamp)
                payload["sign"] = gen_sign(timestamp, self.secret)

            response = httpx.post(
                self.webhook_url,
                json=payload,
                timeout=self.timeout,
            )
            if response.status_code != 200:
                print(
                    f"Feishu webhook request failed: HTTP {response.status_code}: {response.text}"
                )
                return False

            code = response.json().get("code")
            if code != 0:
                print(f"Feishu webhook returned error code {code}")
                return False
            return True
        except Exception as error:
            print(f"Feishu webhook send failed ({type(error).__name__}): {error}")
            return False
