"""Helpers for TradingAgents + NotebookLM style market reports."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ENERGY_INSTRUMENT_ALIASES: dict[str, str] = {
    "brent": "Brent Crude",
    "wti": "WTI Crude",
    "hh": "Henry Hub Natural Gas",
    "ttf": "TTF Natural Gas",
    "jkm": "JKM LNG",
    "mb": "MB (user-defined benchmark)",
    "cp": "CP (user-defined benchmark)",
    "fei": "FEI (user-defined benchmark)",
}


@dataclass(slots=True)
class TradingReportInput:
    """Normalized inputs used to render a market report prompt."""

    instrument: str
    market: str
    horizon: str
    signal: str
    confidence: float
    thesis: str
    entry: str
    stop_loss: str
    take_profit: str
    risk_notes: str
    factors: list[str] = field(default_factory=list)
    counters: list[str] = field(default_factory=list)
    event_watchlist: list[str] = field(default_factory=list)

    @property
    def instrument_display(self) -> str:
        return ENERGY_INSTRUMENT_ALIASES.get(self.instrument.lower(), self.instrument)


def parse_tradingagents_json(path: Path) -> TradingReportInput:
    """Parse a TradingAgents JSON output into TradingReportInput.

    Expected shape is intentionally permissive so teams can map their own
    TradingAgents output schema.
    """
    payload = json.loads(path.read_text(encoding="utf-8"))

    def _get(keys: list[str], default: str = "") -> Any:
        for key in keys:
            if key in payload and payload[key] is not None:
                return payload[key]
        return default

    signal_block = _get(["decision", "signal", "trade_signal"], {})
    if isinstance(signal_block, str):
        signal_value = signal_block
        confidence_value = float(_get(["confidence", "score"], 0.0) or 0.0)
    else:
        signal_value = signal_block.get("direction") or signal_block.get("signal") or "neutral"
        confidence_value = float(
            signal_block.get("confidence")
            or payload.get("confidence")
            or payload.get("score")
            or 0.0
        )

    risk_block = _get(["risk", "risk_plan", "risk_management"], {})
    if isinstance(risk_block, str):
        risk_notes = risk_block
    else:
        risk_notes = risk_block.get("notes") or risk_block.get("summary") or ""

    execution_block = _get(["execution", "trade_plan", "levels"], {})
    if isinstance(execution_block, str):
        entry = execution_block
        stop_loss = ""
        take_profit = ""
    else:
        entry = str(execution_block.get("entry") or execution_block.get("entry_zone") or "")
        stop_loss = str(execution_block.get("stop") or execution_block.get("stop_loss") or "")
        take_profit = str(
            execution_block.get("target")
            or execution_block.get("take_profit")
            or execution_block.get("targets")
            or ""
        )

    factors = _ensure_string_list(
        _get(["factors", "drivers", "bull_case", "supporting_evidence"], [])
    )
    counters = _ensure_string_list(
        _get(["counterpoints", "bear_case", "risks", "opposing_evidence"], [])
    )
    watchlist = _ensure_string_list(_get(["event_watchlist", "events", "calendar"], []))

    return TradingReportInput(
        instrument=str(_get(["instrument", "symbol", "asset"], "unknown")),
        market=str(_get(["market", "exchange", "venue"], "unknown")),
        horizon=str(_get(["horizon", "timeframe", "holding_period"], "swing")),
        signal=str(signal_value),
        confidence=max(0.0, min(1.0, confidence_value)),
        thesis=str(_get(["thesis", "summary", "rationale"], "")),
        entry=entry,
        stop_loss=stop_loss,
        take_profit=take_profit,
        risk_notes=risk_notes,
        factors=factors,
        counters=counters,
        event_watchlist=watchlist,
    )


def build_notebooklm_market_report_prompt(report: TradingReportInput) -> str:
    """Render a NotebookLM-style report prompt from normalized data."""
    sections: list[str] = [
        "# Energy Market Analysis Brief",
        "",
        "## Instrument Context",
        f"- Instrument: {report.instrument_display}",
        f"- Raw Symbol: {report.instrument}",
        f"- Market: {report.market}",
        f"- Horizon: {report.horizon}",
        "",
        "## Signal Summary",
        f"- Direction: {report.signal}",
        f"- Confidence: {report.confidence:.2f}",
        f"- Thesis: {report.thesis or 'N/A'}",
        "",
        "## Trade Plan",
        f"- Entry: {report.entry or 'N/A'}",
        f"- Stop Loss: {report.stop_loss or 'N/A'}",
        f"- Take Profit: {report.take_profit or 'N/A'}",
        f"- Risk Notes: {report.risk_notes or 'N/A'}",
        "",
        "## Supporting Factors",
    ]
    sections.extend(_as_bullets(report.factors, fallback="No supporting factors provided"))

    sections.extend(["", "## Counterpoints", *_as_bullets(report.counters, "No counterpoints provided")])
    sections.extend(
        ["", "## Event Watchlist", *_as_bullets(report.event_watchlist, "No events provided")]
    )
    sections.extend(
        [
            "",
            "## NotebookLM Output Instructions",
            "Produce a concise institutional-style market note with:",
            "1) Executive summary (3-5 bullets)",
            "2) Evidence chain and data caveats",
            "3) Actionable trade plan with invalidation conditions",
            "4) Risk scenarios (base/bull/bear)",
            "5) Explicit assumptions that can be tested tomorrow",
        ]
    )
    return "\n".join(sections)


def _as_bullets(items: list[str], fallback: str) -> list[str]:
    if not items:
        return [f"- {fallback}"]
    return [f"- {item}" for item in items]


def _ensure_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value]
    return []
