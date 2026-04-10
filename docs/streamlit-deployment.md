# Streamlit Deployment for Trading Report UI

**Status:** Active  
**Last Updated:** 2026-04-10

This guide shows how to deploy a front-end for the TradingAgents + NotebookLM workflow.

## 1) Install dependencies

```bash
uv sync --extra frontend
```

Or with pip:

```bash
pip install streamlit
```

## 2) Run the app

```bash
uv run streamlit run docs/examples/trading_streamlit_app.py
```

App capabilities:
- Manual signal input
- Upload TradingAgents JSON
- Run TradingAgents command directly (expects JSON on stdout)
- Generate NotebookLM-style markdown + JSON
- Push markdown source directly to NotebookLM notebook

## 3) Direct TradingAgents execution in UI

In the app choose **运行 TradingAgents 命令** and provide a command template, e.g.:

```bash
python -m tradingagents.run --symbol "{instrument}" --json
```

The app will replace `{instrument}` with the selected symbol and parse stdout as JSON.

## 4) Push report directly to NotebookLM

In tab **喂给 NotebookLM** fill:
- Notebook ID
- Optional profile name

The app internally calls:

```bash
notebooklm [-p <profile>] source add /tmp/notebooklm_trading_report.md -n <notebook_id>
```

## 5) Deploy remotely

You can deploy this Streamlit app on Docker/Cloud Run/VM, then expose port `8501` behind auth and TLS.

Security notes:
- Restrict who can access command execution mode.
- Use a low-privilege runtime user.
- Prefer allowlisted TradingAgents commands in production.
