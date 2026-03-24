"""
ssh_manager.py — Secure SSH connection handler
Supports password auth, SSH key auth, and agent forwarding.
"""

from __future__ import annotations
import time
import socket
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Tuple

import paramiko
from rich.console import Console

console = Console()


@dataclass
class SSHCredentials:
    host: str
    port: int = 22
    username: str = "root"
    password: Optional[str] = None
    key_path: Optional[str] = None
    passphrase: Optional[str] = None
    timeout: int = 30


@dataclass
class CommandResult:
    command: str
    stdout: str
    stderr: str
    exit_code: int
    duration: float = 0.0

    @property
    def success(self) -> bool:
        return self.exit_code == 0

    def __repr__(self):
        status = "✓" if self.success else "✗"
        return f"[{status}] exit={self.exit_code} | {self.command[:60]}"


class SSHManager:
    """
    Manages a persistent SSH connection to a remote server.
    Supports password + key authentication with retry logic.
    """

    def __init__(self, credentials: SSHCredentials, retries: int = 3):
        self.creds = credentials
        self.retries = retries
        self._client: Optional[paramiko.SSHClient] = None
        self._sftp: Optional[paramiko.SFTPClient] = None

    # ------------------------------------------------------------------ #
    #  Connection lifecycle                                                 #
    # ------------------------------------------------------------------ #

    def connect(self) -> bool:
        """Establish SSH connection with retry logic."""
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        connect_kwargs: dict = {
            "hostname": self.creds.host,
            "port": self.creds.port,
            "username": self.creds.username,
            "timeout": self.creds.timeout,
            "allow_agent": True,
            "look_for_keys": True,
        }

        # Auth strategy: key > password
        if self.creds.key_path:
            pkey = self._load_key(self.creds.key_path, self.creds.passphrase)
            if pkey:
                connect_kwargs["pkey"] = pkey
        elif self.creds.password:
            connect_kwargs["password"] = self.creds.password

        for attempt in range(1, self.retries + 1):
            try:
                console.print(
                    f"  [dim]Connecting to [cyan]{self.creds.username}@{self.creds.host}:{self.creds.port}[/cyan] "
                    f"(attempt {attempt}/{self.retries})[/dim]"
                )
                client.connect(**connect_kwargs)
                self._client = client
                console.print(f"  [green]✓ Connected[/green]")
                return True
            except paramiko.AuthenticationException:
                console.print(f"  [red]✗ Authentication failed[/red]")
                return False
            except (socket.timeout, paramiko.SSHException, OSError) as exc:
                console.print(f"  [yellow]⚠ Connection error: {exc}[/yellow]")
                if attempt < self.retries:
                    time.sleep(2 * attempt)
        return False

    def disconnect(self):
        if self._sftp:
            try:
                self._sftp.close()
            except Exception:
                pass
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
        self._client = None
        self._sftp = None

    def is_connected(self) -> bool:
        if not self._client:
            return False
        transport = self._client.get_transport()
        return transport is not None and transport.is_active()

    # ------------------------------------------------------------------ #
    #  Command execution                                                    #
    # ------------------------------------------------------------------ #

    def exec(
        self,
        command: str,
        sudo: bool = False,
        env: Optional[dict] = None,
        timeout: int = 300,
        stream: bool = True,
    ) -> CommandResult:
        """
        Execute a single command on the remote server.
        Returns a CommandResult with stdout, stderr, exit_code.
        """
        if not self.is_connected():
            raise RuntimeError("SSH connection is not active. Call connect() first.")

        full_cmd = command
        if sudo and not command.strip().startswith("sudo"):
            full_cmd = f"sudo {command}"

        # Inject env vars
        if env:
            env_str = " ".join(f'{k}="{v}"' for k, v in env.items())
            full_cmd = f"export {env_str} && {full_cmd}"

        start = time.time()
        stdout_data, stderr_data = "", ""

        try:
            stdin, stdout, stderr = self._client.exec_command(
                full_cmd, timeout=timeout, get_pty=sudo
            )
            # If sudo + pty, feed password if needed
            if sudo and self.creds.password:
                stdin.write(self.creds.password + "\n")
                stdin.flush()

            # Stream stdout in real time
            if stream:
                for line in stdout:
                    stripped = line.rstrip()
                    stdout_data += stripped + "\n"
                    console.print(f"    [dim]{stripped}[/dim]")
            else:
                stdout_data = stdout.read().decode("utf-8", errors="replace")

            stderr_data = stderr.read().decode("utf-8", errors="replace")
            exit_code = stdout.channel.recv_exit_status()

        except socket.timeout:
            exit_code = -1
            stderr_data = "Command timed out"

        duration = time.time() - start
        return CommandResult(
            command=command,
            stdout=stdout_data.strip(),
            stderr=stderr_data.strip(),
            exit_code=exit_code,
            duration=duration,
        )

    def exec_script(self, script_lines: list[str], **kwargs) -> list[CommandResult]:
        """Execute a list of commands sequentially; stop on first failure."""
        results = []
        for cmd in script_lines:
            if not cmd.strip() or cmd.strip().startswith("#"):
                continue
            result = self.exec(cmd, **kwargs)
            results.append(result)
            if not result.success:
                break
        return results

    def upload_file(self, local_path: str, remote_path: str):
        """Upload a local file to the remote server via SFTP."""
        sftp = self._get_sftp()
        sftp.put(local_path, remote_path)
        console.print(f"  [green]↑ Uploaded[/green] {local_path} → {remote_path}")

    def write_remote_file(self, remote_path: str, content: str):
        """Write string content directly to a remote file via SFTP."""
        sftp = self._get_sftp()
        with sftp.open(remote_path, "w") as f:
            f.write(content)
        console.print(f"  [green]✎ Written[/green] → {remote_path}")

    def read_remote_file(self, remote_path: str) -> str:
        sftp = self._get_sftp()
        with sftp.open(remote_path, "r") as f:
            return f.read().decode("utf-8", errors="replace")

    # ------------------------------------------------------------------ #
    #  Helpers                                                              #
    # ------------------------------------------------------------------ #

    def _get_sftp(self) -> paramiko.SFTPClient:
        if not self._sftp:
            self._sftp = self._client.open_sftp()
        return self._sftp

    @staticmethod
    def _load_key(
        key_path: str, passphrase: Optional[str] = None
    ) -> Optional[paramiko.PKey]:
        path = Path(key_path).expanduser()
        if not path.exists():
            console.print(f"  [red]Key file not found: {path}[/red]")
            return None
        for key_class in (
            paramiko.RSAKey,
            paramiko.ECDSAKey,
            paramiko.Ed25519Key,
            paramiko.DSSKey,
        ):
            try:
                return key_class.from_private_key_file(str(path), password=passphrase)
            except paramiko.SSHException:
                continue
            except Exception:
                continue
        console.print(f"  [red]Failed to load key: {path}[/red]")
        return None

    # ------------------------------------------------------------------ #
    #  Context manager support                                              #
    # ------------------------------------------------------------------ #

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *_):
        self.disconnect()
