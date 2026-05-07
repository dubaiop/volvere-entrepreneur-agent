"""Scheduled jobs — daily opportunity alert at 7am Dubai time."""

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

logger = logging.getLogger(__name__)
TZ = pytz.timezone("Asia/Dubai")

OPPORTUNITY_PROMPT = """Give me today's single most interesting business opportunity that a lean team of 1-3 people could start RIGHT NOW.

Format:
🎯 **Opportunity**: [one sharp title]
📍 **Market**: [industry / geography]
😤 **The Problem**: [2 sentences — make it vivid]
💡 **The Solution**: [what you'd build]
💰 **Revenue Model**: [how you'd charge]
⚡ **Why Now**: [the timing argument in one sentence]
🚀 **First Move**: [what to do in the next 48 hours]
📊 **Potential**: [realistic 3-year revenue estimate]

Make it specific, contrarian, and actionable. Focus on underserved markets or new problems created by recent tech or regulation shifts."""


def daily_opportunity_alert():
    logger.info("Sending daily opportunity alert...")
    try:
        from agent import run_skill
        from telegram_alerts import alert_daily_opportunity
        result = run_skill("trend-spotter", OPPORTUNITY_PROMPT, context="Dubai, MENA, global tech", session_id="scheduler")
        alert_daily_opportunity(result[:3500])
    except Exception as e:
        logger.error(f"Daily opportunity error: {e}")


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone=TZ)
    scheduler.add_job(daily_opportunity_alert, CronTrigger(hour=7, minute=0, timezone=TZ), id="daily_opportunity", replace_existing=True)
    scheduler.start()
    logger.info("Entrepreneur scheduler started — daily opportunity at 7am Dubai")
    return scheduler
