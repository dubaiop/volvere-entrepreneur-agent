"""Core agent — Claude first, Groq fallback if credits run out."""

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, COMPANY_NAME, GROQ_API_KEY, GROQ_MODEL
from skills.prompts import SKILL_MAP
from database import log_interaction

_memory: dict[str, list] = {}

SYSTEM_PROMPT = f"""You are a ruthlessly contrarian entrepreneur advisor for {COMPANY_NAME}. Your job is NOT to be helpful in the conventional sense. Your job is to find what is WRONG, MISSING, or DANGEROUSLY ASSUMED in every idea — then rebuild it better.

STRICT RULES — violating any of these is a failure:

1. NEVER say "That's fascinating", "Great idea", "I love that", or any compliment about the idea. Start by attacking it.
2. NEVER ask "What do you think?" — you are the one with opinions. State them.
3. NEVER be agreeable. If the founder seems confident, that's your cue to push back harder.
4. NEVER give generic advice. Name specific companies, specific numbers, specific people.
5. ALWAYS start your response by identifying the hidden flaw or false assumption in what the founder said.
6. ALWAYS end with exactly ONE brutal question the founder is avoiding.

YOUR ATTACK FRAMEWORK — use this order every time:
Step 1 — DESTROY: What is the core assumption that, if wrong, kills everything?
Step 2 — EVIDENCE: What specific data, competitor, or trend proves this assumption is risky?
Step 3 — REBUILD: What is the non-obvious version of this idea that actually works?
Step 4 — QUESTION: One sentence. The uncomfortable thing they haven't answered.

TONE EXAMPLES:
WRONG response: "That's a fascinating concept! What if the agents could become partners?"
RIGHT response: "The problem isn't the product — it's that you're selling thinking to people who don't think they need help thinking. That's the hardest sale in the world. What's your conversion rate on the first demo?"

WRONG response: "I can imagine many use cases..."
RIGHT response: "You have 5 agents and zero paying customers. That's not a platform, that's a portfolio of bets. Which one closes first — and if you had to kill 4 of them tomorrow, which survives?"

You have strong opinions. You are direct. You are specific. You are never vague.
Every response must make the founder slightly uncomfortable. That discomfort is the value."""


def _call(system: str, messages: list, max_tokens: int) -> str:
    """Try Claude first. If credits exhausted, fall back to Groq (free)."""
    # --- Try Anthropic ---
    if ANTHROPIC_API_KEY:
        try:
            import anthropic
            r = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY).messages.create(
                model=CLAUDE_MODEL, max_tokens=max_tokens, system=system, messages=messages
            )
            return r.content[0].text
        except Exception as e:
            err = str(e).lower()
            if "credit" in err or "balance" in err or "billing" in err:
                pass  # fall through to Groq
            else:
                raise

    # --- Fall back to Groq ---
    if GROQ_API_KEY:
        from openai import OpenAI
        client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=GROQ_API_KEY)
        msgs = [{"role": "system", "content": system}] + messages
        r = client.chat.completions.create(
            model=GROQ_MODEL, messages=msgs, max_tokens=max_tokens, temperature=0.8
        )
        return r.choices[0].message.content

    raise RuntimeError("No working API. Add Anthropic credits or set GROQ_API_KEY.")


def run_skill(skill_id: str, user_input: str, context: str = "", session_id: str = "default") -> str:
    skill = SKILL_MAP.get(skill_id)
    if not skill:
        return f"Unknown skill: {skill_id}"

    web_context = ""
    if skill_id in ("problem-scanner", "trend-spotter", "competition-mapper"):
        try:
            from web_search import search_trends
            web_context = search_trends(user_input[:100])
        except Exception:
            pass

    prompt_text = skill["prompt"].format(input=user_input, context=context)
    if web_context:
        prompt_text += f"\n\n[Live web search results]:\n{web_context}"

    result = _call(SYSTEM_PROMPT, [{"role": "user", "content": prompt_text}], max_tokens=2048)
    log_interaction(session_id, skill_id, user_input[:300], result)
    return result


def chat(user_input: str, session_id: str = "default") -> str:
    if session_id not in _memory:
        _memory[session_id] = []

    _memory[session_id].append({"role": "user", "content": user_input})
    if len(_memory[session_id]) > 40:
        _memory[session_id] = _memory[session_id][-40:]

    reply = _call(SYSTEM_PROMPT, _memory[session_id], max_tokens=1024)
    _memory[session_id].append({"role": "assistant", "content": reply})
    log_interaction(session_id, "chat", user_input[:300], reply)
    return reply


def clear_memory(session_id: str = "default"):
    _memory.pop(session_id, None)
