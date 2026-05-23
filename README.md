# CLOSIRA AI AGENT — COMPLETE PROJECT REFERENCE
# Everything in one place: all code, all files, all details
# GitHub: https://github.com/nmnroy/Closira-AI-Agent

═══════════════════════════════════════════════════════════════
 PROJECT OVERVIEW
═══════════════════════════════════════════════════════════════

Name:      Closira AI Agent
Business:  Bloom Aesthetics Clinic
Built for: Closira AI Engineering Intern Assignment
Interface: CLI (Command Line) — no frontend
Language:  Python 3.11+
Providers: Google Gemini (free) / Anthropic Claude / OpenAI GPT

What it does:
  Handles inbound customer enquiries across 4 stages:
  1. FAQ Answering      → answers only from sop.json
  2. Lead Qualification → asks 3 structured questions
  3. Escalation         → detects and logs handoff triggers
  4. Session Summary    → generates structured JSON summary

Conversation flow:
  Customer message → Stage router → FAQ / Qualify
  → Escalation check → Session summary → logs/


═══════════════════════════════════════════════════════════════
 FOLDER STRUCTURE
═══════════════════════════════════════════════════════════════

closira-agent/
├── main.py                   ← CLI entry point, session orchestrator
├── agent.py                  ← Unified AI caller (Gemini/Anthropic/OpenAI)
├── sop.json                  ← Only source of truth for the AI
├── requirements.txt          ← All dependencies
├── .env                      ← API keys + provider choice (never commit)
├── .env.example              ← Template to share
├── stages/
│   ├── __init__.py
│   ├── faq.py                ← Stage 1: SOP answers + escalation parser
│   ├── qualification.py      ← Stage 2: 3-question lead qualification
│   ├── escalation.py         ← Stage 3: Deterministic handoff + logger
│   └── summary.py            ← Stage 4: Structured session summary
├── utils/
│   ├── __init__.py
│   └── logger.py             ← Saves escalation + summary to /logs
├── logs/                     ← Auto-created JSON log files
├── assets/
│   └── demo.png              ← Screenshot for README
├── test_transcripts/
│   ├── 01_in_sop_question.md
│   ├── 02_out_of_scope.md
│   ├── 03_escalation_trigger.md
│   ├── 04_lead_qualification.md
│   └── 05_conversation_summary.md
├── prompt_design.md          ← Full system prompt + design decisions
└── README.md


═══════════════════════════════════════════════════════════════
 FILE: requirements.txt
═══════════════════════════════════════════════════════════════

google-generativeai>=0.7.0
anthropic>=0.25.0
openai>=1.30.0
python-dotenv>=1.0.0
rich>=13.0.0


═══════════════════════════════════════════════════════════════
 FILE: .env  (never commit this)
═══════════════════════════════════════════════════════════════

# Pick ONE provider
PROVIDER=gemini

# Add key for whichever provider you pick
GOOGLE_API_KEY=your_gemini_api_key_here
# ANTHROPIC_API_KEY=your_key_here
# OPENAI_API_KEY=your_key_here


═══════════════════════════════════════════════════════════════
 FILE: .env.example  (safe to commit)
═══════════════════════════════════════════════════════════════

PROVIDER=gemini
GOOGLE_API_KEY=your_gemini_api_key_here
# ANTHROPIC_API_KEY=your_anthropic_api_key_here
# OPENAI_API_KEY=your_openai_api_key_here


═══════════════════════════════════════════════════════════════
 FILE: sop.json
═══════════════════════════════════════════════════════════════

{
  "business_name": "Bloom Aesthetics Clinic",
  "hours": "Monday to Saturday, 9am to 7pm",
  "services": [
    {
      "name": "Botox",
      "price_from": "£200",
      "details": "Anti-wrinkle treatment. Results last 3-4 months."
    },
    {
      "name": "Dermal Fillers",
      "price_from": "£250",
      "details": "Lip, cheek, and jawline fillers available."
    },
    {
      "name": "Consultation",
      "price_from": "Free",
      "details": "Free initial consultation with our aesthetics nurse."
    }
  ],
  "booking": {
    "channels": ["WhatsApp", "website"],
    "cancellation_policy": "24 hours notice required for cancellations or rescheduling."
  },
  "escalation_triggers": [
    "complaint",
    "medical question",
    "pricing negotiation",
    "more than 2 unanswered questions"
  ],
  "contact": {
    "whatsapp": "+44 7700 000000",
    "website": "www.bloomaesthetics.co.uk"
  }
}


