from __future__ import annotations
import requests

class TelegramSender:
    """Thin Bot API client. It only sends text; it never logs in or executes bets."""
    def __init__(self, token: str, chat_id: str, timeout: int = 10):
        self.token = token.strip()
        self.chat_id = str(chat_id).strip()
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.token and self.chat_id)

    def send_message(self, text: str) -> dict:
        if not self.configured:
            raise RuntimeError("Telegram não configurado: informe TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID")
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        response = requests.post(url, json={"chat_id": self.chat_id, "text": text, "disable_web_page_preview": True}, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        if not data.get("ok"):
            raise RuntimeError(str(data))
        return data
