# stages/escalation.py
from utils.logger import log_escalation

ESCALATION_MESSAGES = {
    "complaint": "I'm really sorry to hear you've had a frustrating experience. I'm going to connect you with one of our team members right away who can help resolve this properly.",
    "medical_question": "That's a great question, but for anything medical I'd always want to make sure you're speaking with one of our qualified practitioners. Let me get someone to reach out to you.",
    "pricing_negotiation": "I completely understand — I'd love to help, but pricing discussions are something our team handles personally. I'll have someone get back to you shortly.",
    "out_of_scope": "I want to make sure you get the right answer on this one, and it's not something I'm able to confirm from the information I have. I'll flag this for our team to follow up.",
    "explicit_request": "Of course! I'll hand you over to one of our team right away.",
    "unanswered_limit": "I've hit the limit of what I can help with here — I don't want to give you the wrong information. Let me bring in a human team member to assist.",
    "unknown": "I'm going to connect you with a member of our team who can help you further.",
}


def handle_escalation(state: dict) -> str:
    """
    Stage 3: Format escalation message and log the event.
    Returns the escalation message to show the customer.
    """
    reason = state.get("escalation_reason", "unknown")
    message = ESCALATION_MESSAGES.get(reason, ESCALATION_MESSAGES["unknown"])

    log_escalation(
        reason=reason,
        conversation_summary=_build_escalation_log(state),
    )

    return message


def _build_escalation_log(state: dict) -> str:
    history = state.get("history", [])
    lines = []
    for turn in history:
        role = "Customer" if turn["role"] == "user" else "Aria"
        content = turn["parts"][0] if isinstance(turn["parts"], list) else turn["parts"]
        lines.append(f"{role}: {content}")
    return "\n".join(lines[-6:])  # Last 3 turns for context
