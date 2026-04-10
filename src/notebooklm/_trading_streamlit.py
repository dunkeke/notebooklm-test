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


def run_trading_agents_command(
    command: str,
    timeout: int = 180,
    working_dir: Path | None = None,
) -> dict[str, Any]:
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
        cwd=str(working_dir) if working_dir else None,
    )

    if result.returncode != 0:
        stderr = result.stderr.strip() or "(no stderr)"
        hint = _build_install_hint(stderr, working_dir)
        raise TradingAgentCommandError(
            f"TradingAgents command failed with exit code {result.returncode}: {stderr}{hint}"
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


def _build_install_hint(stderr: str, working_dir: Path | None) -> str:
    lowered = stderr.lower()
    missing_module = "no module named 'tradingagents'" in lowered
    missing_cli = "no module named 'cli'" in lowered
    if not (missing_module or missing_cli):
        return ""

    cwd_msg = f" 当前工作目录: {working_dir}." if working_dir else ""
    return (
        "\nHint: 看起来 TradingAgents 没有安装或工作目录不正确。"
        " 请先 `git clone https://github.com/TauricResearch/TradingAgents.git`，"
        " 在该目录执行 `pip install -r requirements.txt`，"
        " 并在本应用中把 TradingAgents 工作目录设为该仓库路径。"
        f"{cwd_msg}"
    )
