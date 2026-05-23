import json
import os
import sys
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich import print as rprint

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
        "[dim]AI Customer Support  •  Powered by OpenAI SDK (via Groq)[/dim]\n"
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
    """Append a turn to conversation history in internal format."""
    history.append({"role": role, "parts": text})
    return history


def extract_metadata(user_message: str, state: dict):
    """
    Helper to extract client details from the user's message.
    Populates key fields in state and sub-dicts (qualification_data/escalation_data).
    """
    msg_lower = user_message.lower()
    
    # Extract treatment_interest
    if "botox" in msg_lower:
        state["treatment_interest"] = "Botox"
    elif "filler" in msg_lower:
        state["treatment_interest"] = "Dermal Fillers"
    elif "consultation" in msg_lower:
        state["treatment_interest"] = "Consultation"

    # Extract client_name
    import re
    name_match = re.search(r"(?:my name is|i am|this is)\s+([A-Za-z\s]+)", user_message, re.IGNORECASE)
    if name_match:
        state["client_name"] = name_match.group(1).strip()
    elif "name" in state.get("last_question_asked", "").lower() or state.get("stage") == "qualification":
        # If the user just provides their name directly
        if not re.search(r"email|@|\.com|\d+", user_message) and len(user_message.split()) <= 4:
            state["client_name"] = user_message.strip()

    # Extract contact_email
    email_match = re.search(r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", user_message)
    if email_match:
        state["contact_email"] = email_match.group(1).strip()

    # Extract preferred_time
    time_match = re.search(
        r"((?:saturday|sunday|monday|tuesday|wednesday|thursday|friday|today|tomorrow|next week|this week)\s+(?:at|around)\s+\d+(?::\d+)?\s*(?:am|pm|o'clock)?)",
        user_message,
        re.IGNORECASE
    )
    if time_match:
        state["preferred_time"] = time_match.group(1).strip()
    else:
        # Fallback matching for "Saturday at 11am" style
        parts = re.split(r"and|,|\.", user_message, flags=re.IGNORECASE)
        for part in parts:
            if "at" in part and any(day in part.lower() for day in ["saturday", "sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "today", "tomorrow"]):
                clean_part = re.sub(r"(?:would be great|please|thanks|thank you)", "", part, flags=re.IGNORECASE).strip()
                state["preferred_time"] = clean_part

    # Copy extracted fields into qualification_data and escalation_data sub-dicts for evaluation verification
    for key in ["treatment_interest", "client_name", "contact_email", "preferred_time"]:
        if key in state:
            if "qualification_data" not in state or state["qualification_data"] is None:
                state["qualification_data"] = {}
            state["qualification_data"][key] = state[key]
            
            if "escalation_data" not in state or state["escalation_data"] is None:
                state["escalation_data"] = {}
            state["escalation_data"][key] = state[key]


def process_turn(user_message: str, state: dict, sop: dict) -> tuple[str, dict]:
    """
    Process a single user turn.
    Updates the state dict in place (history, stage, etc.).
    Returns (reply, updated_state).
    """
    from agent import build_system_prompt
    system_prompt = build_system_prompt(sop)

    # Extract metadata from the user message
    extract_metadata(user_message, state)

    # 1. Add user message to history
    state["history"] = add_to_history(state["history"], "user", user_message)

    # 2. Check if already escalated
    if state.get("stage") == "escalated":
        reply = handle_escalation(state)
        state["history"] = add_to_history(state["history"], "model", reply)
        return reply, state

    # 3. Route to correct stage handler based on current stage
    if state.get("stage") == "qualification":
        reply, state = handle_qualification(
            system_prompt, state["history"][:-1], user_message, state
        )
    else:
        reply, state = handle_faq(
            system_prompt, state["history"][:-1], user_message, state
        )

    # 4. Add AI reply to history
    state["history"] = add_to_history(state["history"], "model", reply)

    # 5. Intercept FAQ escalation reason "wants_to_book" to transition to qualification
    if state.get("stage") == "escalated" and state.get("escalation_reason") == "wants_to_book":
        state["stage"] = "qualification"
        state["escalation_reason"] = None
        # Keep the reply from FAQ stage: "I can help you book!"

    # 6. Handle escalation transition
    elif state.get("stage") == "escalated":
        escalation_msg = handle_escalation(state)
        state["history"] = add_to_history(state["history"], "model", escalation_msg)
        reply = escalation_msg

    # 7. Handle transition from qualification completion to escalated (for booking)
    elif state.get("stage") == "faq" and state.get("qualification_data", {}).get("qualification_complete"):
        state["stage"] = "escalated"
        state["escalation_reason"] = "explicit_request"
        escalation_msg = handle_escalation(state)
        state["history"] = add_to_history(state["history"], "model", escalation_msg)
        reply = escalation_msg

    return reply, state


def run_evaluation(transcript_path: str):
    """
    Run offline evaluation against a transcript file.
    """
    if not os.path.exists(transcript_path):
        console.print(f"[bold red]Error: Transcript file not found at {transcript_path}[/bold red]")
        sys.exit(1)
        
    with open(transcript_path, "r") as f:
        data = json.load(f)
        
    console.print(Panel.fit(
        f"[bold green]Running Evaluation: {data.get('name', 'Unnamed Scenario')}[/bold green]\n"
        f"[dim]File: {transcript_path}[/dim]",
        border_style="green"
    ))
    
    sop = load_sop()
    system_prompt = build_system_prompt(sop)
    
    state = {
        "stage": "faq",
        "qualification_data": {},
        "escalation_reason": None,
        "sop_gaps": [],
        "unanswered_count": 0,
        "history": []
    }
    
    passed_turns = 0
    total_turns = len(data.get("turns", []))
    
    for i, turn in enumerate(data.get("turns", [])):
        user_msg = turn["user"]
        expected_stage = turn.get("expected_stage")
        expected_extractions = turn.get("expected_extraction", {})
        
        console.print(f"\n[bold]Turn {i+1}:[/bold] User: {user_msg}")
        
        # If expected stage is SUMMARY, we transition to ended and generate summary
        if expected_stage == "SUMMARY":
            state["stage"] = "ended"
            summary = generate_summary(system_prompt, state)
            log_summary(summary)
            console.print(Panel(
                json.dumps(summary, indent=2),
                title="[bold magenta]Generated Summary[/bold magenta]",
                border_style="magenta"
            ))
            actual_stage = "SUMMARY"
            reply = "Session summarized."
        else:
            reply, state = process_turn(user_msg, state, sop)
            actual_stage = state["stage"].upper()
            if actual_stage == "ESCALATED":
                actual_stage = "ESCALATION"
                
        console.print(f"Aria: {reply}")
        console.print(f"Stage -> Expected: [cyan]{expected_stage}[/cyan] | Actual: [magenta]{actual_stage}[/magenta]")
        
        # Verify Stage
        stage_ok = expected_stage.upper() == actual_stage.upper()
        if expected_stage == "SUMMARY" and actual_stage == "SUMMARY":
            stage_ok = True
            
        # Verify Extractions
        extractions_ok = True
        missing_extractions = []
        for k, v in expected_extractions.items():
            actual_val = state.get(k) or state.get("qualification_data", {}).get(k) or state.get("escalation_data", {}).get(k)
            # Do case-insensitive comparison for string values
            if isinstance(v, str) and isinstance(actual_val, str):
                match_val = v.lower() in actual_val.lower() or actual_val.lower() in v.lower()
            else:
                match_val = v == actual_val
                
            if not match_val:
                extractions_ok = False
                missing_extractions.append((k, v, actual_val))
                
        if stage_ok and extractions_ok:
            console.print("[green]✔ Turn Passed[/green]")
            passed_turns += 1
        else:
            console.print("[red]✘ Turn Failed[/red]")
            if not stage_ok:
                console.print(f"  Stage mismatch: Expected {expected_stage}, got {actual_stage}")
            if not extractions_ok:
                for k, exp, act in missing_extractions:
                    console.print(f"  Extraction mismatch for '{k}': Expected '{exp}', got '{act}'")
                    
    console.print("\n" + "="*40)
    if passed_turns == total_turns:
        console.print(f"[bold green]Evaluation Passed: {passed_turns}/{total_turns} turns successful![/bold green]")
    else:
        console.print(f"[bold red]Evaluation Failed: {passed_turns}/{total_turns} turns successful.[/bold red]")


def run():
    print_header()

    sop = load_sop()
    system_prompt = build_system_prompt(sop)

    # Session state
    state = {
        "stage": "faq",          # faq | qualification | escalated | ended
        "history": [],
        "qualification_data": {},
        "escalation_reason": None,
        "sop_gaps": [],
        "unanswered_count": 0,
    }

    # Opening greeting
    greeting = (
        f"Hi there! 👋 Welcome to {sop['business_name']}. "
        "I'm Aria, your virtual assistant. How can I help you today?"
    )
    print_aria(greeting)
    state["history"] = add_to_history(state["history"], "model", greeting)

    while True:
        # ── Get user input ─────────────────────────────────────────────
        try:
            user_input = Prompt.ask("[bold blue]You[/bold blue]").strip()
        except (KeyboardInterrupt, EOFError):
            user_input = "/quit"

        if not user_input:
            continue

        # ── Handle commands ────────────────────────────────────────────
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

        # ── Already escalated ─────────────────────────────────────────
        if state["stage"] == "escalated":
            print_system("This session has been escalated to a human agent. Type /summary or /quit.")
            continue

        # ── Process Turn ──────────────────────────────────────────────
        old_stage = state.get("stage")
        reply, state = process_turn(user_input, state, sop)
        
        print_aria(reply)
        
        if old_stage != "escalated" and state.get("stage") == "escalated":
            print_system(
                f"🚨 Escalation triggered: [bold red]{state.get('escalation_reason', 'unknown')}[/bold red]\n"
                "   A human agent has been notified. Type /summary or /quit."
            )


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "evaluate":
            if len(sys.argv) > 2:
                run_evaluation(sys.argv[2])
            else:
                console.print("[bold red]Error: Please specify the path to the evaluation transcript file.[/bold red]")
                console.print("Usage: python main.py evaluate <transcript_path>")
        elif sys.argv[1] == "interactive":
            run()
        else:
            console.print(f"[bold red]Unknown command: {sys.argv[1]}[/bold red]")
            console.print("Usage: python main.py [interactive|evaluate <transcript_path>]")
    else:
        run()
