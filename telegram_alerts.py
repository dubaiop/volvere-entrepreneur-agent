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


def alert_pipeline_result(opportunity: str, validation: str, biz_model: str, outreach: str, leads: str, sent_to: str = ""):
    send_alert(f"🎯 *Daily Pipeline — Volvere Entrepreneur Agent*\n\n*OPPORTUNITY FOUND:*\n{opportunity[:1800]}")
    send_alert(f"✅ *VALIDATION:*\n{validation[:1800]}")
    send_alert(f"💼 *BUSINESS MODEL & ICP:*\n{biz_model[:1800]}")
    if leads:
        send_alert(f"🔍 *LEADS FOUND:*\n{leads[:1500]}")
    if outreach:
        status = f"\n\n✉️ *Touch 1 auto-sent to {sent_to}*" if sent_to else "\n\n_Set OUTREACH\\_TARGET\\_EMAIL to auto-send Touch 1._"
        send_alert(f"📧 *OUTREACH SEQUENCE:*\n{outreach[:2500]}{status}")
    else:
        send_alert("📧 *Outreach:* Set SALES\\_AGENT\\_URL env var to auto-generate outreach sequences.")
