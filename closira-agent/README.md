# Closira AI Agent — Bloom Aesthetics Clinic

An AI-powered customer support workflow built with Python and Google Gemini Flash.

## Setup

1. **Clone the repo and install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Add your API key:**
```bash
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY
```

3. **Run the CLI:**
```bash
python main.py
```

## Commands (in-session)
| Command | Action |
|---------|--------|
| `/qualify` | Start lead qualification flow |
| `/summary` | Generate session summary |
| `/quit` | End session (auto-generates summary) |
| `/help` | Show commands |

## Architecture
- **Stage 1 — FAQ:** `stages/faq.py` — answers from SOP only, detects escalation flags
- **Stage 2 — Qualification:** `stages/qualification.py` — structured 3-question flow
- **Stage 3 — Escalation:** `stages/escalation.py` — deterministic handler + logger
- **Stage 4 — Summary:** `stages/summary.py` — structured JSON summary via low-temp call

## SOP
Edit `sop.json` to change business info, services, or escalation triggers.

## Logs
All escalations and summaries are saved to `logs/` as timestamped JSON files.

## Trade-offs & Limitations
- No persistent storage — session history lives in RAM only
- Qualification is linear (3 fixed questions); no branching logic
- Summary relies on Gemini output being valid JSON (regex fallback included)
- No frontend — CLI only, as per assignment spec
