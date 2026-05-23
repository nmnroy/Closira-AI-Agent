# Prompt Design — Closira AI Agent

## Overview

This document covers the full system prompt, all design decisions, hallucination prevention strategy, escalation logic, and tone/persona choices for the Closira AI customer support agent built for **Bloom Aesthetics Clinic**.

---

## Full System Prompt

```
You are Aria, a warm, professional AI customer support assistant for {business_name}.

## YOUR KNOWLEDGE BASE
You may ONLY use the following SOP data to answer customer questions.
Do not invent, guess, or infer any facts not present in this data:

{sop_json}

## CORE RULES
1. Stay within the SOP. If a question cannot be answered from the data above,
   do NOT guess. Say you don't have that information and offer to connect them
   with a human.
2. Never fabricate prices, dates, treatments, or policies not listed in the SOP.
3. Be concise and friendly. Keep responses under 100 words unless a longer
   answer is genuinely needed.
4. Detect escalation triggers. You must escalate immediately if the customer:
   - Expresses a complaint or frustration
   - Asks a medical question (e.g. suitability, side effects, contraindications)
   - Requests a price negotiation or discount
   - Asks a question you cannot answer from the SOP (counts toward the 2-question limit)
   - Explicitly asks to speak to a human

## RESPONSE FORMAT FOR ESCALATION
When escalation is needed, always end your message with this exact JSON block on a new line:
{"escalate": true, "reason": "<one of: complaint | medical_question | pricing_negotiation | out_of_scope | explicit_request | unanswered_limit>"}

When no escalation is needed, do NOT include any JSON in your reply.

## TONE & PERSONA
- Warm, reassuring, and professional — like a friendly clinic receptionist
- Use British English spellings (e.g. "colour", "centre", "organise")
- Do not use jargon or overly clinical language
- Address the customer directly and personally
- Keep responses under 100 words
```

---

## Design Decisions

### 1. Dynamic SOP Injection

The SOP data (`sop.json`) is injected directly into the system prompt at runtime as a formatted JSON string. This was a deliberate choice over:

- **Fine-tuning** — too expensive and inflexible; the SOP can change weekly
- **RAG/vector search** — overkill for a single-page SOP document
- **Hardcoded facts** — breaks the moment the business updates pricing or hours

By injecting the full SOP as structured JSON, the model has a single, authoritative source of truth it can cite directly. Swapping businesses requires only changing `sop.json` — no prompt edits needed.

---

### 2. Hallucination Prevention

Three explicit layers prevent the model from fabricating information:

**Layer 1 — Hard instruction in system prompt:**
The prompt uses the phrase *"You may ONLY use the following SOP data"* — phrased as an absolute rule, not a suggestion. The word "ONLY" is intentional; it removes ambiguity about whether the model can supplement with training knowledge.

**Layer 2 — Structured SOP as JSON:**
Injecting the SOP as machine-readable JSON makes it easy for the model to locate specific facts (prices, hours, services) by key name rather than reconstructing them from memory. It also makes the boundaries of available knowledge visually explicit.

**Layer 3 — Escalation as the safe fallback:**
Rather than allowing the model to say "I think..." or attempt a partial answer, the prompt instructs it to treat any unanswerable question as an escalation trigger. This converts "I don't know" from a hallucination risk into a safe, useful handoff action. The system tracks a counter of unanswered questions; hitting 2 forces escalation regardless of model confidence.

---

### 3. Confidence-Based Escalation Logic

Escalation is triggered through two mechanisms working in parallel:

#### Model-Driven (Soft Detection)
The model is instructed to embed a structured JSON flag at the end of its response when it determines a handoff is warranted:

```json
{"escalate": true, "reason": "out_of_scope"}
```

Reason codes are standardised across six categories:

| Code | Trigger |
|------|---------|
| `complaint` | Customer expresses dissatisfaction or anger |
| `medical_question` | Asks about side effects, suitability, contraindications |
| `pricing_negotiation` | Requests a discount or challenges the price |
| `out_of_scope` | Question cannot be answered from SOP |
| `explicit_request` | Customer says "speak to a human" or equivalent |
| `unanswered_limit` | 2+ questions unanswered in the session |

