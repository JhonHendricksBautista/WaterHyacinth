import streamlit as st
import pandas as pd
import time
import os
import subprocess

# ==============================
# PAGE CONFIG
# ==============================
st.set_page_config(
    page_title="HyacinthEye Dashboard",
    layout="wide"
)

# ==============================
# CUSTOM CSS (UI UPGRADE)
# ==============================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background-color: #D9FFF5;
    color: #2D3047;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background-color: #2D3047;
}
section[data-testid="stSidebar"] * {
    color: white !important;
}

/* Cards */
.card {
    background-color: #F7F7FF;
    padding: 20px;
    border-radius: 12px;
    box-shadow: 0px 4px 10px rgba(0,0,0,0.05);
}

/* Metric Highlight */
.metric {
    font-size: 20px;
    font-weight: 600;
    color: #1B9AAA;
}

/* Status colors */
.safe {
    color: green;
    font-weight: bold;
}
.alert {
    color: red;
    font-weight: bold;
}

/* Buttons */
.stButton>button {
    background-color: #1B9AAA;
    color: white;
    border-radius: 8px;
}
.stButton>button:hover {
    background-color: #148a96;
}
</style>
""", unsafe_allow_html=True)

# ==============================
# HEADER
# ==============================
st.markdown("<h1 style='text-align:center;'>🌿 HyacinthEye</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;'>Water Hyacinth Monitoring System</p>", unsafe_allow_html=True)

DATA_PATH = "analytics.csv"

# ==============================
# SIDEBAR
# ==============================
st.sidebar.header("Control Panel")

refresh_rate = st.sidebar.slider("Refresh Rate (sec)", 1, 10, 2)

if st.sidebar.button("▶ Start Detection"):
    subprocess.Popen(["python", r"C:\Users\Win10\OneDrive\Documents\WaterHyacinth\camera.py"])

if st.sidebar.button("⏹ Stop Detection"):
    subprocess.call("taskkill /f /im python.exe", shell=True)

# ==============================
# LOAD DATA
# ==============================
def load_data():
    if os.path.exists(DATA_PATH):
        df = pd.read_csv(DATA_PATH)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df
    return pd.DataFrame(columns=["timestamp","coverage","fps","biomass"])

df = load_data()

# ==============================
# MAIN DASHBOARD
# ==============================
if df.empty:
    st.warning("No data available yet...")
else:
    latest = df.iloc[-1]

    # STATUS
    status = "SAFE" if latest["coverage"] < 20 else "ALERT"
    status_class = "safe" if status == "SAFE" else "alert"

    # ==============================
    # METRICS ROW
    # ==============================
    col1, col2, col3, col4 = st.columns(4)

    col1.markdown(f"<div class='card'><p>🌿 Coverage</p><h2 class='metric'>{latest['coverage']:.2f}%</h2></div>", unsafe_allow_html=True)
    col2.markdown(f"<div class='card'><p>⚖️ Biomass</p><h2 class='metric'>{latest['biomass']:.2f}</h2></div>", unsafe_allow_html=True)
    col3.markdown(f"<div class='card'><p>⚡ FPS</p><h2 class='metric'>{latest['fps']:.2f}</h2></div>", unsafe_allow_html=True)
    col4.markdown(f"<div class='card'><p>Status</p><h2 class='{status_class}'>{status}</h2></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ==============================
    # CHARTS
    # ==============================
    colA, colB = st.columns(2)

    with colA:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("📈 Coverage Over Time")
        st.line_chart(df.set_index("timestamp")["coverage"])
        st.markdown("</div>", unsafe_allow_html=True)

    with colB:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.subheader("📊 Biomass Over Time")
        st.line_chart(df.set_index("timestamp")["biomass"])
        st.markdown("</div>", unsafe_allow_html=True)

    # ==============================
    # FPS CHART
    # ==============================
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("⚡ FPS Performance")
    st.line_chart(df.set_index("timestamp")["fps"])
    st.markdown("</div>", unsafe_allow_html=True)

    # ==============================
    # SUMMARY
    # ==============================
    st.subheader("Summary Statistics")

    col5, col6, col7 = st.columns(3)

    col5.metric("Avg Coverage", f"{df['coverage'].mean():.2f}%")
    col6.metric("Avg Biomass", f"{df['biomass'].mean():.2f}")
    col7.metric("Avg FPS", f"{df['fps'].mean():.2f}")

    # ==============================
    # RAW DATA
    # ==============================
    with st.expander("View Raw Data"):
        st.dataframe(df.tail(50))

# ==============================
# AUTO REFRESH (STREAMLIT SAFE)
# ==============================
time.sleep(refresh_rate)
st.rerun()