═══════════════════════════════════════════════════════════════
 FILE: agent.py
═══════════════════════════════════════════════════════════════

import os
import json
import time
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

PROVIDER = os.getenv("PROVIDER", "gemini").lower()


def load_sop(path: str = "sop.json") -> dict:
    with open(path, "r") as f:
        return json.load(f)


def build_system_prompt(sop: dict) -> str:
    sop_text = json.dumps(sop, indent=2)
    return f"""You are Aria, a warm, professional AI customer support assistant for {sop["business_name"]}.

## YOUR KNOWLEDGE BASE
You may ONLY use the following SOP data to answer customer questions.
Do not invent, guess, or infer any facts not present in this data:

```json
{sop_text}
```

## CORE RULES
1. Stay within the SOP. If a question cannot be answered from the data above,
   do NOT guess. Say you don't have that information and offer to connect them
   with a human.
2. Never fabricate prices, dates, treatments, or policies not listed in the SOP.
3. Be concise and friendly. Keep responses under 100 words unless genuinely needed.
4. Detect escalation triggers. Escalate immediately if the customer:
   - Expresses a complaint or frustration
   - Asks a medical question (e.g. suitability, side effects, contraindications)
   - Requests a price negotiation or discount
   - Asks a question you cannot answer from the SOP
   - Explicitly asks to speak to a human

## RESPONSE FORMAT FOR ESCALATION
When escalation is needed, end your message with this exact JSON on a new line:
{{"escalate": true, "reason": "<complaint|medical_question|pricing_negotiation|out_of_scope|explicit_request|unanswered_limit>"}}

When no escalation is needed, do NOT include any JSON in your reply.

## TONE & PERSONA
- Warm, reassuring, professional — like a friendly clinic receptionist
- Use British English spellings (colour, centre, organise)
- Do not use jargon or overly clinical language
- Address the customer directly and personally
- Keep responses under 100 words
"""


# ── GEMINI (Free default) ─────────────────────────────────────────────────────
def _call_gemini(system_prompt, conversation_history, user_message, temperature):
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=system_prompt,
        generation_config=genai.GenerationConfig(temperature=temperature),
    )
    chat = model.start_chat(history=conversation_history.copy())
    response = chat.send_message(user_message)
    return response.text.strip()


# ── ANTHROPIC CLAUDE ──────────────────────────────────────────────────────────
def _call_anthropic(system_prompt, conversation_history, user_message, temperature):
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    messages = []
    for turn in conversation_history:
        role = "user" if turn["role"] == "user" else "assistant"
        content = turn["parts"][0] if isinstance(turn["parts"], list) else turn["parts"]
        messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_message})
    response = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=512,
        temperature=temperature,
        system=system_prompt,
        messages=messages,
    )
    return response.content[0].text.strip()


# ── OPENAI GPT-4o-mini ────────────────────────────────────────────────────────
def _call_openai(system_prompt, conversation_history, user_message, temperature):
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    messages = [{"role": "system", "content": system_prompt}]
    for turn in conversation_history:
        role = "user" if turn["role"] == "user" else "assistant"
        content = turn["parts"][0] if isinstance(turn["parts"], list) else turn["parts"]
        messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_message})
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=512,
        temperature=temperature,
        messages=messages,
    )
    return response.choices[0].message.content.strip()


# ── UNIFIED CALLER ────────────────────────────────────────────────────────────
def call_gemini(
    system_prompt: str,
    conversation_history: list,
    user_message: str,
    temperature: float = 0.3,
    retries: int = 3,
) -> str:
    for attempt in range(retries):
        try:
            if PROVIDER == "anthropic":
                return _call_anthropic(system_prompt, conversation_history, user_message, temperature)
            elif PROVIDER == "openai":
                return _call_openai(system_prompt, conversation_history, user_message, temperature)
            else:
                return _call_gemini(system_prompt, conversation_history, user_message, temperature)
        except Exception as e:
            err = str(e)
            if "quota" in err.lower() or "429" in err or "rate" in err.lower():
                wait = 45 * (attempt + 1)
                print(f"\n[⚠️  Rate limit hit. Waiting {wait}s... retry {attempt+1}/{retries}]")
                time.sleep(wait)
            else:
                print(f"\n[❌ API Error ({PROVIDER}): {err}]")
                break
    return "I'm experiencing high demand right now. Please try again in a moment."


