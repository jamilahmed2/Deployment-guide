#!/usr/bin/env python3
"""
DeployBot CLI — Production-grade server deployment automation.

Usage:
  deploybot deploy --host 1.2.3.4 --domain app.example.com --type remix --repo https://...
  deploybot manual --host 1.2.3.4
  deploybot profile save myserver
  deploybot profile use myserver
  deploybot server check --host 1.2.3.4
"""

from __future__ import annotations
import sys
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich import box

from core import (
    SSHManager, SSHCredentials,
    DeploymentEngine, DeploymentConfig,
    CredentialStore,
)
from core.command_engine import CommandEngine

app = typer.Typer(
    name="deploybot",
    help="🚀 DeployBot — Automated server deployment via SSH",
    rich_markup_mode="rich",
    no_args_is_help=True,
)
profile_app = typer.Typer(help="Manage deployment profiles")
server_app = typer.Typer(help="Server utility commands")
app.add_typer(profile_app, name="profile")
app.add_typer(server_app, name="server")

console = Console()

BANNER = """
[bold cyan]
  ██████╗ ███████╗██████╗ ██╗      ██████╗ ██╗   ██╗██████╗  ██████╗ ████████╗
  ██╔══██╗██╔════╝██╔══██╗██║     ██╔═══██╗╚██╗ ██╔╝██╔══██╗██╔═══██╗╚══██╔══╝
  ██║  ██║█████╗  ██████╔╝██║     ██║   ██║ ╚████╔╝ ██████╔╝██║   ██║   ██║
  ██║  ██║██╔══╝  ██╔═══╝ ██║     ██║   ██║  ╚██╔╝  ██╔══██╗██║   ██║   ██║
  ██████╔╝███████╗██║     ███████╗╚██████╔╝   ██║   ██████╔╝╚██████╔╝   ██║
  ╚═════╝ ╚══════╝╚═╝     ╚══════╝ ╚═════╝    ╚═╝   ╚═════╝  ╚═════╝    ╚═╝
[/bold cyan]
[dim]  Production-grade SSH deployment automation — v1.0.0[/dim]
"""


def _make_ssh(
    host: str,
    username: str,
    password: Optional[str],
    key_path: Optional[str],
    port: int,
) -> SSHManager:
    creds = SSHCredentials(
        host=host,
        port=port,
        username=username,
        password=password,
        key_path=key_path,
    )
    return SSHManager(creds)


# ------------------------------------------------------------------ #
#  deploy command                                                       #
# ------------------------------------------------------------------ #

@app.command()
def deploy(
    host: str = typer.Option(..., "--host", "-h", help="Server IP or hostname"),
    domain: str = typer.Option(..., "--domain", "-d", help="Domain name (e.g. app.example.com)"),
    project_type: str = typer.Option("node", "--type", "-t",
        help="Stack: node | remix | laravel | static | react | vue | next"),
    username: str = typer.Option("root", "--user", "-u"),
    password: Optional[str] = typer.Option(None, "--password", "-p", hide_input=True),
    key_path: Optional[str] = typer.Option(None, "--key", "-k", help="Path to SSH private key"),
    port: int = typer.Option(22, "--port"),
    repo: Optional[str] = typer.Option(None, "--repo", "-r", help="Git repository URL"),
    branch: str = typer.Option("main", "--branch"),
    app_port: int = typer.Option(3000, "--app-port"),
    db_type: Optional[str] = typer.Option(None, "--db", help="mysql | postgres"),
    db_name: str = typer.Option("appdb", "--db-name"),
    db_password: str = typer.Option("", "--db-password", hide_input=True),
    enable_ssl: bool = typer.Option(True, "--ssl/--no-ssl"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without executing"),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Confirm each step"),
):
    """[bold cyan]🚀 Full automated deployment[/bold cyan] — connects, installs, configures, deploys."""
    console.print(BANNER)

    cfg = DeploymentConfig(
        host=host,
        username=username,
        password=password,
        key_path=key_path,
        port=port,
        domain=domain,
        project_type=project_type,
        repo_url=repo,
        branch=branch,
        app_port=app_port,
        db_type=db_type,
        db_name=db_name,
        db_password=db_password,
        enable_ssl=enable_ssl,
        dry_run=dry_run,
        interactive=interactive,
    )

    ssh = _make_ssh(host, username, password, key_path, port)

    with ssh:
        if not ssh.is_connected():
            console.print("[red]Failed to connect. Aborting.[/red]")
            raise typer.Exit(1)

        engine = DeploymentEngine(ssh, cfg)
        ok = engine.deploy()
        raise typer.Exit(0 if ok else 1)


