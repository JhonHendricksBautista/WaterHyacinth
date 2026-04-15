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
THRESHOLD = 40
DATA_PATH = "analytics.csv"
DASHBOARD_UPDATE_INTERVAL = 10

# ==============================
# PAGE CONFIG (UNCHANGED UI)
# ==============================
st.set_page_config(
    page_title="Hyasim Dashboard",
    layout="wide"
)

if "run_camera" not in st.session_state:
    st.session_state.run_camera = False

# ==============================
# MODEL (FIXED)
# ==============================
@st.cache_resource
def load_model():
    model = YOLO(MODEL_PATH)
    model.to("cpu")
    return model

model = load_model()

# ==============================
# DATA
# ==============================
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
# TITLE (UNCHANGED UI)
# ==============================
st.title("Hyasim Monitoring System")

tab1, tab2, tab3 = st.tabs([
    "Live Detection",
    "Media Upload",
    "Dashboard"
])

# ==============================
# DASHBOARD UI (UNCHANGED)
# ==============================
with tab3:
    st.subheader("System Analytics")
    dash_warning = st.empty()

    m1, m2 = st.columns(2)
    cov_metric_box = m1.empty()
    fps_metric_box = m2.empty()

    chart1_box = st.empty()
    chart2_box = st.empty()
    data_box = st.empty()

def update_dashboard_ui():
    df = load_data()

    if df.empty:
        dash_warning.warning("No data yet.")
        return

    dash_warning.empty()

    latest = df.iloc[-1]
    df_recent = df.tail(200)

    cov_metric_box.metric("Current Coverage", f"{latest['coverage']:.2f}%")
    fps_metric_box.metric("Latest FPS", f"{latest['fps']:.2f}")

    fig1 = px.line(df_recent, x="timestamp", y="coverage", title="Coverage Over Time")
    fig1.add_hline(y=THRESHOLD, line_dash="dash", line_color="red")
    chart1_box.plotly_chart(fig1, use_container_width=True)

    fig2 = px.line(df_recent, x="timestamp", y="fps", title="FPS Over Time")
    chart2_box.plotly_chart(fig2, use_container_width=True)

    data_box.dataframe(df.tail(50), use_container_width=True)