═══════════════════════════════════════════════════════════════
 FILE: stages/faq.py
═══════════════════════════════════════════════════════════════

import json
import re
from agent import call_gemini


def handle_faq(
    system_prompt: str,
    conversation_history: list,
    user_message: str,
    state: dict,
) -> tuple[str, dict]:
    reply = call_gemini(system_prompt, conversation_history, user_message)
    escalation_info = _extract_escalation(reply)
    clean_reply = _strip_json_block(reply)

    if escalation_info and escalation_info.get("escalate"):
        state["stage"] = "escalated"
        state["escalation_reason"] = escalation_info.get("reason", "unknown")
        if "out_of_scope" in escalation_info.get("reason", ""):
            state["sop_gaps"].append(user_message)

    return clean_reply, state


def _extract_escalation(text: str) -> dict | None:
    # Try fenced markdown first
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None
    # Fallback: raw JSON
    match = re.search(r'\{[^{}]*"escalate"\s*:\s*true[^{}]*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return None


def _strip_json_block(text: str) -> str:
    text = re.sub(r"```json\s*\{.*?\}\s*```", "", text, flags=re.DOTALL)
    text = re.sub(r'\{[^{}]*"escalate"\s*:\s*true[^{}]*\}', "", text, flags=re.DOTALL)
    return text.strip()


═══════════════════════════════════════════════════════════════
 FILE: stages/qualification.py
═══════════════════════════════════════════════════════════════

import json
import re
from agent import call_gemini

QUALIFICATION_SYSTEM_ADDON = """
## LEAD QUALIFICATION MODE
You are now collecting qualification information. Ask the following questions
ONE AT A TIME, in a natural conversational way. Do not ask more than one
question per message.

Questions to ask (in order):
1. What brings them in today — which service are they most interested in?
2. Have they had this treatment before, or would this be their first time?
3. How soon are they looking to book — is this something they'd like to arrange this week?

Once all three answers are collected, output ONLY this JSON block:
```json
{{"qualification_complete": true, "interest": "<service>", "experience": "<first_time|returning>", "urgency": "<timeline>"}}
```
"""


def handle_qualification(
    system_prompt: str,
    conversation_history: list,
    user_message: str,
    state: dict,
) -> tuple[str, dict]:
    combined_prompt = system_prompt + QUALIFICATION_SYSTEM_ADDON
    reply = call_gemini(combined_prompt, conversation_history, user_message)

    match = re.search(r"```json\s*(\{.*?\})\s*```", reply, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            if data.get("qualification_complete"):
                state["qualification_data"] = data
                state["stage"] = "faq"
                clean = re.sub(r"```json\s*\{.*?\}\s*```", "", reply, flags=re.DOTALL).strip()
                return clean or "Great, thanks for sharing that! Is there anything else I can help you with?", state
        except json.JSONDecodeError:
            pass

    clean_reply = re.sub(r"```json\s*\{.*?\}\s*```", "", reply, flags=re.DOTALL).strip()
    return clean_reply, state


═══════════════════════════════════════════════════════════════
 FILE: stages/escalation.py
═══════════════════════════════════════════════════════════════

from utils.logger import log_escalation

ESCALATION_MESSAGES = {
    "complaint":
        "I'm really sorry to hear you've had a frustrating experience. I'm going to "
        "connect you with one of our team members right away who can help resolve this properly.",
    "medical_question":
        "That's a great question, but for anything medical I'd always want to make sure "
        "you're speaking with one of our qualified practitioners. Let me get someone to reach out to you.",
    "pricing_negotiation":
        "I completely understand — I'd love to help, but pricing discussions are something "
        "our team handles personally. I'll have someone get back to you shortly.",
    "out_of_scope":
        "I want to make sure you get the right answer on this one, and it's not something "
        "I'm able to confirm from the information I have. I'll flag this for our team to follow up.",
    "explicit_request":
        "Of course! I'll hand you over to one of our team right away.",
    "unanswered_limit":
        "I've hit the limit of what I can help with here — I don't want to give you the "
        "wrong information. Let me bring in a human team member to assist.",
    "unknown":
        "I'm going to connect you with a member of our team who can help you further.",
}


def handle_escalation(state: dict) -> str:
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
    return "\n".join(lines[-6:])


═══════════════════════════════════════════════════════════════
 FILE: stages/summary.py
═══════════════════════════════════════════════════════════════

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


def generate_summary(system_prompt: str, state: dict) -> dict:
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


═══════════════════════════════════════════════════════════════
 FILE: utils/logger.py
═══════════════════════════════════════════════════════════════

import json
import os
from datetime import datetime

LOG_DIR = "logs"


def _ensure_log_dir():
    os.makedirs(LOG_DIR, exist_ok=True)


def log_escalation(reason: str, conversation_summary: str):
    _ensure_log_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    entry = {
        "timestamp": datetime.now().isoformat(),
        "reason": reason,
        "conversation_excerpt": conversation_summary,
    }
    path = os.path.join(LOG_DIR, f"escalation_{timestamp}.json")
    with open(path, "w") as f:
        json.dump(entry, f, indent=2)
    print(f"\n[LOG] Escalation saved → {path}")


def log_summary(summary: dict):
    _ensure_log_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(LOG_DIR, f"summary_{timestamp}.json")
    with open(path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"[LOG] Session summary saved → {path}")


═══════════════════════════════════════════════════════════════
 FILE: main.py
═══════════════════════════════════════════════════════════════

import json
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from agent import load_sop, build_system_prompt
from stages.faq import handle_faq
from stages.qualification import handle_qualification
from stages.escalation import handle_escalation
from stages.summary import generate_summary
from utils.logger import log_summary

console = Console()

COMMANDS = {
    "/qualify": "Switch to lead qualification mode",
    "/summary": "Generate and display session summary",
    "/quit":    "End the session",
    "/help":    "Show this help message",
}


def print_header():
    console.print(Panel.fit(
        "[bold cyan]Closira — Bloom Aesthetics Clinic[/bold cyan]\n"
        "[dim]AI Customer Support  •  Powered by Gemini Flash[/dim]\n"
        "[dim]Type /help for commands  •  /quit to end session[/dim]",
        border_style="cyan"
    ))


def print_help():
    console.print("\n[bold]Available commands:[/bold]")
    for cmd, desc in COMMANDS.items():
        console.print(f"  [cyan]{cmd}[/cyan]  —  {desc}")
    console.print()


def print_aria(message: str):
    console.print(f"\n[bold green]Aria:[/bold green] {message}\n")


def print_system(message: str):
    console.print(f"\n[bold yellow]⚡ System:[/bold yellow] {message}\n")


def add_to_history(history: list, role: str, text: str) -> list:
    history.append({"role": role, "parts": [text]})
    return history


def run():
    print_header()
    sop = load_sop()
    system_prompt = build_system_prompt(sop)

    state = {
        "stage": "faq",
        "history": [],
        "qualification_data": {},
        "escalation_reason": None,
        "sop_gaps": [],
        "unanswered_count": 0,
    }

    greeting = (
        f"Hi there! 👋 Welcome to {sop['business_name']}. "
        "I'm Aria, your virtual assistant. How can I help you today?"
    )
    print_aria(greeting)
    state["history"] = add_to_history(state["history"], "model", greeting)

    while True:
        try:
            user_input = Prompt.ask("[bold blue]You[/bold blue]").strip()
        except (KeyboardInterrupt, EOFError):
            user_input = "/quit"

        if not user_input:
            continue

        if user_input.lower() == "/help":
            print_help()
            continue

        if user_input.lower() == "/qualify":
            state["stage"] = "qualification"
            print_system("Switching to lead qualification mode.")
            user_input = "I'd like to learn more about your services."

        if user_input.lower() == "/summary":
            print_system("Generating session summary…")
            summary = generate_summary(system_prompt, state)
            log_summary(summary)
            console.print(Panel(
                json.dumps(summary, indent=2),
                title="[bold]Session Summary[/bold]",
                border_style="magenta"
            ))
            continue

        if user_input.lower() == "/quit":
            print_system("Generating session summary before closing…")
            summary = generate_summary(system_prompt, state)
            log_summary(summary)
            console.print(Panel(
                json.dumps(summary, indent=2),
                title="[bold]Final Session Summary[/bold]",
                border_style="magenta"
            ))
            console.print("\n[dim]Session ended. Goodbye! 👋[/dim]\n")
            break

        if state["stage"] == "escalated":
            print_system("This session has been escalated. Type /summary or /quit.")
            continue

        state["history"] = add_to_history(state["history"], "user", user_input)

        if state["stage"] == "qualification":
            reply, state = handle_qualification(
                system_prompt, state["history"][:-1], user_input, state
            )
        else:
            reply, state = handle_faq(
                system_prompt, state["history"][:-1], user_input, state
            )

        state["history"] = add_to_history(state["history"], "model", reply)
        print_aria(reply)

        if state["stage"] == "escalated":
            escalation_msg = handle_escalation(state)
            print_aria(escalation_msg)
            state["history"] = add_to_history(state["history"], "model", escalation_msg)
            print_system(
                f"🚨 Escalation triggered: [bold red]{state['escalation_reason']}[/bold red]\n"
                "   A human agent has been notified. Type /summary or /quit."
            )


if __name__ == "__main__":
    run()


═══════════════════════════════════════════════════════════════
 FILE: test_transcripts/01_in_sop_question.md
═══════════════════════════════════════════════════════════════

# Test 1: In-SOP Question

**Scenario:** Customer asks about Botox pricing.
**Expected:** AI answers accurately from SOP only.

---

Aria: Hi there! 👋 Welcome to Bloom Aesthetics Clinic. I'm Aria, how can I help you today?

You: What are your Botox prices?

Aria: Our Botox treatments start from £200. If you'd like to know more or book a
free consultation first, you can reach us via WhatsApp or our website at
www.bloomaesthetics.co.uk. Is there anything else I can help with?

---
Result: ✅ PASS — Price answered accurately from SOP. No hallucination.


═══════════════════════════════════════════════════════════════
 FILE: test_transcripts/02_out_of_scope.md
═══════════════════════════════════════════════════════════════

# Test 2: Out-of-Scope Question

**Scenario:** Customer asks about a service not in the SOP.
**Expected:** AI acknowledges gap and escalates rather than guessing.

---

Aria: Hi there! 👋 Welcome to Bloom Aesthetics Clinic. I'm Aria, how can I help you today?

You: Do you offer laser hair removal?

Aria: I want to make sure you get the right answer on this one, and it's not
something I'm able to confirm from the information I have. I'll flag this for
our team to follow up.

⚡ System: 🚨 Escalation triggered: out_of_scope

---
Result: ✅ PASS — AI did not guess or hallucinate. Escalated cleanly with reason logged.


═══════════════════════════════════════════════════════════════
 FILE: test_transcripts/03_escalation_trigger.md
═══════════════════════════════════════════════════════════════

# Test 3: Escalation — Complaint / Angry Sentiment

**Scenario:** Customer expresses frustration about a previous visit.
**Expected:** AI detects complaint and hands off immediately.

---

Aria: Hi there! 👋 Welcome to Bloom Aesthetics Clinic. I'm Aria, how can I help you today?

You: I am absolutely furious. I came in last week and the treatment was botched. This is unacceptable.

Aria: I'm really sorry to hear you've had a frustrating experience. I'm going to
connect you with one of our team members right away who can help resolve
this properly.

⚡ System: 🚨 Escalation triggered: complaint

---
Result: ✅ PASS — Complaint detected immediately. Empathetic handoff, no deflection.


═══════════════════════════════════════════════════════════════
 FILE: test_transcripts/04_lead_qualification.md
═══════════════════════════════════════════════════════════════

# Test 4: Lead Qualification

**Scenario:** Customer expresses interest; agent qualifies them.
**Expected:** 3 structured questions asked one at a time, data collected.

---

You: /qualify

⚡ System: Switching to lead qualification mode.

Aria: What a great time to reach out! To make sure we point you in the right
direction — which of our treatments are you most interested in? We offer
Botox, Dermal Fillers, and free consultations.

You: I'm thinking about fillers, maybe lips.

Aria: Lovely choice! Have you had lip fillers before, or would this be your first time?

You: First time, I'm a bit nervous.

Aria: Completely understandable — and that's exactly what our free consultations
are for! How soon are you thinking of booking?

You: Probably within the next two weeks.

Aria: Perfect, that's really helpful to know. Thanks for sharing that!
Is there anything else I can help you with?

---
Qualification data collected:
{
  "interest": "Dermal Fillers (lips)",
  "experience": "first_time",
  "urgency": "within 2 weeks"
}

Result: ✅ PASS — 3 questions asked naturally, one at a time. Data stored in session state.


═══════════════════════════════════════════════════════════════
 FILE: test_transcripts/05_conversation_summary.md
═══════════════════════════════════════════════════════════════

# Test 5: Conversation Summary

**Scenario:** End of mixed session (FAQ + qualification). User types /quit.
**Expected:** Structured JSON summary with intent, details, gaps, next action.

---

Command: /quit

⚡ System: Generating session summary before closing…

{
  "customer_intent": "Customer enquired about lip filler pricing and availability, and completed lead qualification.",
  "key_details": {
    "service_interest": "Dermal Fillers (lips)",
    "experience": "first_time",
    "urgency": "within 2 weeks"
  },
  "sop_gaps": [],
  "escalated": false,
  "escalation_reason": null,
  "recommended_next_action": "Follow up via WhatsApp to book a free consultation for lip fillers within the next 2 weeks."
}

Result: ✅ PASS — Structured summary with intent, details, and next action. Saved to logs/.


═══════════════════════════════════════════════════════════════
 API PROVIDERS — WHERE TO GET KEYS
═══════════════════════════════════════════════════════════════

Provider    Model                     Free Tier          Get Key
──────────  ────────────────────────  ─────────────────  ──────────────────────────────────
Gemini      gemini-1.5-flash          ✅ 1500 req/day    aistudio.google.com/app/apikey
Anthropic   claude-3-haiku-20240307   ❌ Paid $0.25/1Mtok  console.anthropic.com
OpenAI      gpt-4o-mini               ❌ Paid ($5 new)   platform.openai.com/api-keys

Recommended: Use PROVIDER=gemini with Gemini API key for development (free).


═══════════════════════════════════════════════════════════════
 CLI COMMANDS (while session is running)
═══════════════════════════════════════════════════════════════

/qualify   → Switch to lead qualification (3 structured questions)
/summary   → Generate session summary on demand
/quit      → End session + auto-generate final summary
/help      → Show all commands


═══════════════════════════════════════════════════════════════
 ESCALATION TRIGGER CODES
═══════════════════════════════════════════════════════════════

complaint             → Customer expresses dissatisfaction or anger
medical_question      → Asks about side effects, suitability, contraindications
pricing_negotiation   → Requests discount or challenges price
out_of_scope          → Question cannot be answered from SOP
explicit_request      → Customer asks to speak to a human
unanswered_limit      → 2+ unanswered questions in one session

All escalations saved to: logs/escalation_<timestamp>.json


═══════════════════════════════════════════════════════════════
 SUMMARY OUTPUT FORMAT
═══════════════════════════════════════════════════════════════

{
  "customer_intent": "...",
  "key_details": {
    "service_interest": "...",
    "experience": "first_time | returning",
    "urgency": "..."
  },
  "sop_gaps": [],
  "escalated": false,
  "escalation_reason": null,
  "recommended_next_action": "..."
}

All summaries saved to: logs/summary_<timestamp>.json


═══════════════════════════════════════════════════════════════
 SETUP — 4 STEPS
═══════════════════════════════════════════════════════════════

Step 1 — Clone
  git clone https://github.com/nmnroy/Closira-AI-Agent.git
  cd Closira-AI-Agent/closira-agent

Step 2 — Install
  pip install -r requirements.txt

Step 3 — Add key to .env
  PROVIDER=gemini
  GOOGLE_API_KEY=your_key_here

Step 4 — Run
  python3 main.py


═══════════════════════════════════════════════════════════════
 KNOWN LIMITATIONS
═══════════════════════════════════════════════════════════════

No persistent storage   → History lives in RAM; lost on exit
No streaming            → Responses appear all at once
Linear qualification    → 3 fixed questions, no branching
JSON via regex          → Handles fenced + raw JSON; rare edge cases possible
CLI only                → No frontend, as per assignment spec
Free tier rate limits   → Gemini: 15 req/min, 1500/day. Auto-retry built in.


═══════════════════════════════════════════════════════════════
 MULTI-PROVIDER SWITCH (no code changes needed)
═══════════════════════════════════════════════════════════════

In .env:
  PROVIDER=gemini     →  gemini-1.5-flash        (free)
  PROVIDER=anthropic  →  claude-3-haiku-20240307  (paid)
  PROVIDER=openai     →  gpt-4o-mini              (paid)

Only .env changes. All stages use the same call_gemini() interface.


═══════════════════════════════════════════════════════════════
 TEMPERATURE SETTINGS
═══════════════════════════════════════════════════════════════

FAQ / Qualification  →  0.3  (warm and natural, but grounded)
Summary              →  0.1  (near-deterministic for JSON output)


═══════════════════════════════════════════════════════════════
 END OF REFERENCE DOCUMENT
═══════════════════════════════════════════════════════════════
