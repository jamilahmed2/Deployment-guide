"""
command_engine.py — Orchestrated command execution with retry,
skip, rollback, and real-time Rich progress reporting.
"""

from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Callable, Optional
from enum import Enum

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich import box

from .ssh_manager import SSHManager, CommandResult

console = Console()


class StepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


@dataclass
class Step:
    name: str
    command: str
    description: str = ""
    sudo: bool = False
    env: dict = field(default_factory=dict)
    timeout: int = 300
    retries: int = 1
    critical: bool = True           # If True, failure stops the pipeline
    skip_on_success_pattern: str = ""  # Skip if stdout matches
    rollback_command: str = ""
    stream: bool = False            # Stream stdout live
    status: StepStatus = StepStatus.PENDING
    result: Optional[CommandResult] = None
    error_hint: str = ""            # Human-readable fix suggestion


@dataclass
class StepGroup:
    name: str
    icon: str
    steps: list[Step]
    description: str = ""


class CommandEngine:
    """
    Executes ordered step groups over an active SSH connection.
    Provides rich TUI output, retry logic, and execution history.
    """

    def __init__(self, ssh: SSHManager, dry_run: bool = False, interactive: bool = False):
        self.ssh = ssh
        self.dry_run = dry_run
        self.interactive = interactive
        self._history: list[dict] = []

    # ------------------------------------------------------------------ #
    #  Public API                                                           #
    # ------------------------------------------------------------------ #

    def run_group(self, group: StepGroup) -> bool:
        """Run all steps in a group. Returns True if all critical steps succeed."""
        console.print()
        console.print(Panel(
            f"[bold white]{group.icon}  {group.name}[/bold white]\n[dim]{group.description}[/dim]",
            border_style="blue",
            padding=(0, 2),
        ))

        all_ok = True
        for step in group.steps:
            ok = self._run_step(step)
            if not ok and step.critical:
                all_ok = False
                console.print(f"\n  [bold red]⛔ Pipeline halted at: {step.name}[/bold red]")
                if step.error_hint:
                    console.print(f"  [yellow]💡 Hint: {step.error_hint}[/yellow]")
                break

        self._record_group(group)
        return all_ok

    def run_groups(self, groups: list[StepGroup]) -> bool:
        """Run multiple groups in sequence."""
        for group in groups:
            ok = self.run_group(group)
            if not ok:
                return False
        return True

    def run_custom(self, command: str, sudo: bool = False) -> CommandResult:
        """Execute an ad-hoc command and return result."""
        console.print(f"\n  [cyan]▶[/cyan] Running: [bold]{command}[/bold]")
        if self.dry_run:
            console.print("  [yellow][DRY RUN] Command not executed[/yellow]")
            return CommandResult(command=command, stdout="", stderr="", exit_code=0)
        return self.ssh.exec(command, sudo=sudo, stream=True)

    # ------------------------------------------------------------------ #
    #  Internal step execution                                              #
    # ------------------------------------------------------------------ #

    def _run_step(self, step: Step) -> bool:
        step.status = StepStatus.RUNNING

        prefix = f"  [cyan]▶[/cyan] [bold]{step.name}[/bold]"
        if step.description:
            prefix += f" [dim]— {step.description}[/dim]"
        console.print(prefix)

        if self.dry_run:
            console.print(f"    [dim yellow][DRY RUN] $ {step.command}[/dim yellow]")
            step.status = StepStatus.SUCCESS
            return True

        if self.interactive:
            import questionary
            action = questionary.select(
                f"Step: {step.name}",
                choices=["Run", "Skip", "Edit command", "Abort"],
            ).ask()
            if action == "Skip":
                step.status = StepStatus.SKIPPED
                console.print(f"    [yellow]↷ Skipped[/yellow]")
                return True
            elif action == "Abort":
                raise KeyboardInterrupt("User aborted")
            elif action == "Edit command":
                step.command = questionary.text("Enter command:", default=step.command).ask()

        # Retry loop
        for attempt in range(1, step.retries + 1):
            if attempt > 1:
                step.status = StepStatus.RETRYING
                console.print(f"    [yellow]↻ Retry {attempt}/{step.retries}...[/yellow]")
                time.sleep(2)

            result = self.ssh.exec(
                step.command,
                sudo=step.sudo,
                env=step.env or None,
                timeout=step.timeout,
                stream=step.stream,
            )
            step.result = result

            if result.success:
                step.status = StepStatus.SUCCESS
                console.print(
                    f"    [green]✓[/green] Done in [dim]{result.duration:.1f}s[/dim]"
                )
                return True
            else:
                # Check skip pattern
                if step.skip_on_success_pattern and step.skip_on_success_pattern in result.stdout:
                    step.status = StepStatus.SKIPPED
                    console.print(f"    [dim]↷ Already done — skipping[/dim]")
                    return True

                if attempt == step.retries:
                    step.status = StepStatus.FAILED
                    console.print(
                        f"    [red]✗ Failed[/red] (exit {result.exit_code})"
                    )
                    if result.stderr:
                        console.print(f"    [dim red]{result.stderr[:300]}[/dim red]")

                    # Attempt rollback
                    if step.rollback_command:
                        console.print(f"    [yellow]↩ Rolling back...[/yellow]")
                        self.ssh.exec(step.rollback_command, sudo=step.sudo, stream=False)

                    return False

        return False

    # ------------------------------------------------------------------ #
    #  History & reporting                                                  #
    # ------------------------------------------------------------------ #

    def _record_group(self, group: StepGroup):
        self._history.append({
            "group": group.name,
            "steps": [
                {
                    "name": s.name,
                    "status": s.status.value,
                    "duration": s.result.duration if s.result else 0,
                    "exit_code": s.result.exit_code if s.result else None,
                }
                for s in group.steps
            ],
        })

    def print_summary(self):
        """Print a rich execution summary table."""
        table = Table(
            title="Execution Summary",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("Group", style="dim")
        table.add_column("Step")
        table.add_column("Status", justify="center")
        table.add_column("Duration", justify="right")

        status_style = {
            "success": "[green]✓ success[/green]",
            "failed": "[red]✗ failed[/red]",
            "skipped": "[yellow]↷ skipped[/yellow]",
            "pending": "[dim]- pending[/dim]",
        }

        for entry in self._history:
            for step in entry["steps"]:
                table.add_row(
                    entry["group"],
                    step["name"],
                    status_style.get(step["status"], step["status"]),
                    f"{step['duration']:.1f}s" if step["duration"] else "—",
                )

        console.print()
        console.print(table)
