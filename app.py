"""
RASSD: Risk Analysis & Supply Status Dashboard
A comprehensive supply chain risk management platform.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import random
import io
import os

# ─── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="RASSD — Risk Analysis & Supply Status Dashboard",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Session state defaults ──────────────────────────────────────────────────
if "df" not in st.session_state:
    st.session_state.df = None
if "triage_df" not in st.session_state:
    st.session_state.triage_df = None
if "action_logs" not in st.session_state:
    st.session_state.action_logs = []
if "share_flags" not in st.session_state:
    st.session_state.share_flags = {}

# ─── Demo data generator ─────────────────────────────────────────────────────
SUPPLIERS = [
    "GlobalEdge Supply Co.", "NexLogistics Ltd.", "PrimePath Distributors",
    "TerraFlex Partners", "Apex Chain Corp.", "BlueSky Fulfillment",
    "OmniTrade Solutions", "SwiftBridge Logistics",
]

def generate_demo_data() -> pd.DataFrame:
    random.seed(42)
    skus = [f"SKU-{1000 + i}" for i in range(50)]
    rows = []
    base_date = datetime(2024, 1, 1)
    for sku in skus:
        supplier = random.choice(SUPPLIERS)
        price = round(random.uniform(5, 500), 2)
        cost = round(price * random.uniform(0.4, 0.75), 2)
        for d in range(90):
            date = base_date + timedelta(days=d)
            # Create varied inventory profiles for richer triage
            profile = random.choice(["critical", "moderate", "healthy"])
            if profile == "critical":
                inventory = random.randint(0, 20)
                units_sold = random.uniform(5, 25)
            elif profile == "moderate":
                inventory = random.randint(300, 800)
                units_sold = random.uniform(0, 1.5)
            else:
                inventory = random.randint(80, 400)
                units_sold = random.uniform(8, 40)
            rows.append({
                "SKU": sku,
                "Inventory Levels": inventory,
                "Units Sold": round(units_sold, 1),
                "Price": price,
                "Cost": cost,
                "Supplier": supplier,
                "Date": date.strftime("%Y-%m-%d"),
            })
    return pd.DataFrame(rows)


# ─── Triage engine ───────────────────────────────────────────────────────────
DELIVERY_STATUSES = [
    "Success", "Success", "Success",
    "API Connection Timeout - Retrying",
    "Failed - Invalid Email",
    "Success",
    "Success",
    "Delivery Queued",
]

def log_action(sku: str, action_type: str, recipient: str):
    status = random.choice(DELIVERY_STATUSES)
    st.session_state.action_logs.append({
        "SKU": sku,
        "Action Type": action_type,
        "Recipient": recipient,
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Delivery Status": status,
    })


def compute_triage(df: pd.DataFrame) -> pd.DataFrame:
    agg = (
        df.groupby("SKU")
        .agg(
            Inventory=("Inventory Levels", "last"),
            Daily_Sales_Velocity=("Units Sold", "mean"),
            Price=("Price", "first"),
            Cost=("Cost", "first"),
            Supplier=("Supplier", "first"),
        )
        .reset_index()
    )
    agg["Days_of_Cover"] = agg.apply(
        lambda r: r["Inventory"] / r["Daily_Sales_Velocity"]
        if r["Daily_Sales_Velocity"] > 0
        else 9999,
        axis=1,
    )

    def classify(row):
        doc = row["Days_of_Cover"]
        vel = row["Daily_Sales_Velocity"]
        inv = row["Inventory"]
        if doc < 2:
            return "CRITICAL"
        elif inv > 200 and vel < 2:
            return "MODERATE"
        else:
            return "LOW"

    agg["Risk_Tier"] = agg.apply(classify, axis=1)
    agg["Capital_Tied"] = (agg["Cost"] * agg["Inventory"]).round(2)
    agg["Replenishment_Date"] = agg["Risk_Tier"].apply(
        lambda t: (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        if t == "CRITICAL"
        else "—"
    )
    return agg


# ─── Sidebar / data loading ──────────────────────────────────────────────────
def sidebar_upload():
    st.sidebar.title("📦 RASSD")
    st.sidebar.caption("Risk Analysis & Supply Status Dashboard")
    st.sidebar.markdown("---")

    st.sidebar.subheader("Data Source")
    uploaded = st.sidebar.file_uploader(
        "Upload Kaggle CSV", type=["csv"], help="High-Dimensional Supply Chain Inventory Dataset"
    )
    use_demo = st.sidebar.button("🗂 Use Demo Mock Data", use_container_width=True)

    if use_demo:
        st.session_state.df = generate_demo_data()
        st.session_state.triage_df = compute_triage(st.session_state.df)
        st.session_state.action_logs = []
        st.session_state.share_flags = {}
        st.sidebar.success("Demo data loaded — 50 SKUs / 90 days")

    if uploaded:
        try:
            raw = pd.read_csv(uploaded)
            required = {"SKU", "Inventory Levels", "Units Sold", "Price", "Cost", "Supplier", "Date"}
            missing = required - set(raw.columns)
            if missing:
                st.sidebar.error(f"Missing columns: {', '.join(missing)}")
            else:
                st.session_state.df = raw
                st.session_state.triage_df = compute_triage(raw)
                st.session_state.action_logs = []
                st.session_state.share_flags = {}
                st.sidebar.success(f"Loaded {len(raw):,} rows from CSV")
        except Exception as e:
            st.sidebar.error(f"Parse error: {e}")

    st.sidebar.markdown("---")
    st.sidebar.markdown("**SANAD AI Architecture v2.0**")
    st.sidebar.caption("Powered by RASSD Predictive Triage Engine")


# ─── Executive Dashboard ─────────────────────────────────────────────────────
def tab_dashboard(triage: pd.DataFrame):
    st.header("📊 Executive Visual Dashboard")

    critical = triage[triage["Risk_Tier"] == "CRITICAL"]
    moderate = triage[triage["Risk_Tier"] == "MODERATE"]
    low = triage[triage["Risk_Tier"] == "LOW"]
    capital_at_risk = critical["Capital_Tied"].sum()
    active_tasks = len(critical) * 2 + len(moderate)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total SKUs", len(triage))
    c2.metric("Critical Alerts", len(critical), delta="Pending Action", delta_color="inverse")
    c3.metric("Capital at Risk", f"${capital_at_risk:,.0f}", delta_color="inverse")
    c4.metric("Active Automation Tasks", active_tasks)

    st.markdown("---")
    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.subheader("Top 10 Critical SKUs — Days of Cover")
        top10 = (
            triage.nsmallest(10, "Days_of_Cover")[["SKU", "Days_of_Cover", "Risk_Tier"]]
            .copy()
        )
        color_map = {"CRITICAL": "#E74C3C", "MODERATE": "#F39C12", "LOW": "#27AE60"}
        top10["Color"] = top10["Risk_Tier"].map(color_map)
        fig_bar = px.bar(
            top10,
            x="Days_of_Cover",
            y="SKU",
            orientation="h",
            color="Risk_Tier",
            color_discrete_map=color_map,
            labels={"Days_of_Cover": "Days of Cover", "SKU": ""},
            title="",
        )
        fig_bar.update_layout(
            height=360,
            margin=dict(l=0, r=0, t=10, b=0),
            legend_title_text="Risk Tier",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(categoryorder="total ascending"),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_right:
        st.subheader("Overall Risk Distribution")
        dist = triage["Risk_Tier"].value_counts().reset_index()
        dist.columns = ["Risk_Tier", "Count"]
        color_map2 = {"CRITICAL": "#E74C3C", "MODERATE": "#F39C12", "LOW": "#27AE60"}
        fig_pie = px.pie(
            dist,
            names="Risk_Tier",
            values="Count",
            color="Risk_Tier",
            color_discrete_map=color_map2,
            hole=0.4,
        )
        fig_pie.update_layout(
            height=360,
            margin=dict(l=0, r=0, t=10, b=0),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        fig_pie.update_traces(textinfo="percent+label")
        st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("---")
    st.subheader("Full SKU Risk Table")
    display = triage[["SKU", "Inventory", "Daily_Sales_Velocity", "Days_of_Cover",
                       "Risk_Tier", "Capital_Tied", "Supplier", "Replenishment_Date"]].copy()
    display.columns = ["SKU", "Inventory", "Avg Daily Sales", "Days of Cover",
                       "Risk Tier", "Capital Tied ($)", "Supplier", "Replenishment Date"]
    display["Days of Cover"] = display["Days of Cover"].apply(
        lambda x: f"{x:.1f}" if x < 9999 else "∞"
    )
    display["Capital Tied ($)"] = display["Capital Tied ($)"].apply(lambda x: f"${x:,.2f}")
    display["Avg Daily Sales"] = display["Avg Daily Sales"].apply(lambda x: f"{x:.2f}")

    def row_color(val):
        if val == "CRITICAL":
            return "background-color: #fde8e8; color: #c0392b; font-weight: bold"
        elif val == "MODERATE":
            return "background-color: #fef3cd; color: #856404; font-weight: bold"
        else:
            return "background-color: #d4edda; color: #155724; font-weight: bold"

    styled = display.style.applymap(row_color, subset=["Risk Tier"])
    st.dataframe(styled, use_container_width=True, height=420)


# ─── Triage Actions ──────────────────────────────────────────────────────────
def tab_triage(triage: pd.DataFrame):
    st.header("⚠️ RASSD Predictive Triage Engine")

    critical = triage[triage["Risk_Tier"] == "CRITICAL"]
    moderate = triage[triage["Risk_Tier"] == "MODERATE"]
    low = triage[triage["Risk_Tier"] == "LOW"]

    # ── CRITICAL ──────────────────────────────────────────────────────────────
    with st.expander(f"🔴 CRITICAL RISK  —  {len(critical)} SKUs  (Days of Cover < 2)", expanded=True):
        if critical.empty:
            st.success("No critical SKUs detected.")
        else:
            for _, row in critical.iterrows():
                col1, col2, col3 = st.columns([2, 2, 1])
                with col1:
                    st.markdown(f"**{row['SKU']}**  |  Supplier: {row['Supplier']}")
                    st.caption(f"Inventory: {row['Inventory']} units  |  Daily Sales: {row['Daily_Sales_Velocity']:.1f}  |  Days of Cover: {row['Days_of_Cover']:.1f}")
                with col2:
                    st.markdown(f"📅 Replenishment Scheduled: `{row['Replenishment_Date']}`")
                with col3:
                    if st.button("🚨 Trigger Alerts", key=f"crit_{row['SKU']}"):
                        log_action(row["SKU"], "Urgent Replenishment Order", "Warehouse Manager")
                        log_action(row["SKU"], "Urgent Supplier Alert", row["Supplier"])
                        st.toast(f"Alerts sent for {row['SKU']}!", icon="🚨")
                st.markdown("---")

    # ── MODERATE ──────────────────────────────────────────────────────────────
    with st.expander(f"🟡 MODERATE RISK  —  {len(moderate)} SKUs  (Stagnant / Excess Stock)", expanded=False):
        if moderate.empty:
            st.success("No moderate-risk SKUs detected.")
        else:
            for _, row in moderate.iterrows():
                sku = row["SKU"]
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**{sku}**  |  Supplier: {row['Supplier']}")
                    st.caption(f"Inventory: {row['Inventory']} units  |  Daily Sales: {row['Daily_Sales_Velocity']:.2f}  |  Capital Tied: ${row['Capital_Tied']:,.2f}")
                with col2:
                    share_key = f"share_{sku}"
                    checked = st.checkbox("Share with Supplier?", key=share_key)
                    if checked and not st.session_state.share_flags.get(sku):
                        st.session_state.share_flags[sku] = True
                        log_action(sku, "Analysis Shared — Stagnant Stock", "Retailer")
                        log_action(sku, "Analysis Shared — Stagnant Stock", row["Supplier"])
                        st.toast(f"Notified Retailer & {row['Supplier']} for {sku}", icon="📤")
                st.markdown("---")

    # ── LOW ───────────────────────────────────────────────────────────────────
    with st.expander(f"🟢 LOW RISK  —  {len(low)} SKUs  (Healthy Stock)", expanded=False):
        if low.empty:
            st.info("No healthy SKUs.")
        else:
            sku_select = st.selectbox(
                "Select a healthy SKU to preview email template",
                low["SKU"].tolist(),
                key="low_select",
            )
            row = low[low["SKU"] == sku_select].iloc[0]
            email_body = f"""