# ------------------------------------------------------------------ #
#  wizard command (interactive guided deploy)                          #
# ------------------------------------------------------------------ #

@app.command()
def wizard():
    """[bold green]🧙 Guided deployment wizard[/bold green] — interactive step-by-step setup."""
    console.print(BANNER)
    console.print(Panel("[bold]Welcome to DeployBot Wizard[/bold]\nAnswer a few questions to get started.", border_style="cyan"))

    host = Prompt.ask("  [cyan]Server IP or hostname[/cyan]")
    username = Prompt.ask("  Username", default="root")
    auth_type = Prompt.ask("  Auth type", choices=["password", "key"], default="key")
    password, key_path = None, None
    if auth_type == "password":
        import getpass
        password = getpass.getpass("  Password: ")
    else:
        key_path = Prompt.ask("  SSH key path", default="~/.ssh/id_rsa")

    domain = Prompt.ask("  [cyan]Domain name[/cyan]")
    project_type = Prompt.ask("  Stack", choices=["node", "remix", "laravel", "static", "react", "next"], default="node")
    repo = Prompt.ask("  Git repo URL (optional)", default="")
    enable_ssl = Confirm.ask("  Enable SSL (Let's Encrypt)?", default=True)
    db_type_raw = Prompt.ask("  Database", choices=["none", "mysql", "postgres"], default="none")
    db_type = None if db_type_raw == "none" else db_type_raw
    dry_run = Confirm.ask("  Dry run? (preview commands without executing)", default=False)

    console.print()
    console.print(Panel(
        f"  Host    : [white]{username}@{host}[/white]\n"
        f"  Domain  : [white]{domain}[/white]\n"
        f"  Stack   : [white]{project_type}[/white]\n"
        f"  Repo    : [white]{repo or 'none'}[/white]\n"
        f"  SSL     : [white]{enable_ssl}[/white]\n"
        f"  DB      : [white]{db_type or 'none'}[/white]",
        title="Configuration Summary",
        border_style="green",
    ))

    if not Confirm.ask("  Proceed with deployment?", default=True):
        raise typer.Exit(0)

    cfg = DeploymentConfig(
        host=host, username=username, password=password, key_path=key_path,
        domain=domain, project_type=project_type,
        repo_url=repo or None, enable_ssl=enable_ssl,
        db_type=db_type, dry_run=dry_run,
    )

    ssh = _make_ssh(host, username, password, key_path, 22)
    with ssh:
        engine = DeploymentEngine(ssh, cfg)
        engine.deploy()


# ------------------------------------------------------------------ #
#  manual command                                                       #
# ------------------------------------------------------------------ #

@app.command()
def manual(
    host: str = typer.Option(..., "--host", "-h"),
    username: str = typer.Option("root", "--user", "-u"),
    password: Optional[str] = typer.Option(None, "--password", hide_input=True),
    key_path: Optional[str] = typer.Option(None, "--key"),
    port: int = typer.Option(22),
):
    """[bold yellow]🔧 Manual mode[/bold yellow] — interactive SSH shell with command history."""
    ssh = _make_ssh(host, username, password, key_path, port)
    engine = CommandEngine(ssh, interactive=True)

    console.print(BANNER)
    console.print(Panel(f"[bold]Manual Mode[/bold] — {username}@{host}\nType commands to execute. [dim]'exit' to quit.[/dim]", border_style="yellow"))

    with ssh:
        while True:
            try:
                cmd = Prompt.ask("\n  [yellow]$[/yellow]")
                if cmd.strip().lower() in ("exit", "quit", "q"):
                    break
                if not cmd.strip():
                    continue
                result = engine.run_custom(cmd)
                if result.stdout:
                    console.print(f"[dim]{result.stdout}[/dim]")
                if result.stderr:
                    console.print(f"[red]{result.stderr}[/red]")
            except KeyboardInterrupt:
                break

    console.print("\n[dim]Session ended.[/dim]")


# ------------------------------------------------------------------ #
#  server subcommands                                                   #
# ------------------------------------------------------------------ #

