import streamlit as st
import pandas as pd
<<<<<<< HEAD
import time
import os
import subprocess
=======
import os
import cv2
import numpy as np
import time
from ultralytics import YOLO
from datetime import datetime
import plotly.express as px

# ==============================
# CONFIG
# ==============================
MODEL_PATH = r"C:\Users\Chris\Downloads\WaterHyasim_\mr89.pt"
FRAME_SIZE = 640
INFERENCE_INTERVAL = 12
THRESHOLD = 40  # Alert threshold updated to 40%
DATA_PATH = "analytics.csv"
DASHBOARD_UPDATE_INTERVAL = 10  # Seconds between dashboard updates
>>>>>>> b0d1189 (Commit WaterHyacinth)

# ==============================
# PAGE CONFIG
# ==============================
<<<<<<< HEAD
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
=======
st.set_page_config(page_title="HyacinthEye", layout="wide")

# ==============================
# SESSION STATE INITIALIZATION
# ==============================
if "run_camera" not in st.session_state:
    st.session_state.run_camera = False

# ==============================
# LOAD MODEL & DATA
# ==============================
@st.cache_resource
def load_model():
    return YOLO(MODEL_PATH)

model = load_model()

def load_data():
    cols = ["timestamp", "coverage", "fps"]
    if os.path.exists(DATA_PATH):
        df = pd.read_csv(DATA_PATH, header=None)
        df = df.iloc[:, :3]
        df.columns = cols
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        return df
    return pd.DataFrame(columns=cols)

def log_data(coverage, fps):
    with open(DATA_PATH, "a") as f:
        f.write(f"{datetime.now()},{coverage:.2f},{fps:.2f}\n")

# ==============================
# UI HEADER & TABS (DRAWN ONCE)
# ==============================
st.title("HyacinthEye Monitoring System")

# Merged Image and Video into a single "Media Upload" tab
tab1, tab2, tab3 = st.tabs([
    "Live Detection", 
    "Media Upload", 
    "Dashboard"
])

# ==============================
# TAB 3: DASHBOARD PLACEHOLDERS
# ==============================
with tab3:
    st.subheader("System Analytics")
    dash_warning = st.empty()
    
    # Create the columns FIRST, then put empty placeholders INSIDE them
    m1, m2 = st.columns(2)
    cov_metric_box = m1.empty()
    fps_metric_box = m2.empty()

    # Placeholders for the charts and data table
    chart1_box = st.empty()
    chart2_box = st.empty()
    data_box = st.empty()

def update_dashboard_ui():
    """Overwrites the placeholders directly instead of stacking widgets."""
    df = load_data()
    if df.empty:
        dash_warning.warning("No data yet. Start the camera to log data.")
        return

    dash_warning.empty() # Clear warning if we have data
    latest = df.iloc[-1]
    df_recent = df.tail(200)

    # 1. Update Metrics
    cov_metric_box.metric("Current Coverage", f"{latest['coverage']:.2f}%")
    fps_metric_box.metric("Latest FPS", f"{latest['fps']:.2f}")

    # 2. Update Charts
    fig1 = px.line(df_recent, x="timestamp", y="coverage", title="Coverage Over Time")
    fig1.add_hline(y=THRESHOLD, line_dash="dash", line_color="red", annotation_text="Alert Threshold (40%)")
    chart1_box.plotly_chart(fig1, use_container_width=True)

    fig2 = px.line(df_recent, x="timestamp", y="fps", title="FPS Over Time")
    chart2_box.plotly_chart(fig2, use_container_width=True)

    # 3. Update Dataframe
    data_box.dataframe(df.tail(50), use_container_width=True)

# ==============================
# TAB 2: MEDIA UPLOAD PLACEHOLDER
# ==============================
with tab2:
    st.subheader("Upload Media for Detection")
    
    # A sleek radio button to toggle between Image and Video modes
    media_type = st.radio("Select Media Type:", ["🖼️ Image", "🎬 Video"], horizontal=True)
    
    st.write("---")

    if media_type == "🖼️ Image":
        st.info("Image upload functionality coming soon. You will be able to upload a single image to test hyacinth detection.")
    else:
        st.info("Video processing coming soon. You will be able to upload an mp4 file to run batch inference.")

