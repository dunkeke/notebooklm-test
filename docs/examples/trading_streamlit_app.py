"""Streamlit front-end for TradingAgents -> NotebookLM market report generation.

Run:
    uv run streamlit run docs/examples/trading_streamlit_app.py
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
from notebooklm._trading_streamlit import (
    TradingAgentCommandError,
    TradingAgentOutputError,
    push_markdown_to_notebook,
    run_trading_agents_command,
)

st.set_page_config(page_title="NotebookLM Trading Studio", page_icon="📈", layout="wide")

st.markdown(
    """
<style>
.block-container {padding-top: 1.5rem; max-width: 1200px;}
.fancy-card {
    background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 50%, #312e81 100%);
    border-radius: 16px;
    padding: 18px;
    color: #f8fafc;
    box-shadow: 0 6px 24px rgba(15, 23, 42, 0.35);
    margin-bottom: 16px;
}
.tag {
    display:inline-block; padding:4px 10px; border-radius:999px; margin-right:8px;
    background: rgba(255,255,255,0.14); font-size: 12px;
}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="fancy-card">
  <h2 style="margin:0;">📈 NotebookLM Trading Studio</h2>
  <p style="margin:8px 0 0 0;">运行 TradingAgents → 自动生成 NotebookLM 风格报告 → 一键喂给 NotebookLM。</p>
  <div style="margin-top:10px;">
    <span class="tag">Energy Futures</span>
    <span class="tag">Brent / WTI / HH / TTF / JKM</span>
    <span class="tag">Streamlit Deploy Ready</span>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

if "report_prompt" not in st.session_state:
    st.session_state.report_prompt = ""
if "payload" not in st.session_state:
    st.session_state.payload = None


with st.sidebar:
    st.subheader("工作流")
    input_mode = st.radio(
        "信号来源",
        ["手动输入", "上传 JSON", "运行 TradingAgents 命令"],
        index=0,
    )
    st.caption("建议先生成报告，再在下方点击上传到 NotebookLM。")


def _manual_form() -> TradingReportInput:
    col1, col2 = st.columns(2)
    with col1:
        instrument = st.text_input("标的", value="brent")
        market = st.text_input("交易所/市场", value="ICE")
        horizon = st.selectbox("周期", ["intraday", "swing", "position"], index=1)
        signal = st.selectbox("方向", ["long", "short", "neutral"], index=2)
        confidence = st.slider("置信度", 0.0, 1.0, 0.5, 0.01)
    with col2:
        thesis = st.text_area("核心观点", value="")
        entry = st.text_input("入场", value="")
        stop_loss = st.text_input("止损", value="")
        take_profit = st.text_input("止盈", value="")
        risk_notes = st.text_area("风险说明", value="")

    factors = st.text_area("支持因素（每行一条）", value="")
    counters = st.text_area("反证因素（每行一条）", value="")
    events = st.text_area("事件观察（每行一条）", value="")

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
        factors=[line.strip() for line in factors.splitlines() if line.strip()],
        counters=[line.strip() for line in counters.splitlines() if line.strip()],
        event_watchlist=[line.strip() for line in events.splitlines() if line.strip()],
    )


def _upload_json() -> TradingReportInput | None:
    uploaded = st.file_uploader("上传 TradingAgents JSON", type=["json"])
    if not uploaded:
        return None
    tmp = Path("/tmp/tradingagents-upload.json")
    tmp.write_bytes(uploaded.getvalue())
    try:
        return parse_tradingagents_json(tmp)
    except json.JSONDecodeError as exc:
        st.error(f"JSON 解析失败：{exc}")
        return None


