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
- Call DeepSeek API to create multi-role market discussion output

## 3) Direct TradingAgents execution in UI

In the app choose **运行 TradingAgents 命令** and provide a command template, e.g.:

```bash
python -c "import json; from tradingagents.graph.trading_graph import TradingAgentsGraph; from tradingagents.default_config import DEFAULT_CONFIG; ta=TradingAgentsGraph(debug=False, config=DEFAULT_CONFIG.copy()); _, d = ta.propagate("{instrument}", "{analysis_date}"); print(json.dumps(d, ensure_ascii=False))"
```

The app will replace `{instrument}` and `{analysis_date}` then parse stdout as JSON.

If you see `ModuleNotFoundError: No module named 'tradingagents'`, install TradingAgents dependencies and set the app's **TradingAgents 工作目录** to your cloned TradingAgents repository path.

If Streamlit shows a redacted `TypeError` at TradingAgents execution, update the repository to this latest version. This build includes backward-compatible invocation logic for older helper signatures.

## 4) Push report directly to NotebookLM

In tab **喂给 NotebookLM** fill:
- Notebook ID
- Optional profile name

The app internally calls:

```bash
notebooklm [-p <profile>] source add /tmp/notebooklm_trading_report.md -n <notebook_id>
```

## 5) Generate DeepSeek discussion

In tab **DeepSeek 讨论** fill:
- `DeepSeek API Key`
- model (default `deepseek-chat`)

The app sends your generated report prompt to DeepSeek chat-completions API and returns a realistic Bull/Bear/Risk panel discussion with desk conclusion.

## 6) Deploy remotely

You can deploy this Streamlit app on Docker/Cloud Run/VM, then expose port `8501` behind auth and TLS.

Security notes:
- Restrict who can access command execution mode.
- Use a low-privilege runtime user.
- Prefer allowlisted TradingAgents commands in production.
- Keep DeepSeek API keys in secret manager / env vars (not hardcoded).
