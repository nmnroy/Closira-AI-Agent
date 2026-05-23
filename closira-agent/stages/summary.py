# stages/summary.py
import json
import re
from agent import call_gemini

SUMMARY_PROMPT = """
You are generating a structured end-of-session summary for a Closira customer conversation.

Based on the conversation history provided, produce a JSON summary with exactly these fields:
- "customer_intent": What the customer was trying to achieve (1-2 sentences)
- "key_details": Object with any collected info (name, service interest, experience level, urgency, etc.)
- "sop_gaps": List of questions the AI could not answer from the SOP (empty list if none)
- "escalated": true/false
- "escalation_reason": The reason if escalated, else null
- "recommended_next_action": What the human team should do next (1 sentence)

Respond ONLY with valid JSON. No preamble, no markdown fences.
"""


def generate_summary(
    system_prompt: str,
    state: dict,
) -> dict:
    """
    Stage 4: Generate a structured conversation summary.
    """
    history_text = _format_history(state.get("history", []))
    qual_data = state.get("qualification_data", {})
    sop_gaps = state.get("sop_gaps", [])

    user_prompt = f"""
Conversation history:
{history_text}

Qualification data collected: {json.dumps(qual_data)}
SOP gaps logged: {json.dumps(sop_gaps)}
Escalated: {state.get("stage") == "escalated"}
Escalation reason: {state.get("escalation_reason", "none")}

Generate the structured summary now.
"""

    reply = call_gemini(SUMMARY_PROMPT, [], user_prompt, temperature=0.1)

    # Strip markdown fences if model adds them
    clean = re.sub(r"```json|```", "", reply).strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        return {"error": "Summary parsing failed", "raw": reply}


def _format_history(history: list) -> str:
    lines = []
    for turn in history:
        role = "Customer" if turn["role"] == "user" else "Aria"
        content = turn["parts"][0] if isinstance(turn["parts"], list) else turn["parts"]
        lines.append(f"{role}: {content}")
    return "\n".join(lines)