@server_app.command("check")
def server_check(
    host: str = typer.Option(..., "--host", "-h"),
    username: str = typer.Option("root", "--user", "-u"),
    password: Optional[str] = typer.Option(None, "--password", hide_input=True),
    key_path: Optional[str] = typer.Option(None, "--key"),
):
    """Check server status — OS, disk, memory, running services."""
    ssh = _make_ssh(host, username, password, key_path, 22)

    checks = [
        ("OS",           "cat /etc/os-release | grep PRETTY_NAME"),
        ("Uptime",       "uptime -p"),
        ("Disk",         "df -h / | tail -1"),
        ("Memory",       "free -h | grep Mem"),
        ("NGINX",        "systemctl is-active nginx 2>/dev/null || echo inactive"),
        ("Node",         "node -v 2>/dev/null || echo 'not installed'"),
        ("NVM",          "bash -c 'source ~/.nvm/nvm.sh 2>/dev/null && nvm --version' || echo 'not installed'"),
        ("PM2",          "bash -c 'source ~/.nvm/nvm.sh 2>/dev/null; ver=$(pm2 --version 2>/dev/null); [ -n \"$ver\" ] && echo \"v$ver - $(pm2 list 2>/dev/null | grep -E \"online|stopped|errored\" | wc -l) app(s)\" || echo not installed' 2>/dev/null || echo 'not installed'"),
        ("MySQL",        "systemctl is-active mysql 2>/dev/null || echo inactive"),
        ("PostgreSQL",   "systemctl is-active postgresql 2>/dev/null || echo inactive"),
        ("Git",          "git --version 2>/dev/null || echo 'not installed'"),
        ("Certbot",      "certbot --version 2>/dev/null | head -1 || echo 'not installed'"),
        ("SSL Certs",    "certbot certificates 2>/dev/null | grep 'Certificate Name' | head -3 || echo 'none'"),
    ]

    table = Table(title=f"Server Status: {host}", box=box.ROUNDED, header_style="bold cyan")
    table.add_column("Check", style="dim")
    table.add_column("Result")

    with ssh:
        for label, cmd in checks:
            result = ssh.exec(cmd, stream=False)
            val = result.stdout.strip() or result.stderr.strip() or "—"
            table.add_row(label, val[:80])

    console.print(table)


@server_app.command("logs")
def server_logs(
    host: str = typer.Option(..., "--host"),
    username: str = typer.Option("root", "--user"),
    password: Optional[str] = typer.Option(None, "--password", hide_input=True),
    key_path: Optional[str] = typer.Option(None, "--key"),
    app_name: str = typer.Option("", "--app", help="PM2 app name"),
    lines: int = typer.Option(50, "--lines", "-n"),
):
    """Tail application logs from remote server."""
    ssh = _make_ssh(host, username, password, key_path, 22)
    with ssh:
        if app_name:
            cmd = f"pm2 logs {app_name} --lines {lines} --nostream 2>/dev/null"
        else:
            cmd = f"journalctl -n {lines} --no-pager 2>/dev/null"
        result = ssh.exec(cmd, stream=True)


# ------------------------------------------------------------------ #
#  profile subcommands                                                  #
# ------------------------------------------------------------------ #

@profile_app.command("save")
def profile_save(name: str = typer.Argument(..., help="Profile name")):
    """Save current deployment configuration as a named profile."""
    store = CredentialStore()
    host = Prompt.ask("  Host")
    username = Prompt.ask("  Username", default="root")
    domain = Prompt.ask("  Domain")
    project_type = Prompt.ask("  Stack", default="node")
    repo = Prompt.ask("  Repo URL (optional)", default="")
    store.save_profile(name, {
        "host": host, "username": username,
        "domain": domain, "project_type": project_type,
        "repo_url": repo,
    })
    console.print(f"[green]✓ Profile '{name}' saved.[/green]")


@profile_app.command("list")
def profile_list():
    """List all saved profiles."""
    store = CredentialStore()
    profiles = store.list_profiles()
    if not profiles:
        console.print("[yellow]No profiles saved yet.[/yellow]")
        return
    table = Table(title="Saved Profiles", box=box.SIMPLE)
    table.add_column("Name", style="cyan")
    for p in profiles:
        data = store.get_profile(p) or {}
        table.add_row(p)
    console.print(table)


@profile_app.command("use")
def profile_use(name: str = typer.Argument(...)):
    """Deploy using a saved profile."""
    store = CredentialStore()
    data = store.get_profile(name)
    if not data:
        console.print(f"[red]Profile '{name}' not found.[/red]")
        raise typer.Exit(1)

    import getpass
    password = getpass.getpass(f"  SSH password for {data.get('username', 'root')}@{data['host']}: ")
    cfg = DeploymentConfig(
        host=data["host"],
        username=data.get("username", "root"),
        password=password,
        domain=data["domain"],
        project_type=data.get("project_type", "node"),
        repo_url=data.get("repo_url") or None,
    )
    ssh = _make_ssh(cfg.host, cfg.username, cfg.password, None, 22)
    with ssh:
        engine = DeploymentEngine(ssh, cfg)
        engine.deploy()


# ------------------------------------------------------------------ #
#  Entry point                                                          #
# ------------------------------------------------------------------ #

if __name__ == "__main__":
    app()
