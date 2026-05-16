"""Cross-agent actions — generate outreach via sales agent, send via email agent."""

import os
import logging
import requests

logger = logging.getLogger(__name__)

SALES_AGENT_URL = os.environ.get("SALES_AGENT_URL", "").rstrip("/")
EMAIL_AGENT_URL = os.environ.get("EMAIL_AGENT_URL", "").rstrip("/")
GTM_AGENT_URL = os.environ.get("GTM_AGENT_URL", "").rstrip("/")
COMPANY_NAME = os.environ.get("COMPANY_NAME", "Volvere.io")


def generate_outreach(opportunity: str, icp: str) -> str:
    """Call the sales agent to write a cold outreach sequence for a validated opportunity."""
    if not SALES_AGENT_URL:
        logger.warning("SALES_AGENT_URL not set — skipping outreach generation")
        return ""
    try:
        payload = {
            "skill": "outreach-writer",
            "input": (
                f"Company selling: AI agent platform for entrepreneurs and startup founders\n"
                f"Company name: {COMPANY_NAME}\n"
                f"Target ICP:\n{icp[:600]}\n\n"
                f"Opportunity context:\n{opportunity[:400]}"
            ),
            "context": f"{COMPANY_NAME} — B2B SaaS, AI agents, Dubai/MENA, lean startup team",
            "session_id": "entrepreneur-pipeline",
        }
        r = requests.post(f"{SALES_AGENT_URL}/skill/sync", json=payload, timeout=90)
        r.raise_for_status()
        return r.json().get("result", "")
    except Exception as e:
        logger.error(f"Outreach generation failed: {e}")
        return ""


def find_leads(biz_model: str, opportunity: str = "") -> str:
    """Search for real leads using targeted queries extracted from the business model ICP."""
    try:
        from web_search import search_leads
        return search_leads(biz_model, opportunity)
    except Exception as e:
        logger.error(f"Lead search failed: {e}")
        return ""


def _extract_touch1(outreach_text: str) -> dict:
    """
    Parse Touch 1 subject and body from a sales agent outreach sequence.
    Returns {"subject": "...", "body": "..."} or empty strings if parsing fails.
    """
    subject = ""
    body_lines = []
    in_touch1 = False

    lines = outreach_text.split("\n")
    for line in lines:
        low = line.lower()

        if not in_touch1:
            if "touch 1" in low or ("day 1" in low and "touch" in low):
                in_touch1 = True
            continue

        # End of touch 1
        if "touch 2" in low or ("day 3" in low and "touch" in low):
            break

        # Extract subject line
        if low.startswith("subject") and ":" in line:
            subject = line.split(":", 1)[-1].strip().strip("*\"'")
        else:
            body_lines.append(line)

    body = "\n".join(body_lines).strip()

    # Fallback: if we couldn't parse, use first 800 chars as body
    if not body and outreach_text:
        body = outreach_text[:800]

    return {
        "subject": subject or f"Quick intro — {COMPANY_NAME}",
        "body": body,
    }


def score_opportunity_icp(opportunity: str, icp: str) -> str:
    """Call GTM agent to score the opportunity's ICP and return tier + reasoning."""
    if not GTM_AGENT_URL:
        logger.warning("GTM_AGENT_URL not set — skipping ICP scoring")
        return ""
    try:
        r = requests.post(
            f"{GTM_AGENT_URL}/run/sync",
            json={
                "skill": "icp-scoring",
                "input": f"Opportunity: {opportunity[:400]}\n\nTarget ICP: {icp[:400]}",
                "context": f"{COMPANY_NAME} — AI agent platform, B2B SaaS, Dubai/MENA",
            },
            timeout=60,
        )
        r.raise_for_status()
        return r.json().get("result", "")
    except Exception as e:
        logger.error(f"ICP scoring failed: {e}")
        return ""


def push_opportunity_to_hubspot(title: str, description: str) -> str:
    """Create a deal in HubSpot for a validated opportunity. Returns deal ID or empty string."""
    if not GTM_AGENT_URL:
        logger.warning("GTM_AGENT_URL not set — skipping HubSpot push")
        return ""
    try:
        r = requests.post(
            f"{GTM_AGENT_URL}/hubspot/add-deal",
            json={"name": title[:100], "description": description[:2000], "stage": "appointmentscheduled"},
            timeout=20,
        )
        r.raise_for_status()
        deal_id = r.json().get("deal_id", "")
        logger.info(f"HubSpot deal created: {deal_id} — {title}")
        return str(deal_id)
    except Exception as e:
        logger.error(f"HubSpot push failed: {e}")
        return ""


def push_lead_to_hubspot(email: str, name: str, company: str, notes: str) -> str:
    """Create a contact in HubSpot for a qualified lead. Returns contact ID or empty string."""
    if not GTM_AGENT_URL:
        return ""
    parts = name.split(" ", 1)
    firstname = parts[0] if parts else name
    lastname = parts[1] if len(parts) > 1 else ""
    try:
        r = requests.post(
            f"{GTM_AGENT_URL}/hubspot/add-lead",
            json={"email": email, "firstname": firstname, "lastname": lastname, "company": company, "notes": notes[:500]},
            timeout=20,
        )
        r.raise_for_status()
        return str(r.json().get("contact_id", ""))
    except Exception as e:
        logger.error(f"HubSpot lead push failed: {e}")
        return ""


def send_outreach_email(to_email: str, to_name: str, outreach_text: str, from_persona: str = "cmo_advisor") -> bool:
    """
    Extract Touch 1 from an outreach sequence and send it via the email agent.
    Returns True if sent successfully.
    """
    if not EMAIL_AGENT_URL:
        logger.warning("EMAIL_AGENT_URL not set — skipping email send")
        return False
    if not to_email:
        logger.warning("No to_email provided — skipping email send")
        return False

    touch1 = _extract_touch1(outreach_text)
    if not touch1["body"]:
        logger.warning("Could not extract Touch 1 from outreach — skipping send")
        return False

    try:
        r = requests.post(
            f"{EMAIL_AGENT_URL}/send-outreach",
            json={
                "to_email": to_email,
                "to_name": to_name,
                "subject": touch1["subject"],
                "body": touch1["body"],
                "from_persona": from_persona,
                "full_sequence": outreach_text,
            },
            timeout=30,
        )
        r.raise_for_status()
        result = r.json()
        logger.info(f"Outreach sent: {result.get('from')} → {to_email}")
        return True
    except Exception as e:
        logger.error(f"Email send failed: {e}")
        return False
