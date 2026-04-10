# Streamlit Deployment for Trading Report UI

**Status:** Active  
**Last Updated:** 2026-04-10

This guide shows how to deploy a lightweight front-end for the TradingAgents + NotebookLM flow.

## 1) Install dependencies

```bash
uv sync --extra frontend
```

Or with pip:

```bash
pip install streamlit
```

## 2) Run the app locally

```bash
uv run streamlit run docs/examples/trading_streamlit_app.py
```

The app allows two modes:
- Manual form input for market signal data
- Upload a TradingAgents JSON output file

Both modes generate a NotebookLM-style markdown report draft.

## 3) Optional: deploy remotely

You can deploy the Streamlit app on any VM/container platform:

- **Docker**: run Streamlit on port `8501`
- **Cloud Run / ECS / VM**: expose `8501` and restrict access with auth/proxy
- **Internal server**: reverse-proxy with Nginx and TLS

## 4) Integrate with NotebookLM CLI

After downloading markdown from the UI:

```bash
notebooklm source add ./brent_notebooklm_report.md
notebooklm ask "Summarize actionable trading plan and risk triggers"
notebooklm generate report --format briefing-doc --wait
```

This creates a simple analyst workflow where TradingAgents does signal generation and NotebookLM handles narrative/reporting.
