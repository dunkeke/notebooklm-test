"""Tests for Streamlit trading utility helpers."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from notebooklm._trading_streamlit import (
    TradingAgentCommandError,
    TradingAgentOutputError,
    push_markdown_to_notebook,
    run_trading_agents_command,
)


class TestRunTradingAgentsCommand:
    """Unit tests for subprocess command execution helper."""

    def test_parses_json_stdout(self):
        completed = subprocess.CompletedProcess(
            args=["fake"],
            returncode=0,
            stdout='{"symbol":"brent","decision":{"direction":"long"}}',
            stderr="",
        )
        with patch("notebooklm._trading_streamlit.subprocess.run", return_value=completed):
            payload = run_trading_agents_command("fake")

        assert payload["symbol"] == "brent"
        assert payload["decision"]["direction"] == "long"

    def test_passes_working_directory(self, tmp_path: Path):
        completed = subprocess.CompletedProcess(
            args=["fake"],
            returncode=0,
            stdout='{"symbol":"brent"}',
            stderr="",
        )
        with patch("notebooklm._trading_streamlit.subprocess.run", return_value=completed) as mock_run:
            run_trading_agents_command("fake", working_dir=tmp_path)

        assert mock_run.call_args.kwargs["cwd"] == str(tmp_path)

    def test_raises_command_error_on_nonzero_exit(self):
        completed = subprocess.CompletedProcess(
            args=["fake"],
            returncode=1,
            stdout="",
            stderr="boom",
        )
        with (
            patch("notebooklm._trading_streamlit.subprocess.run", return_value=completed),
            pytest.raises(TradingAgentCommandError),
        ):
            run_trading_agents_command("fake")

    def test_module_not_found_adds_actionable_hint(self):
        completed = subprocess.CompletedProcess(
            args=["fake"],
            returncode=1,
            stdout="",
            stderr="ModuleNotFoundError: No module named 'tradingagents'",
        )
        with (
            patch("notebooklm._trading_streamlit.subprocess.run", return_value=completed),
            pytest.raises(TradingAgentCommandError) as exc,
        ):
            run_trading_agents_command("fake", working_dir=Path("/tmp/ta"))

        message = str(exc.value)
        assert "Hint:" in message
        assert "TradingAgents" in message

    def test_raises_output_error_on_invalid_json(self):
        completed = subprocess.CompletedProcess(
            args=["fake"],
            returncode=0,
            stdout="not-json",
            stderr="",
        )
        with (
            patch("notebooklm._trading_streamlit.subprocess.run", return_value=completed),
            pytest.raises(TradingAgentOutputError),
        ):
            run_trading_agents_command("fake")


class TestPushMarkdownToNotebook:
    """Unit tests for NotebookLM source upload helper."""

    def test_invokes_notebooklm_cli(self, tmp_path: Path):
        report = tmp_path / "report.md"
        report.write_text("# report", encoding="utf-8")

        completed = subprocess.CompletedProcess(
            args=["notebooklm"],
            returncode=0,
            stdout="ok",
            stderr="",
        )

        with patch("notebooklm._trading_streamlit.subprocess.run", return_value=completed) as mock_run:
            output = push_markdown_to_notebook(report, notebook_id="nb123", profile="work")

        assert output == "ok"
        called_args = mock_run.call_args[0][0]
        assert called_args[:3] == ["notebooklm", "-p", "work"]
        assert called_args[-2:] == ["-n", "nb123"]
