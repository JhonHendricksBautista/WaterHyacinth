import streamlit as st
import pandas as pd
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
MODEL_PATH = "Mr92.pt"
FRAME_SIZE = 640
INFERENCE_INTERVAL = 12
THRESHOLD = 40  # Alert threshold updated to 40%
DATA_PATH = "analytics.csv"
DASHBOARD_UPDATE_INTERVAL = 10  # Seconds between dashboard updates

# ==============================
# PAGE CONFIG
# ==============================

st.set_page_config(
    page_title="Hyasim Dashboard",
    layout="wide"
)

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
st.title("Hyasim Monitoring System")

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
# TAB 2: MEDIA UPLOAD (COMPLETED)
# ==============================
with tab2:
    st.subheader("Upload Media for Detection")

    media_type = st.radio("Select Media Type:", ["🖼️ Image", "🎬 Video"], horizontal=True)
    st.write("---")

    # ==============================
    # IMAGE UPLOAD
    # ==============================
    if media_type == "🖼️ Image":
        uploaded_image = st.file_uploader("Upload an image", type=["jpg", "jpeg", "png"])

        if uploaded_image is not None:
            file_bytes = np.asarray(bytearray(uploaded_image.read()), dtype=np.uint8)
            image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            image = cv2.resize(image, (FRAME_SIZE, FRAME_SIZE))

            if st.button("Run Detection on Image"):
                results = model(image, conf=0.5, imgsz=640, verbose=False)

                mask = np.zeros((FRAME_SIZE, FRAME_SIZE), dtype=np.uint8)

                for r in results:
                    if r.masks is not None:
                        masks = r.masks.data.cpu().numpy()
                        for m in masks:
                            m = cv2.resize(m, (FRAME_SIZE, FRAME_SIZE))
                            mask = cv2.bitwise_or(mask, (m > 0.5).astype(np.uint8))

                # Morphological cleaning
                kernel = np.ones((5, 5), np.uint8)
                mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
                mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

                coverage = (np.sum(mask) / mask.size) * 100

                color = (0, 0, 255) if coverage > THRESHOLD else (0, 255, 0)

                overlay = image.copy()
                overlay[mask == 1] = color
                overlay = cv2.addWeighted(image, 1, overlay, 0.5, 0)

                status = "ALERT" if coverage > THRESHOLD else "SAFE"

                cv2.putText(overlay, f"Coverage: {coverage:.2f}%", (20, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
                cv2.putText(overlay, f"Status: {status}", (20, 80),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

                st.image(cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB), use_container_width=True)
                st.success(f"Coverage: {coverage:.2f}% | Status: {status}")

    # ==============================
    # VIDEO UPLOAD
    # ==============================
    else:
        uploaded_video = st.file_uploader("Upload a video", type=["mp4", "mov", "avi"])

        if uploaded_video is not None:
            temp_input_path = "temp_input.mp4"
            temp_output_path = "temp_output.mp4"

            # Save uploaded video
            with open(temp_input_path, "wb") as f:
                f.write(uploaded_video.read())

            if st.button("Run Detection on Video"):
                cap = cv2.VideoCapture(temp_input_path)

                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                out = cv2.VideoWriter(
                    temp_output_path,
                    fourcc,
                    20.0,
                    (FRAME_SIZE, FRAME_SIZE)
                )

                frame_count = 0
                progress_bar = st.progress(0)

                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

                while cap.isOpened():
                    ret, frame = cap.read()
                    if not ret:
                        break

                    frame = cv2.resize(frame, (FRAME_SIZE, FRAME_SIZE))
                    frame_count += 1

                    # Run inference every N frames
                    if frame_count % INFERENCE_INTERVAL == 0:
                        results = model(frame, conf=0.5, imgsz=640, verbose=False)

                        mask = np.zeros((FRAME_SIZE, FRAME_SIZE), dtype=np.uint8)

                        for r in results:
                            if r.masks is not None:
                                masks = r.masks.data.cpu().numpy()
                                for m in masks:
                                    m = cv2.resize(m, (FRAME_SIZE, FRAME_SIZE))
                                    mask = cv2.bitwise_or(mask, (m > 0.5).astype(np.uint8))

                        kernel = np.ones((5, 5), np.uint8)
                        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
                        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

                        coverage = (np.sum(mask) / mask.size) * 100
                    else:
                        coverage = 0

                    color = (0, 0, 255) if coverage > THRESHOLD else (0, 255, 0)

                    overlay = frame.copy()
                    overlay[mask == 1] = color
                    overlay = cv2.addWeighted(frame, 1, overlay, 0.5, 0)

                    status = "ALERT" if coverage > THRESHOLD else "SAFE"

                    cv2.putText(overlay, f"Coverage: {coverage:.2f}%", (20, 40),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
                    cv2.putText(overlay, f"Status: {status}", (20, 80),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

                    out.write(overlay)

                    progress_bar.progress(min(frame_count / total_frames, 1.0))

                cap.release()
                out.release()

                st.success("Video processing complete!")

                # Display video
                video_file = open(temp_output_path, "rb")
                st.video(video_file.read())

                # Download button
                with open(temp_output_path, "rb") as f:
                    st.download_button(
                        "Download Processed Video",
                        f,
                        file_name="processed_video.mp4"
                    )
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

