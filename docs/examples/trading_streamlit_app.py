"""Streamlit front-end for TradingAgents -> NotebookLM market report generation.

Run:
    uv run streamlit run docs/examples/trading_streamlit_app.py

If you don't use uv:
    pip install streamlit
    streamlit run docs/examples/trading_streamlit_app.py
"""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from notebooklm._trading_report import (
    TradingReportInput,
    build_notebooklm_market_report_prompt,
    parse_tradingagents_json,
)

st.set_page_config(page_title="NotebookLM Trading Report", page_icon="📈", layout="wide")

st.title("📈 NotebookLM 风格交易分析报告")
st.caption("将 TradingAgents 信号转成可直接喂给 NotebookLM 的结构化报告草稿")

with st.sidebar:
    st.subheader("输入方式")
    mode = st.radio(
        "请选择数据来源",
        ["手动输入", "上传 TradingAgents JSON"],
        index=0,
    )


def _manual_form() -> TradingReportInput:
    col1, col2 = st.columns(2)
    with col1:
        instrument = st.text_input("标的", value="brent")
        market = st.text_input("市场/交易所", value="ICE")
        horizon = st.selectbox("周期", ["intraday", "swing", "position"], index=1)
        signal = st.selectbox("方向", ["long", "short", "neutral"], index=2)
        confidence = st.slider("置信度", min_value=0.0, max_value=1.0, value=0.5, step=0.01)
    with col2:
        thesis = st.text_area("核心观点", value="")
        entry = st.text_input("入场", value="")
        stop_loss = st.text_input("止损", value="")
        take_profit = st.text_input("止盈", value="")
        risk_notes = st.text_area("风险备注", value="")

    factors_raw = st.text_area("支持因素（每行一条）", value="")
    counters_raw = st.text_area("反证因素（每行一条）", value="")
    events_raw = st.text_area("事件观察（每行一条）", value="")

    return TradingReportInput(
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
        factors=[line.strip() for line in factors_raw.splitlines() if line.strip()],
        counters=[line.strip() for line in counters_raw.splitlines() if line.strip()],
        event_watchlist=[line.strip() for line in events_raw.splitlines() if line.strip()],
    )


def _upload_json() -> TradingReportInput | None:
    uploaded = st.file_uploader("上传 TradingAgents 输出 JSON", type=["json"])
    if not uploaded:
        return None

    temp_path = Path(st.session_state.get("_ta_json_path", "/tmp/tradingagents-upload.json"))
    temp_path.write_bytes(uploaded.getvalue())

    try:
        return parse_tradingagents_json(temp_path)
    except json.JSONDecodeError as exc:
        st.error(f"JSON 解析失败: {exc}")
        return None


report_input = _manual_form() if mode == "手动输入" else _upload_json()

if st.button("生成 NotebookLM 报告草稿", type="primary"):
    if report_input is None:
        st.warning("请先上传有效的 TradingAgents JSON 文件。")
    else:
        report_prompt = build_notebooklm_market_report_prompt(report_input)
        st.success("已生成，可直接复制到 NotebookLM 或通过 CLI 导入 source。")
        st.subheader("Markdown 预览")
        st.code(report_prompt, language="markdown")

        st.download_button(
            "下载 Markdown",
            data=report_prompt.encode("utf-8"),
            file_name=f"{report_input.instrument}_notebooklm_report.md",
            mime="text/markdown",
        )

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
            "report_prompt": report_prompt,
        }

        st.download_button(
            "下载 JSON",
            data=json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
            file_name=f"{report_input.instrument}_notebooklm_report.json",
            mime="application/json",
        )

st.divider()
st.markdown(
    """
### 部署提示
- 本地：`uv run streamlit run docs/examples/trading_streamlit_app.py`
- 服务器：使用 Docker / Cloud Run 部署 Streamlit，对外暴露 8501 端口
- 与 NotebookLM CLI 结合：先生成 markdown，再 `notebooklm source add <file>`
"""
)