📧 **System Healthy Notification**

To: Warehouse Team
Subject: ✅ Inventory Health Report — {sku_select}

Dear Warehouse Team,

Your inventory levels for **{sku_select}** are well within healthy parameters.

**Summary:**
- Current Inventory: {row['Inventory']} units
- Average Daily Sales: {row['Daily_Sales_Velocity']:.2f} units/day
- Days of Cover: {row['Days_of_Cover']:.1f} days

**Proactive Advice:**
1. Continue current replenishment cycle — no intervention needed.
2. Consider bundling promotions to accelerate healthy turnover.
3. Maintain supplier relationship with {row['Supplier']} for priority access.
4. Monitor for demand spikes during seasonal peaks.

Keep up the great work!

— RASSD Automated System
            """
            st.markdown(email_body)
            if st.button("📤 Log Email Sent", key=f"low_log_{sku_select}"):
                log_action(sku_select, "System Healthy Email", "Warehouse Team")
                st.toast("Email logged successfully!", icon="✅")


# ─── AI Explainable Triage ────────────────────────────────────────────────────
def tab_ai_analysis(triage: pd.DataFrame):
    st.header("🤖 Simulated Gemini AI Explainable Triage")
    st.caption("Transparent 7-section breakdown for any selected SKU")

    sku_list = triage["SKU"].tolist()
    selected = st.selectbox("Select SKU for AI Analysis", sku_list, key="ai_sku")

    if st.button("🔍 Generate AI Analysis", type="primary", key="ai_btn"):
        row = triage[triage["SKU"] == selected].iloc[0]
        tier = row["Risk_Tier"]
        doc = row["Days_of_Cover"]
        vel = row["Daily_Sales_Velocity"]
        inv = row["Inventory"]
        capital = row["Capital_Tied"]
        supplier = row["Supplier"]

        # Confidence score based on data quality
        confidence = 97 if tier == "CRITICAL" else (84 if tier == "MODERATE" else 91)
        confidence += random.randint(-3, 3)

        tier_icons = {"CRITICAL": "🔴", "MODERATE": "🟡", "LOW": "🟢"}
        icon = tier_icons[tier]

        sections = {
            "1. Risk Level Classification": f"{icon} **{tier} RISK**\n\nBased on the current inventory profile, this SKU has been classified as **{tier} RISK**. "
                + (f"With only **{doc:.1f} days of cover** remaining, immediate action is required to prevent stockout."
                   if tier == "CRITICAL"
                   else (f"Stagnant stock detected with **{doc:.0f}+ days of cover** and near-zero velocity. Capital efficiency is at risk."
                         if tier == "MODERATE"
                         else f"This SKU maintains a healthy **{doc:.1f} days of cover** with consistent sales velocity. No intervention needed.")),

            "2. Velocity Trend": f"**Current Sales Momentum:** {vel:.2f} units/day\n\n"
                + (f"Sales velocity is HIGH ({vel:.2f} u/day). The current depletion rate against low inventory creates an imminent stockout risk within **{doc:.1f} days**."
                   if tier == "CRITICAL"
                   else (f"Sales velocity is NEAR-ZERO ({vel:.2f} u/day). Stock has remained stagnant over the observed period. Demand stimulation or liquidation strategy recommended."
                         if tier == "MODERATE"
                         else f"Velocity is STABLE at {vel:.2f} u/day. Trend analysis shows consistent consumer demand with no anomalous spikes or drops.")),

            "3. Financial Exposure": f"**Capital Tied Up:** ${capital:,.2f}\n\n"
                + (f"At current sales velocity, a stockout will result in **lost revenue** of approximately ${vel * row['Price'] * doc:,.2f} over the risk window. Emergency replenishment freight costs may add 15–25% to unit cost."
                   if tier == "CRITICAL"
                   else (f"**${capital:,.2f}** of working capital is locked in stagnant inventory. Opportunity cost is accumulating. Holding costs estimated at 20–30% annually."
                         if tier == "MODERATE"
                         else f"Financial exposure is LOW. Capital of ${capital:,.2f} is efficiently deployed with {doc:.0f} days of runway. No financial risk detected.")),

            "4. Lead Time & Nearest Supplier Scheduling": f"**Preferred Supplier:** {supplier}\n\n"
                + (f"URGENT ORDER RECOMMENDED. Nearest supplier dispatch window: **{(datetime.now() + timedelta(days=1)).strftime('%A, %B %d %Y')}**. Estimated standard lead time: 3–5 business days. Given {doc:.1f}-day cover, express logistics channel activation is advised."
                   if tier == "CRITICAL"
                   else (f"No immediate order required. However, **{supplier}** should be contacted to discuss return or markdown coordination. Rebalancing inventory across locations may alleviate holding cost."
                         if tier == "MODERATE"
                         else f"Current replenishment cycle with **{supplier}** is aligned to demand. Next scheduled order should proceed without modification.")),

            "5. Action Justification": "**Why this decision was made:**\n\n"
                + (f"The RASSD Triage Engine flagged this SKU because Days of Cover ({doc:.1f}) fell below the critical threshold of 2 days. Cross-referenced against the 90-day velocity profile, the system determined that a stockout event is **imminent without intervention**. Automated alerts have been queued for the Warehouse Manager and {supplier}."
                   if tier == "CRITICAL"
                   else (f"The engine detected an inverse relationship between inventory levels ({inv} units) and daily sales velocity ({vel:.2f} u/day). This pattern is consistent with demand decline, forecast misalignment, or poor product-market fit. Sharing analysis with the supplier enables collaborative markdown or return decisions."
                         if tier == "MODERATE"
                         else f"All key performance indicators — Days of Cover ({doc:.1f}), daily velocity ({vel:.2f} u/day), and capital efficiency — fall within acceptable ranges. The system confirms operational stability for this SKU.")),

            "6. Proactive Mitigation Step": "**Recommended Next Action:**\n\n"
                + (f"1. Activate emergency supplier order via {supplier}\n2. Notify Warehouse Manager for expedited put-away slots\n3. Consider temporary demand throttling (price increase) to stretch remaining stock\n4. Flag for priority receiving dock allocation upon delivery"
                   if tier == "CRITICAL"
                   else (f"1. Run a 14-day promotional push to accelerate sell-through\n2. Request supplier return authorization for overstocked units\n3. Consider cross-docking to higher-velocity locations\n4. Reassess demand forecast for next quarter"
                         if tier == "MODERATE"
                         else f"1. Maintain current replenishment cadence\n2. Set a Days-of-Cover alert at 7 days for early warning\n3. Explore demand-boosting promotions to capitalize on availability\n4. Share positive health report with warehouse team for morale")),

            "7. Triage Confidence Score": f"**{confidence}%**\n\n"
                + f"The RASSD AI engine processed 90 days of historical data across {len(triage)} SKUs to derive this classification. The confidence score of **{confidence}%** reflects the consistency of the velocity signal and the clarity of the inventory trajectory. "
                + ("High confidence in critical classification due to strong depletion signal."
                   if tier == "CRITICAL"
                   else ("Moderate confidence due to ambiguity in near-zero velocity — recommend manual review."
                         if tier == "MODERATE"
                         else "High confidence in healthy classification — pattern is stable and well-defined.")),
        }

        for title, content in sections.items():
            with st.expander(f"🔹 {title}", expanded=True):
                st.markdown(content)

        log_action(selected, "AI Triage Analysis Generated", "System")

        col1, col2, col3 = st.columns(3)
        with col1:
            conf_fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=confidence,
                title={"text": "Confidence Score"},
                gauge={
                    "axis": {"range": [0, 100]},
                    "bar": {"color": "#2ECC71" if confidence > 85 else "#F39C12"},
                    "steps": [
                        {"range": [0, 60], "color": "#fde8e8"},
                        {"range": [60, 80], "color": "#fff3cd"},
                        {"range": [80, 100], "color": "#d4edda"},
                    ],
                },
                number={"suffix": "%"},
            ))
            conf_fig.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(conf_fig, use_container_width=True)


# ─── Logs Tab ─────────────────────────────────────────────────────────────────
def tab_logs():
    st.header("📋 Google Sheets Logs — Simulated Delivery Audit")

    if not st.session_state.action_logs:
        st.info("No actions logged yet. Trigger alerts or generate AI analysis to populate the log.")
        return

    log_df = pd.DataFrame(st.session_state.action_logs)

    # KPIs
    total = len(log_df)
    success = (log_df["Delivery Status"] == "Success").sum()
    failed = log_df["Delivery Status"].str.startswith("Failed").sum()
    retrying = log_df["Delivery Status"].str.contains("Retrying|Queued").sum()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Log Entries", total)
    c2.metric("Successful Deliveries", success)
    c3.metric("Failed Deliveries", failed)
    c4.metric("Pending / Retrying", retrying)

    st.markdown("---")

    def color_status(val):
        if val == "Success":
            return "background-color: #d4edda; color: #155724"
        elif "Failed" in str(val):
            return "background-color: #fde8e8; color: #c0392b"
        else:
            return "background-color: #fff3cd; color: #856404"

    styled = log_df.style.applymap(color_status, subset=["Delivery Status"])
    st.dataframe(styled, use_container_width=True, height=480)

    st.markdown("---")
    col1, col2, col3 = st.columns(3)

    with col1:
        csv_buf = io.StringIO()
        log_df.to_csv(csv_buf, index=False)
        st.download_button(
            "⬇️ Download as CSV",
            data=csv_buf.getvalue().encode(),
            file_name=f"rassd_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with col2:
        excel_buf = io.BytesIO()
        with pd.ExcelWriter(excel_buf, engine="xlsxwriter") as writer:
            log_df.to_excel(writer, index=False, sheet_name="RASSD Logs")
        st.download_button(
            "⬇️ Download as Excel",
            data=excel_buf.getvalue(),
            file_name=f"rassd_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    with col3:
        if st.button("🗑 Clear All Logs", use_container_width=True):
            st.session_state.action_logs = []
            st.rerun()


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    sidebar_upload()

    st.title("📦 RASSD — Risk Analysis & Supply Status Dashboard")
    st.caption("SANAD AI Architecture · Predictive Supply Chain Triage · Powered by RASSD Engine v2.0")

    if st.session_state.df is None or st.session_state.triage_df is None:
        st.markdown("---")
        st.info("👈 **Get started:** Upload a supply chain CSV or click **Use Demo Mock Data** in the sidebar to load pre-built data.")
        with st.container():
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown("### 📤 Upload CSV\nSupports the Kaggle High-Dimensional Supply Chain Inventory Dataset format.")
            with c2:
                st.markdown("### 🤖 AI Triage\nSimulated Gemini AI analysis with 7-section explainable breakdown per SKU.")
            with c3:
                st.markdown("### 📊 Live Dashboard\nExecutive KPIs, risk distribution charts, and audit logs.")
        return

    tabs = st.tabs([
        "📊 Executive Dashboard",
        "⚠️ Triage Engine",
        "🤖 AI Analysis",
        "📋 Delivery Logs",
    ])

    with tabs[0]:
        tab_dashboard(st.session_state.triage_df)
    with tabs[1]:
        tab_triage(st.session_state.triage_df)
    with tabs[2]:
        tab_ai_analysis(st.session_state.triage_df)
    with tabs[3]:
        tab_logs()


if __name__ == "__main__":
    main()
