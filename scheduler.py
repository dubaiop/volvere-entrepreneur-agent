"""Scheduled jobs — daily opportunity pipeline at 7am Dubai time."""

import logging
import os
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


def daily_full_pipeline():
    """
    Full autonomous pipeline:
    1. Find opportunity (trend-spotter)
    2. Validate it (opportunity-validator)
    3. Model it (business-model-designer)
    4. Find leads (web search)
    5. Write outreach (sales agent API)
    6. Push everything to Telegram
    """
    logger.info("Starting daily opportunity pipeline...")
    try:
        from agent import run_skill
        from telegram_alerts import alert_pipeline_result, alert_daily_opportunity

        # Step 1 — Find opportunity
        logger.info("Step 1: Finding opportunity...")
        opportunity = run_skill(
            "trend-spotter", OPPORTUNITY_PROMPT,
            context="Dubai, MENA, global tech, AI, B2B SaaS",
            session_id="scheduler"
        )

        # Step 2 — Validate it
        logger.info("Step 2: Validating opportunity...")
        validation = run_skill(
            "opportunity-validator", opportunity[:1200],
            context="lean team of 1-3 people, volvere.io AI agent platform, Dubai",
            session_id="scheduler"
        )

        # If the agent rates it PASS, still send it but skip outreach
        is_strong = "❌ PASS" not in validation

        # Step 3 — Business model + ICP (only if not a hard pass)
        biz_model = ""
        if is_strong:
            logger.info("Step 3: Designing business model...")
            biz_model = run_skill(
                "business-model-designer", opportunity[:1200],
                context="lean team of 1-3, volvere.io, AI agent platform, Dubai",
                session_id="scheduler"
            )

        # Step 4 — Score ICP via GTM agent
        icp_score = ""
        if is_strong and biz_model:
            logger.info("Step 4: Scoring ICP...")
            try:
                from actions import score_opportunity_icp
                icp_score = score_opportunity_icp(opportunity, biz_model)
            except Exception as e:
                logger.warning(f"ICP scoring skipped: {e}")

        # Step 5 — Push opportunity to HubSpot as a deal
        deal_id = ""
        if is_strong:
            logger.info("Step 5: Pushing to HubSpot...")
            try:
                from actions import push_opportunity_to_hubspot
                title = opportunity.split("\n")[0].replace("🎯", "").replace("**Opportunity**:", "").strip()[:80]
                deal_id = push_opportunity_to_hubspot(title or "New Opportunity", opportunity[:1000])
            except Exception as e:
                logger.warning(f"HubSpot push skipped: {e}")

        # Step 6 — Find leads
        leads = ""
        if is_strong and biz_model:
            logger.info("Step 6: Searching for leads...")
            try:
                from actions import find_leads
                leads = find_leads(biz_model, opportunity)
            except Exception as e:
                logger.warning(f"Lead search skipped: {e}")

        # Step 7 — Generate outreach via sales agent
        outreach = ""
        if is_strong and biz_model:
            logger.info("Step 7: Generating outreach...")
            try:
                from actions import generate_outreach
                outreach = generate_outreach(opportunity, biz_model)
            except Exception as e:
                logger.warning(f"Outreach generation skipped: {e}")

        # Step 8 — Auto-send Touch 1 if a target email is configured
        sent_to = ""
        target_email = os.environ.get("OUTREACH_TARGET_EMAIL", "")
        target_name = os.environ.get("OUTREACH_TARGET_NAME", "")
        if is_strong and outreach and target_email:
            logger.info(f"Step 8: Sending Touch 1 to {target_email}...")
            try:
                from actions import send_outreach_email
                if send_outreach_email(target_email, target_name, outreach):
                    sent_to = target_email
            except Exception as e:
                logger.warning(f"Auto-send skipped: {e}")

        # Step 9 — Push to Telegram
        logger.info("Step 9: Sending to Telegram...")
        alert_pipeline_result(opportunity, validation, biz_model or "Skipped (rated PASS).", outreach, leads, sent_to, icp_score, deal_id)
        logger.info("Daily pipeline complete.")

    except Exception as e:
        logger.error(f"Daily pipeline error: {e}")
        try:
            from telegram_alerts import send_alert
            send_alert(f"⚠️ *Entrepreneur pipeline error:* {str(e)[:200]}")
        except Exception:
            pass


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone=TZ)
    scheduler.add_job(
        daily_full_pipeline,
        CronTrigger(hour=7, minute=0, timezone=TZ),
        id="daily_pipeline",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Entrepreneur scheduler started — full pipeline at 7am Dubai")
    return scheduler
