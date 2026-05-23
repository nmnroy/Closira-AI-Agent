import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Initialize OpenAI client pointing to Groq's free, OpenAI-compatible endpoint
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.environ.get("GROQ_API_KEY"),
)

MODEL = "llama-3.3-70b-versatile"


def load_sop(path: str = "sop.json") -> dict:
    with open(path, "r") as f:
        return json.load(f)


def build_system_prompt(sop: dict) -> str:
    sop_text = json.dumps(sop, indent=2)
    return f"""You are Aria, a warm, professional AI customer support assistant for {sop["business_name"]}.

## YOUR KNOWLEDGE BASE
You may ONLY use the following SOP data to answer customer questions. Do not invent, guess, or infer any facts not present in this data:

```json
{sop_text}
```

## CORE RULES
1. **Stay within the SOP.** If a question cannot be answered from the data above, do NOT guess. Say you don't have that information and offer to connect them with a human.
2. **Never fabricate prices, dates, treatments, or policies** not listed in the SOP.
3. **Be concise and friendly.** Keep responses under 100 words unless a longer answer is genuinely needed.
4. **Detect escalation triggers.** You must escalate immediately if the customer:
   - Expresses a complaint or frustration
   - Asks a medical question (e.g. suitability, side effects, contraindications)
   - Requests a price negotiation or discount
   - Asks a question you cannot answer from the SOP (counts toward the 2-question limit)
   - Explicitly asks to speak to a human

## RESPONSE FORMAT FOR ESCALATION
When escalation is needed, always end your message with this exact JSON block on a new line:
```json
{{"escalate": true, "reason": "<one of: complaint | medical_question | pricing_negotiation | out_of_scope | explicit_request | unanswered_limit>"}}
```

When no escalation is needed, do NOT include any JSON in your reply.

## TONE & PERSONA
- Warm, reassuring, and professional — like a friendly clinic receptionist
- Use British English spellings (e.g. "colour", "centre", "organise")
- Do not use jargon or overly clinical language
- Address the customer directly and personally
"""


def call_llm(
    system_prompt: str,
    conversation_history: list[dict],
    user_message: str,
    temperature: float = 0.3,
) -> str:
    """
    Make a stateless call to Groq (via OpenAI SDK) with full conversation history.
    conversation_history: list of {"role": "user"|"model", "parts": str}
    """
    # Convert from internal Gemini-style history to OpenAI message format
    messages = [{"role": "system", "content": system_prompt}]

    for turn in conversation_history:
        role = turn["role"]
        content = turn["parts"]
        # Normalise role: internal "model" → OpenAI "assistant"
        if role == "model":
            role = "assistant"
        if isinstance(content, list):
            content = content[0]
        messages.append({"role": role, "content": content})

    # Append the latest user message
    messages.append({"role": "user", "content": user_message})

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=temperature,
    )
    return response.choices[0].message.content.strip()


# Backwards-compatible alias so any file still calling call_gemini works
call_gemini = call_llm