def _run_command() -> TradingReportInput | None:
    command = st.text_area(
        "TradingAgents 命令（需输出 JSON 到 stdout）",
        value='python -m tradingagents.run --symbol "{instrument}" --json',
        help="会将 {instrument} 替换为下方输入值。",
    )
    instrument = st.text_input("运行标的", value="brent")
    timeout = st.number_input("超时（秒）", min_value=30, max_value=600, value=180, step=30)

    if st.button("执行 TradingAgents", use_container_width=True):
        rendered_cmd = command.format(instrument=instrument)
        with st.status("正在执行 TradingAgents 命令...", expanded=True) as status:
            st.code(rendered_cmd, language="bash")
            try:
                payload = run_trading_agents_command(rendered_cmd, timeout=int(timeout))
                temp_path = Path("/tmp/tradingagents-runtime.json")
                temp_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
                report_input = parse_tradingagents_json(temp_path)
                status.update(label="TradingAgents 执行成功", state="complete")
                st.success("已获取信号并转换为报告输入。")
                return report_input
            except (TradingAgentCommandError, TradingAgentOutputError, RuntimeError) as exc:
                status.update(label="执行失败", state="error")
                st.error(str(exc))
            except KeyError as exc:
                status.update(label="执行失败", state="error")
                st.error(f"命令模板变量错误: {exc}")
    return None


if input_mode == "手动输入":
    current_input = _manual_form()
elif input_mode == "上传 JSON":
    current_input = _upload_json()
else:
    current_input = _run_command()

if st.button("生成 NotebookLM 报告", type="primary", use_container_width=True):
    if current_input is None:
        st.warning("当前模式还没有可用输入，请先填写或执行命令。")
    else:
        report_prompt = build_notebooklm_market_report_prompt(current_input)
        payload = {
            "instrument": current_input.instrument,
            "market": current_input.market,
            "horizon": current_input.horizon,
            "signal": current_input.signal,
            "confidence": current_input.confidence,
            "thesis": current_input.thesis,
            "entry": current_input.entry,
            "stop_loss": current_input.stop_loss,
            "take_profit": current_input.take_profit,
            "risk_notes": current_input.risk_notes,
            "factors": current_input.factors,
            "counters": current_input.counters,
            "event_watchlist": current_input.event_watchlist,
            "report_prompt": report_prompt,
        }
        st.session_state.report_prompt = report_prompt
        st.session_state.payload = payload
        st.success("报告已生成。")

if st.session_state.report_prompt:
    preview_tab, json_tab, notebook_tab = st.tabs(["Markdown 预览", "JSON 预览", "喂给 NotebookLM"])

    with preview_tab:
        st.code(st.session_state.report_prompt, language="markdown")
        st.download_button(
            "下载 Markdown",
            data=st.session_state.report_prompt.encode("utf-8"),
            file_name="notebooklm_trading_report.md",
            mime="text/markdown",
            use_container_width=True,
        )

    with json_tab:
        payload_json = json.dumps(st.session_state.payload, ensure_ascii=False, indent=2)
        st.code(payload_json, language="json")
        st.download_button(
            "下载 JSON",
            data=payload_json.encode("utf-8"),
            file_name="notebooklm_trading_report.json",
            mime="application/json",
            use_container_width=True,
        )

    with notebook_tab:
        st.write("将当前 markdown 作为 source 自动上传到指定 NotebookLM notebook。")
        notebook_id = st.text_input("Notebook ID")
        profile = st.text_input("Profile（可选）", value="")

        if st.button("上传到 NotebookLM", use_container_width=True):
            if not notebook_id.strip():
                st.warning("请填写 Notebook ID")
            else:
                report_path = Path("/tmp/notebooklm_trading_report.md")
                report_path.write_text(st.session_state.report_prompt, encoding="utf-8")
                try:
                    output = push_markdown_to_notebook(
                        report_path,
                        notebook_id=notebook_id.strip(),
                        profile=profile.strip() or None,
                    )
                    st.success("已上传到 NotebookLM source。")
                    st.text(output)
                except RuntimeError as exc:
                    st.error(str(exc))

st.divider()
st.info(
    "生产部署建议：将此应用放到云主机/容器中，使用反向代理与鉴权保护。"
)