# ==============================
# MEDIA UPLOAD TAB (FIXED ONLY LOGIC)
# ==============================
with tab2:
    st.subheader("Upload Media for Detection")

    media_type = st.radio("Select Media Type:", ["🖼️ Image", "🎬 Video"], horizontal=True)

    # ================= IMAGE =================
    if media_type == "🖼️ Image":
        uploaded_image = st.file_uploader("Upload an image", type=["jpg", "jpeg", "png"])

        if uploaded_image is not None:
            file_bytes = np.asarray(bytearray(uploaded_image.read()), dtype=np.uint8)
            image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            image = cv2.resize(image, (FRAME_SIZE, FRAME_SIZE))

            if st.button("Run Detection on Image"):

                results = model.predict(
                    source=image,
                    conf=0.5,
                    imgsz=640,
                    verbose=False,
                    device="cpu"
                )

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

                color = (0, 0, 255) if coverage > THRESHOLD else (0, 255, 0)

                overlay = image.copy()
                overlay[mask == 1] = color
                overlay = cv2.addWeighted(image, 1, overlay, 0.5, 0)

                status = "ALERT" if coverage > THRESHOLD else "SAFE"

                cv2.putText(overlay, f"Coverage: {coverage:.2f}%", (20, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

                cv2.putText(overlay, f"Status: {status}", (20, 80),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

                st.image(cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB))

                st.success(f"Coverage: {coverage:.2f}% | {status}")

    # ================= VIDEO =================
    else:
        uploaded_video = st.file_uploader("Upload a video", type=["mp4", "mov", "avi"])

        if uploaded_video is not None:
            temp_input_path = "temp_input.mp4"
            temp_output_path = "temp_output.mp4"

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
                last_mask = np.zeros((FRAME_SIZE, FRAME_SIZE), dtype=np.uint8)

                while cap.isOpened():
                    ret, frame = cap.read()
                    if not ret:
                        break

                    frame = cv2.resize(frame, (FRAME_SIZE, FRAME_SIZE))
                    frame_count += 1

                    mask = last_mask

                    if frame_count % INFERENCE_INTERVAL == 0:
                        results = model.predict(
                            frame,
                            conf=0.5,
                            imgsz=640,
                            verbose=False,
                            device="cpu"
                        )

                        mask = np.zeros((FRAME_SIZE, FRAME_SIZE), dtype=np.uint8)

                        for r in results:
                            if r.masks is not None:
                                masks = r.masks.data.cpu().numpy()
                                for m in masks:
                                    m = cv2.resize(m, (FRAME_SIZE, FRAME_SIZE))
                                    mask = cv2.bitwise_or(mask, (m > 0.5).astype(np.uint8))

                        last_mask = mask

                    coverage = (np.sum(mask) / mask.size) * 100

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
                    progress_bar.progress(frame_count / total_frames)

                cap.release()
                out.release()

                st.success("Video processing complete!")
                st.video(temp_output_path)

# ==============================
# LIVE CAMERA TAB (FIXED ONLY LOGIC)
# ==============================
with tab1:
    st.markdown("<h3 style='text-align: center;'>Live Camera</h3>", unsafe_allow_html=True)

    b_col1, b_col2, b_col3, b_col4 = st.columns(4)
    with b_col2:
        start_btn = st.button("▶ Start Camera", use_container_width=True)
    with b_col3:
        stop_btn = st.button("⏹ Stop Camera", use_container_width=True)

    cam_status = st.empty()
    frame_window = st.empty()

if start_btn:
    st.session_state.run_camera = True

if stop_btn:
    st.session_state.run_camera = False

if not st.session_state.run_camera:
    update_dashboard_ui()

if st.session_state.run_camera:
    cap = cv2.VideoCapture(0)

    prev_time = 0
    frame_count = 0
    last_mask = np.zeros((FRAME_SIZE, FRAME_SIZE), dtype=np.uint8)
    last_coverage = 0.0

    last_dash_update = time.time()
    update_dashboard_ui()

    while cap.isOpened() and st.session_state.run_camera:
        ret, frame = cap.read()
        if not ret:
            cam_status.error("Camera disconnected.")
            break

        frame = cv2.resize(frame, (FRAME_SIZE, FRAME_SIZE))
        frame_count += 1

        current_time = time.time()
        fps = 1 / (current_time - prev_time) if prev_time else 0
        prev_time = current_time

        mask = last_mask

        if frame_count % INFERENCE_INTERVAL == 0:
            results = model.predict(
                frame,
                conf=0.5,
                imgsz=640,
                verbose=False,
                device="cpu"
            )

            mask = np.zeros((FRAME_SIZE, FRAME_SIZE), dtype=np.uint8)

            for r in results:
                if r.masks is not None:
                    masks = r.masks.data.cpu().numpy()
                    for m in masks:
                        m = cv2.resize(m, (FRAME_SIZE, FRAME_SIZE))
                        mask = cv2.bitwise_or(mask, (m > 0.5).astype(np.uint8))

            last_mask = mask
            last_coverage = (np.sum(mask) / mask.size) * 100
        else:
            mask = last_mask

        coverage = last_coverage

        color = (0, 0, 255) if coverage > THRESHOLD else (0, 255, 0)

        overlay = frame.copy()
        overlay[mask == 1] = color
        overlay = cv2.addWeighted(frame, 1, overlay, 0.5, 0)

        cv2.putText(overlay, f"Coverage: {coverage:.2f}%", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

        cv2.putText(overlay, f"Status: {'ALERT' if coverage > THRESHOLD else 'SAFE'}",
                    (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

        cv2.putText(overlay, f"FPS: {fps:.2f}",
                    (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)

        if frame_count % 10 == 0:
            log_data(coverage, fps)

        frame_window.image(cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB))

        if time.time() - last_dash_update > DASHBOARD_UPDATE_INTERVAL:
            update_dashboard_ui()
            last_dash_update = time.time()

    cap.release()