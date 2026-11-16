"""
Telegram Bot API Client Wrapper.
"""

import logging
from typing import Dict, Any, Optional, List
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class TelegramClient:
    def __init__(self, token: Optional[str] = None):
        self.token = token or getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
        self.base_url = f"https://api.telegram.org/bot{self.token}" if self.token else ""

    @property
    def is_configured(self) -> bool:
        return bool(self.token)

    def send_message(
        self,
        chat_id: int | str,
        text: str,
        parse_mode: str = "Markdown",
        reply_markup: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Send message to a Telegram chat."""
        if not self.is_configured:
            return {"ok": False, "error": "telegram_not_configured"}

        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup

        try:
            resp = requests.post(url, json=payload, timeout=10)
            return resp.json()
        except (requests.RequestException, ValueError):
            logger.warning("Telegram send request failed.")
            return {"ok": False, "error": "telegram_request_failed"}

    def get_updates(self, offset: Optional[int] = None, timeout: int = 25) -> List[Dict[str, Any]]:
        """Long polling updates fetcher for local laptop development."""
        if not self.is_configured:
            return []

        url = f"{self.base_url}/getUpdates"
        params = {"timeout": timeout}
        if offset is not None:
            params["offset"] = offset

        try:
            resp = requests.get(url, params=params, timeout=timeout + 5)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("result", [])
        except (requests.RequestException, ValueError):
            logger.warning("Telegram polling request failed.")
        return []

    def answer_callback_query(self, callback_query_id: str, text: Optional[str] = None) -> Dict[str, Any]:
        if not self.is_configured:
            return {"ok": False, "error": "telegram_not_configured"}
        url = f"{self.base_url}/answerCallbackQuery"
        payload = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text
        try:
            return requests.post(url, json=payload, timeout=5).json()
        except (requests.RequestException, ValueError):
            return {"ok": False, "error": "telegram_request_failed"}
