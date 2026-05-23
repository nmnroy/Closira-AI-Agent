import json
import re
from agent import call_gemini


def handle_faq(
    system_prompt: str,
    conversation_history: list,
    user_message: str,
    state: dict,
) -> tuple[str, dict]:
    """
    Stage 1: Answer customer questions from SOP only.
    Returns (ai_reply, updated_state).
    Detects escalation flags embedded in the response.
    """
    reply = call_gemini(system_prompt, conversation_history, user_message)

    # Check for embedded escalation JSON
    escalation_info = _extract_escalation(reply)
    clean_reply = _strip_json_block(reply)

    if escalation_info and escalation_info.get("escalate"):
        state["stage"] = "escalated"
        state["escalation_reason"] = escalation_info.get("reason", "unknown")
        state["sop_gaps"].append(user_message) if "out_of_scope" in escalation_info.get("reason", "") else None

    return clean_reply, state


def _extract_escalation(text: str) -> dict | None:
    """Handle both fenced ```json blocks AND raw inline JSON."""
    # Try fenced first
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None

    # Fallback: raw JSON object anywhere in the text
    match = re.search(r'\{[^{}]*"escalate"\s*:\s*true[^{}]*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None

    return None


def _strip_json_block(text: str) -> str:
    """Remove both fenced and raw JSON escalation blocks."""
    # Remove fenced blocks
    text = re.sub(r"```json\s*\{.*?\}\s*```", "", text, flags=re.DOTALL)
    # Remove raw JSON blocks containing "escalate"
    text = re.sub(r'\{[^{}]*"escalate"\s*:\s*true[^{}]*\}', "", text, flags=re.DOTALL)
    return text.strip()
