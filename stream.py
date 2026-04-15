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
# PAGE CONFIG
# ==============================
st.set_page_config(
    page_title="Hyasim Dashboard",
    layout="wide"
)

if "run_camera" not in st.session_state:
    st.session_state.run_camera = False

# ==============================
# MODEL
# ==============================
@st.cache_resource
def load_model():
    model = YOLO(MODEL_PATH)
    model.to("cpu")  # IMPORTANT for Streamlit Cloud
    return model

model = load_model()

# ==============================
# DATA HANDLING
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
# DASHBOARD PLACEHOLDERS
# ==============================
st.title("Hyasim Monitoring System")

tab1, tab2, tab3 = st.tabs(["Live Detection", "Media Upload", "Dashboard"])

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
# MEDIA UPLOAD TAB
# ==============================
with tab2:
    st.subheader("Upload Media for Detection")

    media_type = st.radio("Select Media Type:", ["Image", "Video"], horizontal=True)

    # ================= IMAGE =================
    if media_type == "Image":
        uploaded_image = st.file_uploader("Upload image", type=["jpg", "jpeg", "png"])

        if uploaded_image:
            file_bytes = np.asarray(bytearray(uploaded_image.read()), dtype=np.uint8)
            image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

            image = cv2.resize(image, (FRAME_SIZE, FRAME_SIZE))

            if st.button("Run Detection on Image"):

                # ✅ FIXED INFERENCE
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

                cv2.putText(overlay, f"{coverage:.2f}%", (20, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

                cv2.putText(overlay, status, (20, 80),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

                st.image(cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB),
                         use_container_width=True)

                st.success(f"Coverage: {coverage:.2f}% | {status}")

    # ================= VIDEO =================
    else:
        uploaded_video = st.file_uploader("Upload video", type=["mp4", "mov", "avi"])

        if uploaded_video:
            input_path = "temp.mp4"
            output_path = "output.mp4"

            with open(input_path, "wb") as f:
                f.write(uploaded_video.read())

            if st.button("Run Detection on Video"):

                cap = cv2.VideoCapture(input_path)

                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                out = cv2.VideoWriter(output_path, fourcc, 20.0, (FRAME_SIZE, FRAME_SIZE))

                frame_count = 0
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                progress = st.progress(0)

                last_mask = np.zeros((FRAME_SIZE, FRAME_SIZE), dtype=np.uint8)

                while cap.isOpened():
                    ret, frame = cap.read()
                    if not ret:
                        break

                    frame = cv2.resize(frame, (FRAME_SIZE, FRAME_SIZE))
                    frame_count += 1

                    mask = last_mask

                    if frame_count % INFERENCE_INTERVAL == 0:
                        results = model.predict(frame, conf=0.5, imgsz=640, verbose=False)

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

                    cv2.putText(overlay, f"{coverage:.2f}%", (20, 40),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

                    status = "ALERT" if coverage > THRESHOLD else "SAFE"
                    cv2.putText(overlay, status, (20, 80),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

                    out.write(overlay)
                    progress.progress(frame_count / total_frames)

                cap.release()
                out.release()

                st.success("Done!")

                st.video(output_path)

# ==============================
# CAMERA TAB (UNCHANGED CORE FIXES ONLY)
# ==============================
with tab1:
    st.subheader("Live Camera")

    col1, col2 = st.columns(2)
    start = col1.button("Start")
    stop = col2.button("Stop")

    frame_box = st.empty()

if start:
    st.session_state.run_camera = True

if stop:
    st.session_state.run_camera = False

if st.session_state.run_camera:
    cap = cv2.VideoCapture(0)

    last_mask = np.zeros((FRAME_SIZE, FRAME_SIZE), dtype=np.uint8)

    while cap.isOpened() and st.session_state.run_camera:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.resize(frame, (FRAME_SIZE, FRAME_SIZE))

        results = model.predict(frame, conf=0.5, imgsz=640, verbose=False)

        mask = np.zeros((FRAME_SIZE, FRAME_SIZE), dtype=np.uint8)

        for r in results:
            if r.masks is not None:
                masks = r.masks.data.cpu().numpy()
                for m in masks:
                    m = cv2.resize(m, (FRAME_SIZE, FRAME_SIZE))
                    mask = cv2.bitwise_or(mask, (m > 0.5).astype(np.uint8))

        overlay = frame.copy()
        overlay[mask == 1] = (0, 0, 255)
        overlay = cv2.addWeighted(frame, 1, overlay, 0.5, 0)

        frame_box.image(cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB))

    cap.release()