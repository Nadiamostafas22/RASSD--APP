# RASSD — Risk Analysis & Supply Status Dashboard

A comprehensive supply chain risk management platform built with Streamlit, implementing the SANAD AI architecture for predictive inventory triage, AI explainability, and automated alerting.

## Run & Operate

- `streamlit run app.py --server.port 5000` — run the dashboard (managed by "RASSD Dashboard" workflow)

## Stack

- Python 3.13 + Streamlit 1.59
- Plotly for interactive charts
- Pandas for data processing
- XlsxWriter / openpyxl for Excel export

## Where things live

- `app.py` — single-file Streamlit application (all modules)
- `.streamlit/config.toml` — server configuration (port 5000, headless)

## Architecture decisions

- Single-file app for simplicity; all tabs are functions called from `main()`
- Session state (`st.session_state`) holds uploaded data, triage results, action logs, and share flags across reruns
- Demo data generates 50 SKUs × 90 days with varied risk profiles (critical/moderate/healthy) seeded for reproducibility
- Triage engine uses `Days of Cover = Inventory / Daily Sales Velocity` with configurable thresholds
- Confidence scores are deterministic per tier with ±3% random jitter for realism

## Product

- **Data Upload & Demo Mode** — CSV upload or one-click demo with 50 pre-built SKUs
- **RASSD Predictive Triage Engine** — Critical/Moderate/Low classification with auto-scheduling and alert simulation
- **Simulated Gemini AI Analysis** — 7-section explainable triage per SKU with confidence gauge
- **Google Sheets Log Simulator** — full audit trail with delivery error simulation, CSV/Excel export
- **Executive Dashboard** — KPI cards, top-10 critical bar chart, risk distribution pie chart, full SKU table

## User preferences

_Populate as you build — explicit user instructions worth remembering across sessions._

## Gotchas

- Streamlit reruns on every widget interaction; session_state is essential for persisting computed data
- `st.rerun()` replaces the deprecated `st.experimental_rerun()`
- Do not change `.streamlit/config.toml` server section — headless + 0.0.0.0 binding is required for Replit proxy
