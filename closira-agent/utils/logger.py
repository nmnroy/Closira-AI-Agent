# utils/logger.py
import json
import os
from datetime import datetime
from rich.console import Console

console = Console()
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
    console.print(f"\n[bold red][LOG] Escalation saved → {path}[/bold red]")


def log_summary(summary: dict):
    _ensure_log_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(LOG_DIR, f"summary_{timestamp}.json")
    with open(path, "w") as f:
        json.dump(summary, f, indent=2)
    console.print(f"[bold green][LOG] Session summary saved → {path}[/bold green]")


def info(message: str):
    console.print(f"[bold blue]INFO:[/bold blue] {message}")


def warn(message: str):
    console.print(f"[bold yellow]WARN:[/bold yellow] {message}")


def error(message: str):
    console.print(f"[bold red]ERROR:[/bold red] {message}")


def log_api_call(action: str, details: str):
    console.print(f"[bold cyan]API CALL — {action}:[/bold cyan] [dim]{details}[/dim]")

