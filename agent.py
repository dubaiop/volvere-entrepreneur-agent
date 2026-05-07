"""Core agent — runs skills and free-form entrepreneurship chat."""

import anthropic
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, COMPANY_NAME
from skills.prompts import SKILL_MAP
from database import log_interaction

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
_memory: dict[str, list] = {}

SYSTEM_PROMPT = f"""You are the Entrepreneur Intelligence Agent for {COMPANY_NAME} — a world-class AI advisor combining the minds of Elon Musk, Paul Graham, and Peter Thiel.

Your mission: help the founder spot real problems in the world, validate business opportunities, design models, and move fast from idea to first revenue.

You have access to live market knowledge, trend analysis, and business model expertise across all industries — from deep tech to Dubai real estate to MENA consumer markets.

Always be:
- DIRECT: give a verdict, not a list of considerations
- SPECIFIC: name real companies, real numbers, real strategies
- PROVOCATIVE: challenge assumptions, ask the uncomfortable question
- ACTION-ORIENTED: every response ends with a concrete next step

You remember everything from this conversation. Build on prior context. When the user shares an idea, reference it in future responses."""


def run_skill(skill_id: str, user_input: str, context: str = "", session_id: str = "default") -> str:
    skill = SKILL_MAP.get(skill_id)
    if not skill:
        return f"Unknown skill: {skill_id}"

    # Try to enrich with live web search for relevant skills
    web_context = ""
    if skill_id in ("problem-scanner", "trend-spotter", "competition-mapper"):
        try:
            from web_search import search_trends
            web_context = search_trends(user_input[:100])
        except Exception:
            pass

    prompt_text = skill["prompt"].format(input=user_input, context=context)
    if web_context:
        prompt_text += f"\n\n[Live web search results — use to ground your analysis]:\n{web_context}"

    response = _client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt_text}],
    )
    result = response.content[0].text
    log_interaction(session_id, skill_id, user_input[:300], result)
    return result


def chat(user_input: str, session_id: str = "default") -> str:
    if session_id not in _memory:
        _memory[session_id] = []

    _memory[session_id].append({"role": "user", "content": user_input})
    if len(_memory[session_id]) > 40:
        _memory[session_id] = _memory[session_id][-40:]

    response = _client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=_memory[session_id],
    )
    reply = response.content[0].text
    _memory[session_id].append({"role": "assistant", "content": reply})
    log_interaction(session_id, "chat", user_input[:300], reply)
    return reply


def clear_memory(session_id: str = "default"):
    _memory.pop(session_id, None)
