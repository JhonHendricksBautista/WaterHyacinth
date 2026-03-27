import cv2
import numpy as np
import time
import os
from ultralytics import YOLO
from datetime import datetime

# ==============================
# CONFIG
# ==============================
MODEL_PATH = r"C:\Users\Win10\OneDrive\Documents\WaterHyacinth\BAGONG WIEGHTS\mr89.pt"
FRAME_SIZE = 640
INFERENCE_INTERVAL = 12   # balanced (you used 24 → too slow)
THRESHOLD = 20

SCREENSHOT_DELAY = 30
SCREENSHOT_COOLDOWN = 30

SAVE_DIR = "Critical Infestation"
os.makedirs(SAVE_DIR, exist_ok=True)

# ==============================
# INIT
# ==============================
model = YOLO(MODEL_PATH)
cap = cv2.VideoCapture(0)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_SIZE)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_SIZE)

frame_count = 0
prev_time = 0

coverage_buffer = []
fps_buffer = []

last_mask = np.zeros((FRAME_SIZE, FRAME_SIZE), dtype=np.uint8)
last_coverage = 0.0

last_critical_time = None
last_screenshot_time = 0

# ==============================
# FUNCTIONS
# ==============================
def log_data(coverage, fps):
    with open("analytics.csv", "a") as f:
        f.write(f"{datetime.now()},{coverage:.2f},{fps:.2f}\n")

def process_masks(results):
    mask = np.zeros((FRAME_SIZE, FRAME_SIZE), dtype=np.uint8)

    if results[0].masks is not None:
        masks = results[0].masks.data.cpu().numpy()

        for m in masks:
            m_resized = cv2.resize(m, (FRAME_SIZE, FRAME_SIZE))
            binary = (m_resized > 0.5).astype(np.uint8)
            mask = cv2.bitwise_or(mask, binary)

    # Morphological cleaning
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

    return mask

def calculate_coverage(mask):
    return (np.sum(mask) / mask.size) * 100

def apply_overlay(frame, mask, coverage):
    color = (0, 0, 255) if coverage > THRESHOLD else (0, 255, 0)

    colored_mask = np.zeros_like(frame)
    colored_mask[mask == 1] = color

    overlay = cv2.addWeighted(frame, 1, colored_mask, 0.5, 0)
    return overlay, color

# ==============================
# MAIN LOOP
# ==============================
while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.resize(frame, (FRAME_SIZE, FRAME_SIZE))
    frame_count += 1

    # ==============================
    # FPS (smoothed)
    # ==============================
    current_time = time.time()
    fps = 1 / (current_time - prev_time) if prev_time > 0 else 0
    prev_time = current_time

    fps_buffer.append(fps)
    if len(fps_buffer) > 10:
        fps_buffer.pop(0)
    fps_display = np.mean(fps_buffer)

    # ==============================
    # INFERENCE
    # ==============================
    if frame_count % INFERENCE_INTERVAL == 0:
        results = model(frame, conf=0.5, imgsz=640, verbose=False)

        mask = process_masks(results)
        coverage = calculate_coverage(mask)

        # Smooth coverage
        coverage_buffer.append(coverage)
        if len(coverage_buffer) > 10:
            coverage_buffer.pop(0)

        coverage = np.mean(coverage_buffer)

        # SAVE STATE
        last_mask = mask
        last_coverage = coverage

    else:
        mask = last_mask
        coverage = last_coverage

    # ==============================
    # APPLY OVERLAY
    # ==============================
    overlay, color = apply_overlay(frame, mask, coverage)
    status = "ALERT" if coverage > THRESHOLD else "SAFE"

    # ==============================
    # CRITICAL DETECTION SYSTEM
    # ==============================
    if coverage > THRESHOLD:
        if last_critical_time is None:
            last_critical_time = time.time()

        if time.time() - last_critical_time >= SCREENSHOT_DELAY:
            if time.time() - last_screenshot_time >= SCREENSHOT_COOLDOWN:
                filename = os.path.join(
                    SAVE_DIR,
                    f"critical_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                )
                cv2.imwrite(filename, overlay)
                print(f"[INFO] Screenshot saved: {filename}")
                last_screenshot_time = time.time()
    else:
        last_critical_time = None

    # ==============================
    # DISPLAY UI
    # ==============================
    cv2.putText(overlay, f"Coverage: {coverage:.2f}%", (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

    cv2.putText(overlay, f"Status: {status}", (20, 80),
                cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

    cv2.putText(overlay, f"FPS: {fps_display:.2f}", (20, 120),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

    log_data(coverage, fps_display)

    cv2.imshow("Hyacinth Monitoring System", overlay)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()