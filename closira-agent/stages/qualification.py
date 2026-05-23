# stages/qualification.py
from agent import call_gemini

QUALIFICATION_SYSTEM_ADDON = """
## LEAD QUALIFICATION MODE
You are now collecting qualification information. Ask the following questions ONE AT A TIME, 
in a natural conversational way. Do not ask more than one question per message.

Questions to ask (in order):
1. What brings them in today — which service are they most interested in?
2. Have they had this treatment before, or would this be their first time?
3. How soon are they looking to book — is this something they'd like to arrange this week?

Once all three answers are collected, output ONLY this JSON block (nothing else after it):
```json
{{"qualification_complete": true, "interest": "<service>", "experience": "<first_time|returning>", "urgency": "<timeline>"}}
```
"""

QUALIFICATION_QUESTIONS = [
    "which service are they interested in",
    "first time or returning",
    "booking urgency / timeline",
]


def handle_qualification(
    system_prompt: str,
    conversation_history: list,
    user_message: str,
    state: dict,
) -> tuple[str, dict]:
    """
    Stage 2: Collect qualification data via structured questions.
    """
    import json, re

    combined_prompt = system_prompt + QUALIFICATION_SYSTEM_ADDON
    reply = call_gemini(combined_prompt, conversation_history, user_message)

    # Check if qualification is complete
    match = re.search(r"```json\s*(\{.*?\})\s*```", reply, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            if data.get("qualification_complete"):
                state["qualification_data"] = data
                state["stage"] = "faq"  # Return to FAQ after qualifying
                clean = re.sub(r"```json\s*\{.*?\}\s*```", "", reply, flags=re.DOTALL).strip()
                return clean or "Great, thanks for sharing that! Is there anything else I can help you with?", state
        except json.JSONDecodeError:
            pass

    clean_reply = re.sub(r"```json\s*\{.*?\}\s*```", "", reply, flags=re.DOTALL).strip()
    return clean_reply, state
