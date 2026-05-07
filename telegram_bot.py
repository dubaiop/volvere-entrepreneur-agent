"""Telegram bot — entrepreneur agent commands."""

import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from config import TELEGRAM_BOT_TOKEN

logger = logging.getLogger(__name__)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 *Volvere Entrepreneur Agent* ready.\n\n"
        "I help you find problems, validate ideas, and build businesses.\n\n"
        "Commands:\n"
        "/idea — Get today's business opportunity\n"
        "/scan [industry] — Scan for problems in an industry\n"
        "/validate [idea] — Validate your idea brutally\n"
        "/trend — Spot emerging trends right now\n"
        "/help — Show this menu\n\n"
        "Or just talk to me — share any idea and I'll challenge it.",
        parse_mode="Markdown",
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cmd_start(update, context)


async def cmd_idea(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💡 Finding today's best opportunity...")
    try:
        from scheduler import OPPORTUNITY_PROMPT
        from agent import run_skill
        result = run_skill("trend-spotter", OPPORTUNITY_PROMPT, context="Dubai, MENA, global tech", session_id=f"tg_{update.effective_user.id}")
        for chunk in [result[i:i+4000] for i in range(0, len(result), 4000)]:
            await update.message.reply_text(chunk)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def cmd_scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    industry = " ".join(context.args) if context.args else "tech and software"
    await update.message.reply_text(f"🔍 Scanning {industry} for problems...")
    try:
        from agent import run_skill
        result = run_skill("problem-scanner", f"Scan {industry} for business problems", context=industry, session_id=f"tg_{update.effective_user.id}")
        for chunk in [result[i:i+4000] for i in range(0, len(result), 4000)]:
            await update.message.reply_text(chunk)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def cmd_validate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idea = " ".join(context.args) if context.args else ""
    if not idea:
        await update.message.reply_text("Usage: /validate [your idea description]")
        return
    await update.message.reply_text(f"⚖️ Validating: {idea[:80]}...")
    try:
        from agent import run_skill
        result = run_skill("opportunity-validator", idea, session_id=f"tg_{update.effective_user.id}")
        for chunk in [result[i:i+4000] for i in range(0, len(result), 4000)]:
            await update.message.reply_text(chunk)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def cmd_trend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    topic = " ".join(context.args) if context.args else "technology and business"
    await update.message.reply_text(f"📡 Spotting trends in {topic}...")
    try:
        from agent import run_skill
        result = run_skill("trend-spotter", f"What trends are emerging in {topic}?", context=topic, session_id=f"tg_{update.effective_user.id}")
        for chunk in [result[i:i+4000] for i in range(0, len(result), 4000)]:
            await update.message.reply_text(chunk)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    session_id = f"tg_{update.effective_user.id}"
    try:
        from agent import chat
        reply = chat(user_input, session_id=session_id)
        for chunk in [reply[i:i+4000] for i in range(0, len(reply), 4000)]:
            await update.message.reply_text(chunk)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


def build_application() -> Application:
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).updater(None).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("idea", cmd_idea))
    app.add_handler(CommandHandler("scan", cmd_scan))
    app.add_handler(CommandHandler("validate", cmd_validate))
    app.add_handler(CommandHandler("trend", cmd_trend))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    return app
