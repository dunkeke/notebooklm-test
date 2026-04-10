"""Agent integration commands."""

from __future__ import annotations

from pathlib import Path

import click

from notebooklm._trading_report import (
    TradingReportInput,
    build_notebooklm_market_report_prompt,
    parse_tradingagents_json,
)

from .agent_templates import get_agent_source_content
from .helpers import console, json_output_response


@click.group()
def agent():
    """Show bundled instructions for supported agent environments."""
    pass


@agent.command("show")
@click.argument("target", type=click.Choice(["codex", "claude"], case_sensitive=False))
def show_agent(target: str):
    """Display instructions for Codex or Claude Code."""
    content = get_agent_source_content(target)
    if content is None:
        console.print(f"[red]Error:[/red] {target} instructions not found in package data.")
        raise SystemExit(1)

    console.print(content)


@agent.command("trading-report")
@click.option(
    "--tradingagents-json",
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
    help="Path to TradingAgents output JSON.",
)
@click.option("--instrument", default="brent", show_default=True, help="Instrument/symbol name.")
@click.option("--market", default="ICE", show_default=True, help="Exchange/market name.")
@click.option("--horizon", default="swing", show_default=True, help="Holding horizon.")
@click.option(
    "--signal",
    type=click.Choice(["long", "short", "neutral"], case_sensitive=False),
    default="neutral",
    show_default=True,
    help="Trade direction.",
)
@click.option("--confidence", type=float, default=0.5, show_default=True, help="0~1 confidence.")
@click.option("--thesis", default="", help="Primary thesis summary.")
@click.option("--entry", default="", help="Entry level or condition.")
@click.option("--stop-loss", default="", help="Stop loss level.")
@click.option("--take-profit", default="", help="Take profit level.")
@click.option("--risk-notes", default="", help="Risk management notes.")
@click.option("--factor", "factors", multiple=True, help="Supporting factor (repeatable).")
@click.option("--counter", "counters", multiple=True, help="Counterpoint (repeatable).")
@click.option("--event", "events", multiple=True, help="Event watchlist item (repeatable).")
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=Path, dir_okay=False),
    help="Write rendered prompt markdown to file.",
)
@click.option("--json", "json_output", is_flag=True, help="Output normalized payload as JSON.")
def trading_report(
    tradingagents_json: Path | None,
    instrument: str,
    market: str,
    horizon: str,
    signal: str,
    confidence: float,
    thesis: str,
    entry: str,
    stop_loss: str,
    take_profit: str,
    risk_notes: str,
    factors: tuple[str, ...],
    counters: tuple[str, ...],
    events: tuple[str, ...],
    output: Path | None,
    json_output: bool,
):
    """Render a NotebookLM-style market report prompt for TradingAgents workflows."""
    if not 0.0 <= confidence <= 1.0:
        raise click.ClickException("--confidence must be between 0 and 1")

    report_input = (
        parse_tradingagents_json(tradingagents_json)
        if tradingagents_json
        else TradingReportInput(
            instrument=instrument,
            market=market,
            horizon=horizon,
            signal=signal,
            confidence=confidence,
            thesis=thesis,
            entry=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_notes=risk_notes,
            factors=list(factors),
            counters=list(counters),
            event_watchlist=list(events),
        )
    )

    rendered = build_notebooklm_market_report_prompt(report_input)

    if output:
        output.write_text(rendered, encoding="utf-8")
        console.print(f"[green]Saved[/green] trading report prompt: {output}")

    if json_output:
        payload = {
            "instrument": report_input.instrument,
            "market": report_input.market,
            "horizon": report_input.horizon,
            "signal": report_input.signal,
            "confidence": report_input.confidence,
            "thesis": report_input.thesis,
            "entry": report_input.entry,
            "stop_loss": report_input.stop_loss,
            "take_profit": report_input.take_profit,
            "risk_notes": report_input.risk_notes,
            "factors": report_input.factors,
            "counters": report_input.counters,
            "event_watchlist": report_input.event_watchlist,
            "report_prompt": rendered,
        }
        json_output_response(payload)
        return

    console.print(rendered)
