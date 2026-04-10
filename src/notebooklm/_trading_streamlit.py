"""Utilities used by Streamlit-based trading workflows."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


class TradingAgentCommandError(RuntimeError):
    """Raised when TradingAgents command execution fails."""


class TradingAgentOutputError(RuntimeError):
    """Raised when TradingAgents command output is not valid JSON."""


def run_trading_agents_command(command: str, timeout: int = 180) -> dict[str, Any]:
    """Execute TradingAgents command and parse JSON output from stdout.

    The command should print a single JSON object to stdout.
    """
    result = subprocess.run(
        command,
        shell=True,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    if result.returncode != 0:
        stderr = result.stderr.strip() or "(no stderr)"
        raise TradingAgentCommandError(
            f"TradingAgents command failed with exit code {result.returncode}: {stderr}"
        )

    stdout = result.stdout.strip()
    if not stdout:
        raise TradingAgentOutputError("TradingAgents command returned empty stdout")

    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise TradingAgentOutputError(f"TradingAgents stdout is not valid JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise TradingAgentOutputError("TradingAgents output must be a JSON object")

    return payload


def push_markdown_to_notebook(markdown_path: Path, notebook_id: str, profile: str | None = None) -> str:
    """Push markdown report into NotebookLM as a source via CLI."""
    cmd = ["notebooklm"]
    if profile:
        cmd.extend(["-p", profile])
    cmd.extend(["source", "add", str(markdown_path), "-n", notebook_id])

    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip() or "unknown error"
        raise RuntimeError(f"notebooklm source add failed: {stderr}")
    return result.stdout.strip() or "uploaded"
