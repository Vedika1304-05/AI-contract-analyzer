"""
app.py - the Streamlit app (the screen your users see).
Run it with:   streamlit run app.py
"""
import tempfile
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import config, pipeline, risk_rules, cashflow

st.set_page_config(page_title="AI Contract Analyser", layout="wide")
st.title("AI Contract Analyser for Financial Risk Clauses")
st.caption("CE725 Construction Economics and Finance - decision-support tool")

st.warning("**Confidentiality:** if you use the AI engine, text from the contract is sent to an external AI "
           "provider. Use only public or non-confidential documents. "
           "**Human verification required:** check every extracted value against the original contract. "
           "This tool is not legal advice.")

# ------------------------------------------------------------------ sidebar inputs
with st.sidebar:
    st.header("Settings")
    engine_label = st.radio("Extraction engine", ["AI (LLM)", "Rules only (baseline, no AI)"])
    engine = "llm" if engine_label.startswith("AI") else "baseline"
    if engine == "llm":
        st.caption(f"Provider: {config.PROVIDER} | prompt: {config.PROMPT_VERSION}")
    run_id = st.number_input("Run number (new number = fresh AI answer)", min_value=1, value=1, step=1)
    st.header("Project assumptions")
    contract_value = st.number_input("Contract value (Rs lakh)", min_value=1.0, value=1000.0, step=50.0)
    duration = st.number_input("Duration (months)", min_value=2, max_value=60, value=10, step=1)
    cost_ratio = st.slider("Cost as % of billing", 50, 100, 90) / 100
    overdraft_rate = st.slider("Overdraft interest (% per year)", 5.0, 20.0, 11.0, 0.5) / 100
    dlp = st.number_input("Defects liability period (months)", min_value=0, max_value=36, value=12)

# ------------------------------------------------------------------ choose the contract
source = st.radio("Contract source", ["Pick a PDF from the data/ folder", "Upload a PDF"], horizontal=True)
pdf_path = None
if source.startswith("Pick"):
    files = sorted(str(p) for p in (config.ROOT / "data").rglob("*.pdf"))
    if files:
        pdf_path = st.selectbox("Contract", files)
    else:
        st.info("No PDFs found in the data/ folder yet.")
else:
    up = st.file_uploader("Upload a text-based contract PDF", type="pdf")
    if up is not None:
        tmp = Path(tempfile.gettempdir()) / up.name
        tmp.write_bytes(up.getbuffer())
        pdf_path = str(tmp)

if st.button("Analyse contract", type="primary", disabled=pdf_path is None):
    bar = st.progress(0.0, text="Starting...")
    try:
        st.session_state["analysis"] = pipeline.analyse(
            pdf_path, engine=engine, run_id=int(run_id),
            progress=lambda i, n, c: bar.progress(i / n, text=f"Extracting {c} ({i}/{n})"))
        bar.empty()
    except Exception as e:
        bar.empty()
        st.error(f"Could not analyse this contract: {e}")

analysis = st.session_state.get("analysis")
if analysis:
    results = analysis["results"]
    st.subheader(f"1. Extracted clauses - {analysis['contract']}")
    st.caption(f"Engine: {analysis['engine']} | pages: {analysis['n_pages']} | "
               "Check column: 'verified' = quote found on that page; 'unverified' = quote NOT found (do not trust).")
    table = pipeline.results_table(analysis)
    st.dataframe(table.drop(columns=["Error"]), width="stretch")
    bad = [k for k, r in results.items() if r.found and r.verification == "unverified"]
    if bad:
        st.error(f"Quote could not be verified for: {', '.join(bad)}. These may be invented - check manually.")
    errs = [k for k, r in results.items() if r.error]
    if errs:
        st.warning(f"Extraction errors for: {', '.join(errs)} (see the Error column in the CSV download).")

    # ---------------------------------------------------------- risk flags
    st.subheader("2. Risk flags")
    flags = risk_rules.assess(results, duration_months=int(duration))
    icon = {"high": "🔴 HIGH", "medium": "🟠 MEDIUM", "low": "🟢 LOW", "info": "⚪ CHECK"}
    st.dataframe(pd.DataFrame([{"Level": icon[f["level"]], "Clause": f["clause"], "Finding": f["finding"],
                                "Why it matters": f["reason"]} for f in flags]), width="stretch")

    # ---------------------------------------------------------- cash flow
    st.subheader("3. Cash flow impact")
    params, assumptions = pipeline.cashflow_params_from_results(
        results, contract_value, int(duration), cost_ratio, overdraft_rate, int(dlp))
    df, summ = cashflow.run_cashflow(**params)
    clean = dict(params, retention_pct=0.0, retention_cap_pct=None, payment_delay_months=0, advance_pct=0.0)
    df_clean, summ_clean = cashflow.run_cashflow(**clean)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Peak funding need (Rs lakh)", f"{summ['peak_funding']:.1f}")
    c2.metric("Overdraft interest (Rs lakh)", f"{summ['total_interest']:.1f}")
    c3.metric("Max retention locked (Rs lakh)", f"{summ['max_retention_locked']:.1f}")
    c4.metric("Peak funding with NO delay / retention / advance", f"{summ_clean['peak_funding']:.1f}")

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["Month"], y=df["Cumulative cash"], name="With contract terms", mode="lines+markers"))
    fig.add_trace(go.Scatter(x=df_clean["Month"], y=df_clean["Cumulative cash"], name="Clean baseline", mode="lines"))
    fig.update_layout(xaxis_title="Month", yaxis_title="Cumulative cash (Rs lakh)", height=420)
    st.plotly_chart(fig, width="stretch")
    with st.expander("Assumptions used"):
        for a in assumptions:
            st.write("- " + a)
    with st.expander("Monthly cash flow table"):
        st.dataframe(df, width="stretch")
    with st.expander("Sensitivity: payment delay and retention"):
        st.dataframe(cashflow.sensitivity_table(params), width="stretch")

    # ---------------------------------------------------------- summary + downloads
    st.subheader("4. Plain-language summary")
    st.text(risk_rules.plain_summary(flags, summ))
    st.download_button("Download results (CSV)", table.to_csv(index=False), f"{analysis['contract']}_results.csv")
