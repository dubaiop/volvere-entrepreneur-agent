"""Telegram alerts — daily opportunity of the day."""

import requests
import logging
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger(__name__)


def send_alert(message: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    for chunk in [message[i:i+4000] for i in range(0, len(message), 4000)]:
        try:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": TELEGRAM_CHAT_ID, "text": chunk, "parse_mode": "Markdown"},
                timeout=10,
            )
        except Exception as e:
            logger.error(f"Telegram alert error: {e}")


def alert_daily_opportunity(opportunity: str):
    send_alert(f"""💡 *Daily Opportunity — Volvere Entrepreneur Agent*\n\n{opportunity}\n\n_Spot it. Validate it. Build it._""")