# ==============================
# TAB 1: CAMERA UI
# ==============================
with tab1:
    st.markdown("<h3 style='text-align: center;'>Live Camera</h3>", unsafe_allow_html=True)
    
    # Centered Buttons
    b_col1, b_col2, b_col3, b_col4 = st.columns(4)
    with b_col2:
        start_btn = st.button("▶ Start Camera", use_container_width=True)
    with b_col3:
        stop_btn = st.button("⏹ Stop Camera", use_container_width=True)

    cam_status = st.empty() # Placeholder specifically for error messages
    st.write("") 
    
    # ==========================================
    # FULL-SCREEN VIDEO FEED
    # ==========================================
    frame_window = st.empty()

# ==============================
# BUTTON LOGIC
# ==============================
if start_btn:
    st.session_state.run_camera = True
if stop_btn:
    st.session_state.run_camera = False

# Draw dashboard immediately on load if camera is off
if not st.session_state.run_camera:
    update_dashboard_ui()

# ==============================
# CONTINUOUS CAMERA LOOP
# ==============================
if st.session_state.run_camera:
    cap = cv2.VideoCapture(0)
    prev_time = 0
    frame_count = 0
    last_mask = np.zeros((FRAME_SIZE, FRAME_SIZE), dtype=np.uint8)
    last_coverage = 0.0
    
    last_dash_update = time.time()
    update_dashboard_ui() # Initial population of dashboard

    while cap.isOpened() and st.session_state.run_camera:
        ret, frame = cap.read()
        if not ret:
            cam_status.error("Camera disconnected. Please check your connection.") 
            break

        frame = cv2.resize(frame, (FRAME_SIZE, FRAME_SIZE))
        frame_count += 1

        # FPS
        current_time = time.time()
        fps = 1 / (current_time - prev_time) if prev_time > 0 else 0
        prev_time = current_time

        # Inference
        if frame_count % INFERENCE_INTERVAL == 0:
            results = model(frame, conf=0.5, imgsz=640, verbose=False)
            mask = np.zeros((FRAME_SIZE, FRAME_SIZE), dtype=np.uint8)

            for r in results:
                if r.masks is not None:
                    masks = r.masks.data.cpu().numpy()
                    for m in masks:
                        m = cv2.resize(m, (FRAME_SIZE, FRAME_SIZE))
                        mask = cv2.bitwise_or(mask, (m > 0.5).astype(np.uint8))

            # ==========================================
            # MORPHOLOGICAL CLEANING
            # ==========================================
            kernel = np.ones((5, 5), np.uint8)
            # 1. Opening: Removes tiny stray pixels (noise) in the water
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            # 2. Closing: Fills in tiny gaps/holes inside the hyacinth clusters
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

            coverage = (np.sum(mask) / mask.size) * 100
            last_mask = mask
            last_coverage = coverage
        else:
            mask = last_mask
            coverage = last_coverage

        # Overlay
        color = (0, 0, 255) if coverage > THRESHOLD else (0, 255, 0)
        overlay = frame.copy()
        overlay[mask == 1] = color
        overlay = cv2.addWeighted(frame, 1, overlay, 0.5, 0)
        status = "ALERT" if coverage > THRESHOLD else "SAFE"

        cv2.putText(overlay, f"Coverage: {coverage:.2f}%", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
        cv2.putText(overlay, f"Status: {status}", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
        cv2.putText(overlay, f"FPS: {fps:.2f}", (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        # Logging
        if frame_count % 10 == 0:
            log_data(coverage, fps)

        # Update Video Box directly (Stretches to fill container width)
        frame_rgb = cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB)
        frame_window.image(frame_rgb, channels="RGB", use_container_width=True)

        # Update Dashboard Boxes every 10 seconds
        if current_time - last_dash_update >= DASHBOARD_UPDATE_INTERVAL:
            update_dashboard_ui()
            last_dash_update = current_time

    cap.release()
>>>>>>> b0d1189 (Commit WaterHyacinth)
