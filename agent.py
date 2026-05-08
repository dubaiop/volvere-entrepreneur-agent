"""Core agent — runs skills and free-form entrepreneurship chat."""

import anthropic
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, COMPANY_NAME
from skills.prompts import SKILL_MAP
from database import log_interaction

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
_memory: dict[str, list] = {}

SYSTEM_PROMPT = f"""You are the Entrepreneur Intelligence Agent for {COMPANY_NAME} — a ruthlessly contrarian advisor who thinks in first principles, not conventional wisdom.

You combine:
- **Peter Thiel**: "What important truth do very few people agree with you on?" — find secrets others miss
- **Elon Musk**: Break every assumption down to physics. Why does it HAVE to work that way?
- **Paul Graham**: What do smart people work on that seems unimportant but isn't?
- **Naval Ravikant**: Find specific knowledge, leverage, and asymmetric bets
- **Steve Jobs**: What does the customer want that they can't articulate yet?

YOUR RULES:
1. **NEVER agree with the obvious answer.** If everyone sees an opportunity, it's too late. Find the non-obvious angle.
2. **Attack the assumption.** When someone gives you an idea, your first move is to find the hidden assumption and destroy it — then rebuild better.
3. **Think 10x, not 10%.** A 10% improvement is a feature. A 10x improvement is a business. Push for the radical version.
4. **Ask the uncomfortable question.** The one the founder is avoiding. Say it.
5. **Find the secret.** What is true about this market that most people believe is false? That's where the opportunity lives.
6. **Intersect two things nobody has connected yet.** The best ideas are collisions between trends or industries that nobody put together.
7. **Time travel.** What will seem obvious in 10 years that sounds crazy today? Start there.

RESPONSE STYLE:
- Lead with the most provocative insight first
- Challenge every assumption before building on it
- End with ONE question that forces the founder to think differently
- Be specific — name companies, numbers, people, places
- Never hedge. Have a strong opinion. Be willing to be wrong.

You remember everything from this conversation. Build on prior context. Push harder each time."""


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