The `stages/faq.py` parser extracts this flag using regex that handles both fenced markdown (` ```json `) and raw inline JSON — the latter being a common model output variation.

#### Rule-Based (Hard Detection)
A session-level counter (`unanswered_count`) is maintained in application state. If the model flags `out_of_scope` twice in a session, escalation is forced on the third unanswerable question regardless of what the model outputs. This guards against edge cases where the model is overconfident about a partial answer.

All escalations are:
- Logged to `logs/escalation_<timestamp>.json` with reason and conversation excerpt
- Surfaced to the customer with a human, empathetic message (not a generic error)
- Stored in session state so the CLI prevents further AI responses after handoff

---

### 4. Tone and Persona

**Name:** "Aria" — chosen to feel approachable and human without being overly robotic or obviously AI-branded.

**Register:** British English throughout (spellings, idioms), consistent with the clinic's UK context. This is enforced in the system prompt with explicit examples ("colour", "centre", "organise").

**Response length:** Capped at ~100 words per response. This mirrors the natural character limit of WhatsApp messages — the primary channel for SMB customer communication — and prevents the model from producing long, clinical paragraphs that would feel out of place in a chat interface.

**Language style:** Plain English over clinical jargon. A customer asking "will this hurt?" should receive a warm, reassuring answer — not a medical disclaimer.

---

### 5. Stage Separation Architecture

Each stage is a separate Python module with its own prompt additions layered on top of the base system prompt:

```
Base system prompt (Aria persona + SOP + rules)
       │
       ├── stages/faq.py          → No additions; base prompt only
       ├── stages/qualification.py → Adds qualification question sequence
       ├── stages/escalation.py   → Deterministic; no AI call needed
       └── stages/summary.py      → Separate low-temperature call (0.1)
```

This separation ensures qualification questions do not leak into FAQ mode (which would confuse normal conversations) and that the summary stage, which requires deterministic structured output, uses a separate, near-zero-temperature call rather than the conversational temperature used elsewhere.

---

### 6. Temperature Settings

| Stage | Temperature | Rationale |
|-------|-------------|-----------|
| FAQ / Qualification | `0.3` | Warm and natural, but grounded; avoids creative fabrication |
| Summary | `0.1` | Near-deterministic; required for reliable JSON output |

A temperature of `0.0` was considered for the summary stage but `0.1` was chosen to allow minor phrasing variation while still producing consistent structure.

---

### 7. Multi-Provider Architecture

The `call_gemini()` function in `agent.py` is a unified caller that routes to one of three providers based on the `PROVIDER` environment variable:

| Provider | Model | Use Case |
|----------|-------|----------|
| `gemini` | `gemini-1.5-flash` | Default — 1,500 free req/day |
| `anthropic` | `claude-3-haiku-20240307` | Assignment-specified; cheapest Claude model |
| `openai` | `gpt-4o-mini` | Assignment-specified; cheapest GPT model |

History format conversion (Gemini uses `{"role", "parts"}` vs OpenAI/Anthropic `{"role", "content"}`) is handled inside each provider's private function, keeping the interface identical for all stages.

---

## Known Limitations and Trade-offs

| Limitation | Impact | Reason for Trade-off |
|------------|--------|----------------------|
| No persistent memory | Each session is stateless; history lives in RAM only | Keeps the system simple and dependency-free; a production system would use a database |
| No response streaming | Replies appear all at once, not token-by-token | Streaming adds significant complexity for a CLI demo |
| Linear qualification | 3 fixed questions with no branching | Branching logic requires a state machine; out of scope for this assignment |
| JSON extraction via regex | Occasionally brittle if model varies output format | The parser handles both fenced and raw JSON as a fallback |
| No authentication | CLI is open; no user identity | Not required for this assignment scope |
| Gemini history format | Gemini's `parts` field differs from OpenAI/Anthropic `content` | Handled via format conversion in each provider's private function |
