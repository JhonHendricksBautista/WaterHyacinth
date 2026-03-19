import streamlit as st
import pandas as pd
import time
import os
import subprocess



# Page config
st.set_page_config(
    page_title="Water Hyacinth Monitoring System",
    layout="wide"
)

st.title("🌿 Water Hyacinth Monitoring Dashboard")

DATA_PATH = "analytics.csv"

# Auto refresh
refresh_rate = st.sidebar.slider("Refresh rate (seconds)", 1, 10, 2)

# Load data
def load_data():
    if os.path.exists(DATA_PATH):
        df = pd.read_csv(DATA_PATH)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df
    else:
        return pd.DataFrame(columns=["timestamp","coverage","fps","biomass"])

# Main loop (auto-refresh)
placeholder = st.empty()

st.sidebar.subheader("Control Panel")

if st.sidebar.button("▶ Start Detection"):
    subprocess.Popen(["python", r"C:\Users\Win10\OneDrive\Documents\WaterHyacinth\camera.py"])

if st.sidebar.button("⏹ Stop Detection"):
    # Optional: kill process (basic version)
    subprocess.call("taskkill /f /im python.exe", shell=True)

while True:
    df = load_data()

    with placeholder.container():

        if df.empty:
            st.warning("No data available yet...")
        else:
            latest = df.iloc[-1]

            # ---- METRICS ----
            col1, col2, col3, col4 = st.columns(4)

            col1.metric("🌿 Coverage %", f"{latest['coverage']:.2f}%")
            col2.metric("⚖️ Biomass (kg/m²)", f"{latest['biomass']:.2f}")
            col3.metric("⚡ FPS", f"{latest['fps']:.2f}")
            col4.metric("📊 Total Samples", len(df))

            st.divider()

            # ---- CHARTS ----
            colA, colB = st.columns(2)

            with colA:
                st.subheader("Coverage Over Time")
                st.line_chart(df.set_index("timestamp")["coverage"])

            with colB:
                st.subheader("Biomass Over Time")
                st.line_chart(df.set_index("timestamp")["biomass"])

            st.subheader("FPS Performance")
            st.line_chart(df.set_index("timestamp")["fps"])

            # ---- SUMMARY STATS ----
            st.subheader("Summary Statistics")

            col5, col6, col7 = st.columns(3)

            col5.metric("Avg Coverage", f"{df['coverage'].mean():.2f}%")
            col6.metric("Avg Biomass", f"{df['biomass'].mean():.2f}")
            col7.metric("Avg FPS", f"{df['fps'].mean():.2f}")

            # ---- RAW DATA ----
            with st.expander("View Raw Data"):
                st.dataframe(df.tail(50))

    time.sleep(refresh_rate)