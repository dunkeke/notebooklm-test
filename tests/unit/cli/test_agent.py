"""Tests for agent CLI commands."""

import json
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from notebooklm.notebooklm_cli import cli

from .conftest import get_cli_module

agent_module = get_cli_module("agent")
agent_templates_module = get_cli_module("agent_templates")


@pytest.fixture
def runner():
    return CliRunner()


class TestAgentShow:
    """Tests for agent show command."""

    def test_agent_show_codex_displays_content(self, runner):
        """Test that agent show codex displays the bundled instructions."""
        with patch.object(
            agent_module, "get_agent_source_content", return_value="# Repository Guidelines"
        ):
            result = runner.invoke(cli, ["agent", "show", "codex"])

        assert result.exit_code == 0
        assert "Repository Guidelines" in result.output

    def test_agent_show_claude_displays_content(self, runner):
        """Test that agent show claude displays the bundled instructions."""
        with patch.object(agent_module, "get_agent_source_content", return_value="# Claude Skill"):
            result = runner.invoke(cli, ["agent", "show", "claude"])

        assert result.exit_code == 0
        assert "Claude Skill" in result.output

    def test_agent_show_missing_content_returns_error(self, runner):
        """Test error when bundled agent instructions are missing."""
        with patch.object(agent_module, "get_agent_source_content", return_value=None):
            result = runner.invoke(cli, ["agent", "show", "codex"])

        assert result.exit_code == 1
        assert "not found" in result.output.lower()


class TestAgentTemplates:
    """Tests for bundled agent template loading."""

    def test_codex_template_falls_back_to_package_data(self, tmp_path):
        """Test that codex content falls back to packaged data outside repo root."""
        with (
            patch.object(agent_templates_module, "REPO_ROOT_AGENTS", tmp_path / "AGENTS.md"),
            patch.object(
                agent_templates_module,
                "_read_package_data",
                return_value="# Repository Guidelines",
            ),
        ):
            content = agent_templates_module.get_agent_source_content("codex")

        assert content is not None
        assert "Repository Guidelines" in content

    def test_claude_template_reads_package_data(self):
        """Test that claude content reads from packaged skill data."""
        content = agent_templates_module.get_agent_source_content("claude")

        assert content is not None
        assert "NotebookLM Automation" in content


class TestTradingReport:
    """Tests for TradingAgents market report rendering command."""

    def test_trading_report_plain_text_output(self, runner):
        """Command should render NotebookLM style sections in text mode."""
        result = runner.invoke(
            cli,
            [
                "agent",
                "trading-report",
                "--instrument",
                "wti",
                "--signal",
                "long",
                "--confidence",
                "0.72",
                "--factor",
                "US crude drawdown",
                "--counter",
                "OPEC surprise supply",
            ],
        )

        assert result.exit_code == 0
        assert "Energy Market Analysis Brief" in result.output
        assert "WTI Crude" in result.output
        assert "US crude drawdown" in result.output

    def test_trading_report_json_output(self, runner):
        """JSON mode should emit machine-readable normalized output."""
        result = runner.invoke(
            cli,
            [
                "agent",
                "trading-report",
                "--instrument",
                "ttf",
                "--signal",
                "short",
                "--json",
            ],
        )

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["instrument"] == "ttf"
        assert payload["signal"] == "short"
        assert "report_prompt" in payload

    def test_trading_report_from_json_file(self, runner, tmp_path):
        """TradingAgents JSON input should map into the final prompt."""
        signal_path = tmp_path / "tradingagents.json"
        signal_path.write_text(
            json.dumps(
                {
                    "symbol": "jkm",
                    "market": "ICE",
                    "timeframe": "weekly",
                    "decision": {"direction": "long", "confidence": 0.81},
                    "thesis": "Asian spot demand is recovering.",
                    "trade_plan": {
                        "entry": "15.5-16.2",
                        "stop_loss": "14.7",
                        "take_profit": "17.9",
                    },
                    "factors": ["Improved LNG import pull"],
                    "counterpoints": ["Mild weather outlook"],
                    "event_watchlist": ["EU storage trajectory"],
                }
            ),
            encoding="utf-8",
        )

        result = runner.invoke(
            cli, ["agent", "trading-report", "--tradingagents-json", str(signal_path)]
        )

        assert result.exit_code == 0
        assert "JKM LNG" in result.output
        assert "Asian spot demand is recovering." in result.output

    def test_trading_report_confidence_range_validation(self, runner):
        """Confidence values above 1.0 should fail validation."""
        result = runner.invoke(
            cli,
            ["agent", "trading-report", "--confidence", "1.2"],
        )

        assert result.exit_code != 0
        assert "between 0 and 1" in result.output
