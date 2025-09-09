import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
import numpy as np
import httpx
import plotly.graph_objects as go
from utils.logger import get_logger
import os
import glob

logger = get_logger("FrontendStreamlitApp")
st.set_page_config(page_title="FariSight Analytics", layout="wide")

# Auto-refresh every 5 sec
st_autorefresh(interval=5000, limit=None, key="dashboardrefresh")


# Fetch KPIs
@st.cache_data(ttl=2)
def fetch_kpis():
    try:
        resp = httpx.get("http://localhost:8081/kpis", timeout=3)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error(f"Could not load KPI data: {e}")
        return None


kpis = fetch_kpis()
if not kpis:
    st.stop()


# ---------- Load Font Awesome ----------
st.markdown(
    """
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
""",
    unsafe_allow_html=True,
)

# ----- PAGE HEADER BAR -----
header_col1, header_col2 = st.columns([0.15, 0.85])
with header_col1:
    st.image("utils/assets/i-exceed-Hi-Res-copy-1.png", width=120)

with header_col2:
    st.markdown(
        """
        <div style="padding:6px 0 10px 0; background:none;">
            <div style="display:flex; align-items:center;gap:20px;">
                <div style="font-size:2.1em;font-weight:700;letter-spacing:-1.2px;">
                FariSight Analytics
                </div>
                <div style="flex:1 1 auto"></div>
                <div>
                    <a href="#" class="download-btn" style="background:#e53935;color:white;padding:7px 20px;border-radius:6px;font-size:1em;font-weight:500;text-decoration:none;margin-right:10px;">
                        <i class="fa-solid fa-file-pdf" style="margin-right:6px;"></i> Download PDF
                    </a>
                    <a href="#" class="download-btn" style="background:#27ae60;color:white;padding:7px 20px;border-radius:6px;font-size:1em;font-weight:500;text-decoration:none;">
                        <i class="fa-solid fa-file-excel" style="margin-right:6px;"></i> Download Excel
                    </a>
                </div>
            </div>
            <div style="color:#789; font-size:1.08em; margin-left:2px;">Real-time Data Insights Dashboard</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ----- METRIC CARDS -----
st.markdown(
    """
<style>
.stCard {border-radius:12px;padding:18px 14px;background:#fff;box-shadow:0 3px 10px 0 #eee;margin-bottom:6px;}
.metric-title {color:#384A5E;font-size:1.1em;margin-bottom:2px;}
.metric-value {font-size:2.0em;font-weight:bold;}
.metric-delta {font-size:.95em;padding-left:9px;}
</style>
""",
    unsafe_allow_html=True,
)

card_cont = st.container()
with card_cont:
    met1, met2, met3, met4 = st.columns(4)
    met1.markdown(
        f"""<div class='stCard'>
        <div class='metric-title'>Total Transactions</div>
        <div class='metric-value'>{kpis['total_transactions']:,}</div>
        <div class='metric-delta' style="color:#27ae60"><i class="fa-solid fa-arrow-up"></i> +15%</div>
    </div>""",
        unsafe_allow_html=True,
    )

    met2.markdown(
        f"""<div class='stCard'>
            <div class='metric-title'>Total Amount (USD)</div>
            <div class='metric-value'>${float(kpis['total_amount_usd'])/1e6:,.1f} M</div>
            <div class='metric-delta' style="color:#27ae60"><i class="fa-solid fa-arrow-up"></i> +10%</div>
        </div>""",
        unsafe_allow_html=True,
    )
    met3.markdown(
        f"""<div class='stCard'>
            <div class='metric-title'>Total Amount (RM)</div>
            <div class='metric-value'>RM {float(kpis['total_amount_rm'])/1e6:,.1f} M</div>
            <div class='metric-delta' style="color:#27ae60"><i class="fa-solid fa-arrow-up"></i> +12%</div>
        </div>""",
        unsafe_allow_html=True,
    )
    met4.markdown(
        f"""<div class='stCard'>
            <div class='metric-title'>Debit / Credit</div>
            <div class='metric-value'>{kpis['dr_count']:,} / {kpis['cr_count']:,}</div>
            <div class='metric-delta' style="color:#e74c3c"><i class="fa-solid fa-arrow-down"></i> -2%</div>
        </div>""",
        unsafe_allow_html=True,
    )

st.write("")

# --- KPI Data (from API) ---
txn_split = kpis.get("txn_type_split", {})

with st.container(border=True):
    upper = st.columns([2, 2.5, 1])
    with upper[0]:
        st.markdown(
            "<div class='trend-title' style='padding-bottom:32px; font-weight:bold;'> Transaction trend </div>",
            unsafe_allow_html=True,
        )
    with upper[1]:
        filter_choice = st.radio(
            "Transaction Type",
            list(txn_split.keys()),  # dynamically from backend
            horizontal=True,
            label_visibility="collapsed",
            key="trend_filter",
        )
    with upper[2]:
        date_range = st.selectbox(
            "Date Range",
            ["Past Hour", "Past 24 Hours"],
            key="date_range",
            label_visibility="collapsed",
        )

    # --- time binning logic ---
    if date_range == "Past Hour":
        bins = 60
        x_ticks = [f"{m:02d}m" for m in range(bins)]
    elif date_range == "Past 24 Hours":
        bins = 24
        x_ticks = [f"{h:02d}:00" for h in range(bins)]

    # --- get count for selected type ---
    txn_data = txn_split.get(filter_choice, {"count": 0})
    if isinstance(txn_data, dict):
        total_count = txn_data.get("count", 0)
    else:
        total_count = txn_data

    # (for now: simulate distribution until backend provides actual bins)
    rng = np.random.default_rng(seed=42)
    values = rng.poisson(total_count / bins, bins)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=x_ticks,
            y=values,
            mode="lines+markers",
            line={"color": "#1565c0", "width": 2},
        )
    )
    fig.update_layout(
        margin={"l": 10, "r": 10, "t": 26, "b": 10},
        xaxis_title=None,
        yaxis_title=None,
        height=250,
        plot_bgcolor="#fafcff",
    )
    st.plotly_chart(fig, use_container_width=True)


bottom_card_cont = st.container()
with bottom_card_cont:
    # --- LOWER TWO CARDS row ---
    bottom_row = st.columns([1.6, 1.1])

    # Transaction Split card
    with bottom_row[0]:
        with st.container(border=True):
            st.markdown(
                "<div class='transaction-title' style='margin-bottom:10px;font-weight:bold;font-size:1.3em;'>Transaction Split</div>",
                unsafe_allow_html=True,
            )

            cats = list(txn_split.keys())
            vals = [
                (
                    txn_split[c]["count"]
                    if isinstance(txn_split[c], dict)
                    else txn_split[c]
                )
                for c in cats
            ]

            split_fig = go.Figure([go.Bar(x=cats, y=vals, marker_color="#1565c0")])
            split_fig.update_layout(
                margin={"l": 12, "r": 12, "t": 25, "b": 20},
                xaxis_title="",
                yaxis_title="",
                height=275,
                plot_bgcolor="#fafcff",
            )
            st.plotly_chart(split_fig, use_container_width=True)

    # Failure percentage card (Donut)
    with bottom_row[1]:
        with st.container(border=True):
            st.markdown(
                """
                <div class='metric-title' style="margin-bottom:5px; font-size:1.3em; font-weight:bold;">Failure Analysis</div>
                """,
                unsafe_allow_html=True,
            )

            # overall failure stats
            total_fails = sum(
                d.get("fail_count", 0) if isinstance(d, dict) else 0
                for d in txn_split.values()
            )
            total_txns = sum(
                (
                    d.get("count", 0)
                    if isinstance(d, dict)
                    else d if isinstance(d, int) else 0
                )
                for d in txn_split.values()
            )
            failure_rate = (total_fails / total_txns * 100) if total_txns > 0 else 0

            st.markdown(
                f"""<div style='font-size:1.2em;font-weight:600;display:inline'>
                    Total Failed: {total_fails:,} ({failure_rate:.1f}% overall)
                    </div><div class='metric-delta' style="color:#e74c3c;display:inline;"><i class="fa-solid fa-arrow-up"></i> +4%</div>""",
                unsafe_allow_html=True,
            )

            # per-type failure %
            labels = []
            values = []
            hover_text = []
            for ttype, stats in txn_split.items():
                if isinstance(stats, dict) and stats.get("count", 0) > 0:
                    fails = stats.get("fail_count", 0)
                    rate = (fails / stats["count"]) * 100
                else:
                    fails, rate = 0, 0
                labels.append(ttype)
                values.append(rate)
                hover_text.append(
                    f"<b>{ttype}</b><br>Fails: <b>{fails:,}</b><br>{rate:.1f}%"
                )

            # Plotly Donut
            blue_shades = [
                "#6A5ACD",
                "#000080",
                "#4682B4",
                "#0000CD",
                "#00BFFF",
            ]  # darker to lighter

            donut_fig = go.Figure(
                data=[
                    go.Pie(
                        labels=labels,
                        values=values,
                        hole=0.55,
                        textinfo="percent",  # no labels inside
                        hoverinfo="text",
                        hovertext=hover_text,
                        marker={"colors": blue_shades[: len(labels)]},
                    )
                ]
            )
            donut_fig.update_layout(
                margin={"l": 12, "r": 12, "t": 25, "b": 20},
                height=250,
                showlegend=True,
                legend={"orientation": "v"},  # horizontal legend
            )
            st.plotly_chart(donut_fig, use_container_width=True)


# --- AI Insights & FariBot CARD FULL WIDTH ---
# --- fetch insights helper ---
def fetch_insights():
    resp = httpx.get("http://localhost:8081/insights")  # adjust backend URL if needed
    if resp.status_code == 200:
        return resp.json().get("insights", [])
    return []


# --- call chatbot backend ---
def ask_chatbot(query: str):
    try:
        resp = httpx.post(
            "http://localhost:8081/chatbot", json={"query": query}, timeout=60
        )
        if resp.status_code == 200:
            return resp.json().get("answer", "")
        else:
            return f"⚠️ Error: {resp.status_code} {resp.text}"
    except Exception as e:
        return f"⚠️ Exception: {e}"

REPORTS_DIR = "/opt/preslaes/AI_Projects/FariSight_Analytics/reports"  # same as backend

def get_latest_report():
    """Fetch the latest report PDF from the reports folder."""
    pdf_files = glob.glob(os.path.join(REPORTS_DIR, "*.pdf"))
    if not pdf_files:
        return None
    latest_file = max(pdf_files, key=os.path.getmtime)
    return latest_file

# --- AI Insights + Chatbot UI ---
ai_card = st.container()
with ai_card:

    col1, col2 = st.columns([1.6, 1.1])
    with col1:
        with st.container(border=True):
            insights = fetch_insights()
            st.markdown(
                """
                <div class='metric-title' style='font-size:1.3em; font-weight:bold; padding-bottom:10px;'>AI Insights</div>
                """,
                unsafe_allow_html=True,
            )

            for insight in insights:
                st.markdown(
                    f"""
                    <div style="display:flex; align-items:center; margin-bottom:10px; font-size:1.1em;">
                        <i class="fa-solid fa-{insight['icon']}" 
                        style="color:{insight['color']}; font-size:20px; margin-right:10px;"></i>
                        <span>{insight['text']}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            st.markdown("</div></div>", unsafe_allow_html=True)

    # # --- FariBot column (replace your existing col2 block with this) ---
    # with col2:
    #     with st.container():
    #         st.markdown(
    #             """
    #             <div class='metric-title' style='font-size:1.3em; font-weight:bold; padding-bottom:10px;'>FariBot</div>
    #             """,
    #             unsafe_allow_html=True,
    #         )

    #         # --- Config for fallback downloads ---
    #         BACKEND_BASE_URL = "http://localhost:8081"
    #         REPORTS_DIR = "/opt/preslaes/AI_Projects/FariSight_Analytics/reports"  # same as backend

    #         # --- Initialize session state ---
    #         if "chat_history" not in st.session_state:
    #             st.session_state["chat_history"] = []
    #         if "show_history" not in st.session_state:
    #             st.session_state["show_history"] = False

    #         # --- Input form ---
    #         with st.form(key="chat_form", clear_on_submit=True):
    #             user_query = st.text_input(
    #                 label="Ask FariBot", placeholder="Type your question here..."
    #             )
    #             submitted = st.form_submit_button("Send")

    #         # --- Handle new query ---
    #         if submitted and user_query.strip():
    #             with st.spinner("FariBot is thinking..."):
    #                 response = ask_chatbot(user_query)

    #             # Ensure response is a dict and preserve structure returned by backend
    #             if not isinstance(response, dict):
    #                 response = {"answer": str(response), "report_file": None, "raw": None}

    #             # Add the original user query so UI can display it
    #             response["q"] = user_query

    #             # Append the full backend response (do NOT drop report_file)
    #             st.session_state["chat_history"].append(response)

    #         # --- Display placeholder if no history ---
    #         if not st.session_state["chat_history"]:
    #             st.markdown(
    #                 """
    #                 <div style="margin-top:10px; margin-bottom: 10px; padding:10px; background:#f9f9f9; border-radius:8px; color:#789;">
    #                     Type a question above and press Send to chat with FariBot.
    #                 </div>
    #                 """,
    #                 unsafe_allow_html=True,
    #             )
    #         else:
    #             # --- Show latest answer ---
    #             latest = st.session_state["chat_history"][-1]

    #             st.markdown(
    #                 f"""
    #                 <div style="margin-top:10px; margin-bottom:10px; padding:10px; background:#f1f1f1; border-radius:8px;">
    #                     <b>You:</b> {latest.get('q', '')}
    #                 </div>
    #                 """,
    #                 unsafe_allow_html=True,
    #             )

    #             # Try to get PDF bytes:
    #             pdf_bytes = None
    #             report_path = latest.get("report_file")

    #             if report_path:
    #                 try:
    #                     # 1) If path looks local and under allowed folder, try to open it
    #                     if os.path.isabs(report_path) and report_path.startswith(REPORTS_DIR):
    #                         if os.path.exists(report_path) and os.path.isfile(report_path):
    #                             with open(report_path, "rb") as fh:
    #                                 pdf_bytes = fh.read()
    #                                 logger.info(f"Loaded report from local path: {report_path}")
    #                     # 2) Maybe backend sent a filename or relative path; try joining with REPORTS_DIR
    #                     if pdf_bytes is None:
    #                         candidate = os.path.join(REPORTS_DIR, os.path.basename(report_path))
    #                         if os.path.exists(candidate) and os.path.isfile(candidate):
    #                             with open(candidate, "rb") as fh:
    #                                 pdf_bytes = fh.read()
    #                                 logger.info(f"Loaded report from candidate path: {candidate}")
    #                 except Exception as e:
    #                     logger.warning(f"Local read failed for {report_path}: {e}")

    #                 # 3) HTTP fallback(s) - try a couple of reasonable endpoints on the backend
    #                 if pdf_bytes is None:
    #                     filename = os.path.basename(report_path)
    #                     urls_to_try = [
    #                         f"{BACKEND_BASE_URL}/reports/{filename}",  # common static mounting pattern
    #                         f"{BACKEND_BASE_URL}/download_report?path={report_path}",  # custom fallback (if backend implements)
    #                     ]
    #                     for url in urls_to_try:
    #                         try:
    #                             r = httpx.get(url, timeout=10)
    #                             if r.status_code == 200:
    #                                 # accept PDF or any binary
    #                                 pdf_bytes = r.content
    #                                 logger.info(f"Fetched report over HTTP from {url}")
    #                                 break
    #                         except Exception as e:
    #                             logger.debug(f"HTTP fallback failed for {url}: {e}")

    #             # If we have bytes, show download button
    #             if pdf_bytes:
    #                 filename = os.path.basename(report_path) if report_path else f"report_{len(st.session_state['chat_history'])}.pdf"
    #                 # Provide a clear label based on filename
    #                 if "bank_charges" in filename:
    #                     label = "⬇️ Download Bank Charges Report"
    #                 elif "failure_timeline" in filename:
    #                     label = "⬇️ Download Failure Timeline Report"
    #                 else:
    #                     label = "⬇️ Download Report"

    #                 st.download_button(
    #                     label=label,
    #                     data=pdf_bytes,
    #                     file_name=filename,
    #                     mime="application/pdf",
    #                 )
    #             else:
    #                 # No file available - show LLM answer and offer regen fallback
    #                 st.markdown(
    #                     f"""
    #                     <div style="margin-top:10px; margin-bottom:10px; padding:10px; background:#f1f1f1; border-radius:8px;">
    #                         <b>FariBot:</b> {latest.get('answer', 'No response')}
    #                     </div>
    #                     """,
    #                     unsafe_allow_html=True,
    #                 )

    #                 # Offer user to try regenerating the report (calls backend again)
    #                 regen_key = f"regen_{len(st.session_state['chat_history'])}"
    #                 if latest.get("report_file") and st.button("Regenerate report", key=regen_key):
    #                     with st.spinner("Regenerating report..."):
    #                         regen_resp = ask_chatbot(latest.get("q", ""))  # will trigger backend generation again
    #                         if not isinstance(regen_resp, dict):
    #                             regen_resp = {"answer": str(regen_resp), "report_file": None, "raw": None}
    #                         regen_resp["q"] = latest.get("q", "")
    #                         st.session_state["chat_history"].append(regen_resp)
    #                         st.experimental_rerun()  # refresh UI to pick up regenerated file

    #             # --- Show history toggle if more than 1 entry ---
    #             if len(st.session_state["chat_history"]) > 1:
    #                 toggle_label = (
    #                     "Hide history"
    #                     if st.session_state["show_history"]
    #                     else "Show history"
    #                 )
    #                 if st.button(toggle_label, key="history_toggle"):
    #                     st.session_state["show_history"] = not st.session_state["show_history"]

    #                 # Inject CSS to make toggle look like a link
    #                 st.markdown(
    #                     """
    #                     <style>
    #                         button[kind="secondary"] {
    #                             background: none !important;
    #                             border: none !important;
    #                             color: #0066cc !important;
    #                             text-decoration: underline;
    #                             font-size: 0.9em;
    #                             padding: 0;
    #                             margin-top: 5px;
    #                         }
    #                         button[kind="secondary"]:hover {
    #                             color: #004999 !important;
    #                         }
    #                     </style>
    #                     """,
    #                     unsafe_allow_html=True,
    #                 )

    #                 if st.session_state["show_history"]:
    #                     # Render older chats (use backend key names)
    #                     for chat in reversed(st.session_state["chat_history"][:-1]):
    #                         st.markdown(
    #                             f"""
    #                             <div style="margin-top:10px; padding:10px; background:#fafafa; border-radius:8px;">
    #                                 <b>You:</b> {chat.get('q','')}<br><br>
    #                                 <b>FariBot:</b> {chat.get('answer','')}
    #                             </div>
    #                             """,
    #                             unsafe_allow_html=True,
    #                         )



    with col2:
        with st.container():
            st.markdown(
                """
                <div class='metric-title' style='font-size:1.3em; font-weight:bold; padding-bottom:10px;'>FariBot</div>
                """,
                unsafe_allow_html=True,
            )

            # --- Initialize session state ---
            if "chat_history" not in st.session_state:
                st.session_state["chat_history"] = []
            if "show_history" not in st.session_state:
                st.session_state["show_history"] = False

            # --- Input form ---
            with st.form(key="chat_form", clear_on_submit=True):
                user_query = st.text_input(
                    label="Ask FariBot", placeholder="Type your question here..."
                )
                submitted = st.form_submit_button("Send")

            # --- Handle new query ---
            if submitted and user_query.strip():
                with st.spinner("FariBot is thinking..."):
                    response = ask_chatbot(user_query)

                # Normalize response (but ignore report_file from API now)
                answer_text = response.get("answer", "") if isinstance(response, dict) else str(response)

                entry = {
                    "q": user_query,
                    "a": answer_text,
                }
                st.session_state["chat_history"].append(entry)

            # --- Show latest Q/A if exists ---
            if st.session_state["chat_history"]:
                latest = st.session_state["chat_history"][-1]

                st.markdown(
                    f"""
                    <div style="margin-top:10px; margin-bottom:10px; padding:10px; background:#f1f1f1; border-radius:8px;">
                        <b>You:</b> {latest['q']}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # Always try to fetch the latest report from folder
                latest_report = get_latest_report()
                if latest_report:
                    filename = os.path.basename(latest_report)
                    if "bank_charges" in filename:
                        label = "⬇️ Download Bank Charges Report"
                    elif "failure_timeline" in filename:
                        label = "⬇️ Download Failure Timeline Report"
                    else:
                        label = f"⬇️ Download Report ({filename})"

                    with open(latest_report, "rb") as f:
                        st.download_button(
                            label=label,
                            data=f,
                            file_name=filename,
                            mime="application/pdf",
                        )
                else:
                    # No report found, fallback to just showing text
                    st.markdown(
                        f"""
                        <div style="margin-top:10px; margin-bottom:10px; padding:10px; background:#f1f1f1; border-radius:8px;">
                            <b>FariBot:</b> {latest['a']}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            else:
                # --- Placeholder when no query is asked ---
                st.markdown(
                    """
                    <div style="margin-top:10px; margin-bottom: 10px; padding:10px; background:#f9f9f9; border-radius:8px; color:#789;">
                        Type a question above and press Send to chat with FariBot.
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
# ------- Updated Custom CSS tweaks -------
st.markdown(
    """
<style>
.stCard {
    border-radius:14px;
    padding:22px 18px;
    background:#f9f9f9;  /* off white */
    box-shadow:0 6px 18px rgba(0,0,0,0.08);
    margin-bottom:18px;
    transition: all 0.25s ease-in-out; /* smooth hover animation */
}

.stCard:hover {
    background:#f1f1f1;  /* slightly darker on hover */
    box-shadow:0 8px 22px rgba(0,0,0,0.12);
}

a.download-btn:hover {opacity:.82;}
[data-testid="stMetricDelta"] > div {font-size:.98em;}
.css-184tjsw {padding-top:10px;}
[data-testid="stVerticalBlockBorderWrapper"] {
    border: 0 !important;
    border-radius: 14px;
    padding: 22px 18px;
    background: #FFFFF0;
    box-shadow: 0 6px 18px rgba(0,0,0,0.08);
    margin-bottom: 16px;
}
div[data-baseweb="text-input"] > label {
        display: none;
        height: 0;
        margin: 0;
        padding: 0;
        overflow: hidden;
    }
</style>

""",
    unsafe_allow_html=True,
)
