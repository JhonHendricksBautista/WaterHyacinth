import cv2
from ultralytics import YOLO
from datetime import datetime
import time

model = YOLO(r"C:\Users\Win10\OneDrive\Documents\WaterHyacinth\BAGONG WIEGHTS\AMDw.pt")
cap = cv2.VideoCapture(0)

def log_data(coverage, fps, biomass):
    with open("analytics.csv", "a") as f:
        f.write(f"{datetime.now()},{coverage},{fps},{biomass}\n")

prev_time = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break

    results = model(frame)

    annotated = results[0].plot()

    # Dummy values (replace with your real calculation)
    coverage = 30.0
    biomass = 1.5

    # FPS
    curr_time = time.time()
    fps = 1 / (curr_time - prev_time) if prev_time != 0 else 0
    prev_time = curr_time

    log_data(coverage, fps, biomass)

    cv2.imshow("Detection", annotated)

    if cv2.waitKey(1) == 27:
        break

cap.release()
cv2.destroyAllWindows()