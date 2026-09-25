"""app.py -- Step 18 Streamlit UI for FactoryBrain."""

import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import time

import os

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="FactoryBrain Digital Twin", layout="wide")

st.title("🏭 FactoryBrain Digital Twin Dashboard")

# Create layout
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Live 3D Factory Floor")
    twin_placeholder = st.empty()

with col2:
    st.subheader("Active Cases & Escalations")
    cases_placeholder = st.empty()

metrics_placeholder = st.empty()

def fetch_twin_state():
    try:
        r = requests.get(f"{API_URL}/twin")
        return r.json()
    except:
        return None
        
def fetch_cases():
    try:
        r = requests.get(f"{API_URL}/cases")
        return r.json()
    except:
        return []

# Continuous polling loop (use Streamlit's rerun mechanism)
state = fetch_twin_state()
cases = fetch_cases()

if state:
    # Build 3D scatter plot data
    machine_data = []
    for mid, mstate in state.get("machines", {}).items():
        # Using placeholder 3D coords for machines (normally in config)
        x = hash(mid) % 100
        y = (hash(mid) // 100) % 100
        z = 0
        machine_data.append({
            "Machine": mid,
            "X": x, "Y": y, "Z": z,
            "Temp (°C)": mstate.get("temperature_c", 0.0),
            "Vibration (mm/s)": mstate.get("vibration_mm_s", 0.0),
            "Status": "Error" if mstate.get("temperature_c", 0) > 80 else "Normal"
        })
        
    df = pd.DataFrame(machine_data)
    
    if not df.empty:
        fig = px.scatter_3d(df, x='X', y='Y', z='Z', color='Status', size='Temp (°C)', 
                            hover_name='Machine',
                            color_discrete_map={"Normal": "green", "Error": "red"})
        twin_placeholder.plotly_chart(fig, use_container_width=True)
        
    # Metrics
    with metrics_placeholder.container():
        st.subheader("Machine Metrics")
        st.dataframe(df.drop(columns=["X", "Y", "Z"]))
else:
    twin_placeholder.warning("⚠️ FastAPI Backend offline. Start with: `python backend/main.py`")

if cases:
    with cases_placeholder.container():
        for case in cases:
            with st.expander(f"Case {case['case_id']} - {case['status']}"):
                st.write(f"**Machine:** {case['machine_id']}")
                st.write(f"**Line:** {case['line_id']}")
                if case.get("findings"):
                    st.write("**Latest Findings:**")
                    for agent, finding in case["findings"].items():
                        st.write(f"- _{agent}_: {finding['summary']}")
else:
    cases_placeholder.info("No active cases.")

# Refresh button or auto-rerun
time.sleep(2)
st.rerun()
