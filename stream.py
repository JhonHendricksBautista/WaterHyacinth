import streamlit as st
import pandas as pd
import os
import cv2
import numpy as np
import time
from ultralytics import YOLO
from datetime import datetime
import plotly.express as px
from av import VideoFrame

# WebRTC
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase

# ==============================
# CONFIG
# ==============================
MODEL_PATH = "Mr92.pt"
FRAME_SIZE = 640
INFERENCE_INTERVAL = 12
THRESHOLD = 40
DATA_PATH = "analytics.csv"
DASHBOARD_UPDATE_INTERVAL = 5

# ==============================
# PAGE CONFIG
# ==============================
st.set_page_config(
    page_title="Hyasim Dashboard",
    layout="wide"
)

# ==============================
# MODEL
# ==============================
@st.cache_resource
def load_model():
    model = YOLO(MODEL_PATH)
    model.to("cpu")
    return model

model = load_model()

# ==============================
# DATA FUNCTIONS
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
# TITLE
# ==============================
st.title("Hyasim Monitoring System")

tab1, tab2, tab3 = st.tabs([
    "Live Detection",
    "Media Upload",
    "Dashboard"
])

# ==============================
# DASHBOARD
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
        dash_warning.warning("No data yet. Run live detection first.")
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

# AUTO REFRESH DASHBOARD
if tab3:
    if st.checkbox("Auto Refresh Dashboard", value=True):
        update_dashboard_ui()
        time.sleep(DASHBOARD_UPDATE_INTERVAL)
        st.rerun()
    else:
        if st.button("Refresh Dashboard"):
            update_dashboard_ui()

# ==============================
# MEDIA UPLOAD
# ==============================
with tab2:
    st.subheader("Upload Media for Detection")

    media_type = st.radio("Select Media Type:", ["🖼️ Image", "🎬 Video"], horizontal=True)

    # ================= IMAGE =================
    if media_type == "🖼️ Image":
        uploaded_image = st.file_uploader("Upload an image", type=["jpg", "jpeg", "png"])

        if uploaded_image:
            file_bytes = np.asarray(bytearray(uploaded_image.read()), dtype=np.uint8)
            image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            image = cv2.resize(image, (FRAME_SIZE, FRAME_SIZE))

            if st.button("Run Detection on Image"):
                results = model.predict(image, conf=0.5, imgsz=640, device="cpu")

                mask = np.zeros((FRAME_SIZE, FRAME_SIZE), dtype=np.uint8)

                for r in results:
                    if r.masks is not None:
                        masks = r.masks.data.cpu().numpy()
                        for m in masks:
                            m = cv2.resize(m, (FRAME_SIZE, FRAME_SIZE))
                            mask = cv2.bitwise_or(mask, (m > 0.5).astype(np.uint8))

                coverage = (np.sum(mask) / mask.size) * 100
                color = (0, 0, 255) if coverage > THRESHOLD else (0, 255, 0)

                overlay = image.copy()
                overlay[mask == 1] = color
                overlay = cv2.addWeighted(image, 1, overlay, 0.5, 0)

                st.image(cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB))
                st.success(f"Coverage: {coverage:.2f}%")

    # ================= VIDEO =================
    else:
        uploaded_video = st.file_uploader("Upload video", type=["mp4", "mov", "avi"])

        if uploaded_video and st.button("Run Detection on Video"):
            temp_in = "temp.mp4"
            temp_out = "out.mp4"

            with open(temp_in, "wb") as f:
                f.write(uploaded_video.read())

            cap = cv2.VideoCapture(temp_in)

            # FIXED FPS
            fps_input = cap.get(cv2.CAP_PROP_FPS)
            if fps_input == 0:
                fps_input = 20.0

            # FIXED CODEC (better browser support)
            fourcc = cv2.VideoWriter_fourcc(*"avc1")
            out = cv2.VideoWriter(temp_out, fourcc, fps_input, (FRAME_SIZE, FRAME_SIZE))

            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                frame = cv2.resize(frame, (FRAME_SIZE, FRAME_SIZE))

                results = model.predict(frame, conf=0.5, imgsz=640, device="cpu")

                mask = np.zeros((FRAME_SIZE, FRAME_SIZE), dtype=np.uint8)

                for r in results:
                    if r.masks is not None:
                        masks = r.masks.data.cpu().numpy()
                        for m in masks:
                            m = cv2.resize(m, (FRAME_SIZE, FRAME_SIZE))
                            mask = cv2.bitwise_or(mask, (m > 0.5).astype(np.uint8))

                overlay = frame.copy()
                overlay[mask == 1] = (0, 255, 0)
                overlay = cv2.addWeighted(frame, 1, overlay, 0.5, 0)

                out.write(overlay)

            cap.release()
            out.release()

            time.sleep(1)  # ensure file is ready
            st.video(temp_out)

# ==============================
# LIVE CAMERA (FIXED)
# ==============================
class VideoProcessor(VideoTransformerBase):
    def __init__(self):
        self.frame_count = 0
        self.last_mask = np.zeros((FRAME_SIZE, FRAME_SIZE), dtype=np.uint8)
        self.last_time = time.time()

    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        img = cv2.resize(img, (FRAME_SIZE, FRAME_SIZE))

        self.frame_count += 1

        current_time = time.time()
        fps = 1 / (current_time - self.last_time)
        self.last_time = current_time

        mask = self.last_mask

        if self.frame_count % INFERENCE_INTERVAL == 0:
            results = model.predict(img, conf=0.5, imgsz=640, device="cpu")

            mask = np.zeros((FRAME_SIZE, FRAME_SIZE), dtype=np.uint8)

            for r in results:
                if r.masks is not None:
                    masks = r.masks.data.cpu().numpy()
                    for m in masks:
                        m = cv2.resize(m, (FRAME_SIZE, FRAME_SIZE))
                        mask = cv2.bitwise_or(mask, (m > 0.5).astype(np.uint8))

            self.last_mask = mask

            # ✅ LOG DATA FOR DASHBOARD
            coverage = (np.sum(mask) / mask.size) * 100
            log_data(coverage, fps)

        coverage = (np.sum(mask) / mask.size) * 100

        color = (0, 0, 255) if coverage > THRESHOLD else (0, 255, 0)

        overlay = img.copy()
        overlay[mask == 1] = color
        overlay = cv2.addWeighted(img, 1, overlay, 0.5, 0)

        cv2.putText(overlay, f"Coverage: {coverage:.2f}%", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

        cv2.putText(overlay, f"FPS: {fps:.2f}", (20, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        return VideoFrame.from_ndarray(overlay, format="bgr24")

with tab1:
    st.markdown("<h3 style='text-align: center;'>Live Camera</h3>", unsafe_allow_html=True)

    webrtc_streamer(
        key="hyasim-camera",
        video_processor_factory=VideoProcessor,
        media_stream_constraints={"video": True, "audio": False}
    )