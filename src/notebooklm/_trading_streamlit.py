"""Utilities used by Streamlit-based trading workflows."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import httpx


class TradingAgentCommandError(RuntimeError):
    """Raised when TradingAgents command execution fails."""


class TradingAgentOutputError(RuntimeError):
    """Raised when TradingAgents command output is not valid JSON."""


class DeepSeekAPIError(RuntimeError):
    """Raised when DeepSeek API calls fail."""


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


def generate_deepseek_discussion(
    report_prompt: str,
    api_key: str,
    model: str = "deepseek-chat",
    timeout: float = 60.0,
    base_url: str = "https://api.deepseek.com/v1",
) -> str:
    """Generate market discussion using DeepSeek chat-completions API."""
    if not api_key.strip():
        raise DeepSeekAPIError("DeepSeek API key is required")

    url = f"{base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": model,
        "temperature": 0.2,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an institutional energy derivatives panel. "
                    "Debate bull/bear views, challenge assumptions, and conclude with a risk-aware plan."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Based on the trading report draft below, produce a realistic panel discussion "
                    "between Bull Analyst, Bear Analyst, and Risk Manager. End with a final desk decision.\n\n"
                    f"{report_prompt}"
                ),
            },
        ],
    }
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json",
    }

    try:
        response = httpx.post(url, headers=headers, json=payload, timeout=timeout)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise DeepSeekAPIError(f"DeepSeek API request failed: {exc}") from exc

    data = response.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise DeepSeekAPIError("DeepSeek API response format is invalid") from exc


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
