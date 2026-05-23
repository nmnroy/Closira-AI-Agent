# prompt_design.md — Closira AI Agent

## System Prompt

See `agent.py → build_system_prompt()` for the full dynamic prompt.

---

## Design Decisions

### 1. System Prompt Architecture
The system prompt is built dynamically by injecting the SOP JSON directly into the prompt at runtime. This means:
- The AI always has the exact, up-to-date SOP in context
- There is no ambiguity about what the AI "knows"
- The SOP can be swapped (e.g. different clinic) without touching prompt logic

### 2. Hallucination Prevention
Three explicit controls are in place:

**a) Hard instruction:** The prompt says "You may ONLY use the following SOP data. Do not invent, guess, or infer any facts not present in this data." This is phrased as an absolute rule, not a suggestion.

**b) Enumerated facts:** The SOP is injected as structured JSON, making it easy for the model to locate specific facts (prices, hours, channels) rather than recalling from training data.

**c) Escalation as the fallback:** Instead of guessing, the model is instructed to escalate when it cannot answer. This turns "I don't know" into a safe, useful action rather than a risky hallucination.

### 3. Confidence-Based Escalation
Escalation is triggered in two ways:

**Model-driven (soft):** The model is prompted to embed a JSON flag `{"escalate": true, "reason": "..."}` in its response when it determines a hand-off is needed. The `stages/faq.py` parser extracts this flag.

**Rule-based (hard):** A 2-unanswered-question counter is tracked in session state. If hit, escalation is forced regardless of model output. This prevents edge cases where the model is overconfident.

Reason codes are standardised: `complaint | medical_question | pricing_negotiation | out_of_scope | explicit_request | unanswered_limit`

### 4. Tone & Persona
- **Name:** "Aria" — friendly, approachable, not robotic
- **Register:** British English, warm but professional (clinic receptionist energy)
- **Length:** Capped at ~100 words per response to match WhatsApp/chat norms
- **No jargon:** Clinical or technical terms avoided in favour of plain English

### 5. Stage Separation
Each stage (FAQ, Qualification, Escalation, Summary) is a separate Python module with its own prompt additions. This means:
- Qualification questions don't leak into FAQ mode and vice versa
- The summary stage uses a separate, low-temperature call (0.1) for structured JSON output
- Escalation is purely rule-based with no AI needed — deterministic and reliable

### 6. Temperature Settings
- FAQ / Qualification: `0.3` — some warmth, but grounded
- Summary: `0.1` — near-deterministic for structured JSON output

---

## Known Limitations & Trade-offs
- **No persistent memory:** Each session is stateless; history is held in RAM only
- **No streaming:** Responses are returned in full, not streamed token-by-token
- **Gemini JSON extraction:** The model occasionally wraps JSON in markdown fences even when instructed not to — the parser handles this with regex stripping
- **Qualification branching:** Currently linear (3 fixed questions); a production system would branch based on answers
