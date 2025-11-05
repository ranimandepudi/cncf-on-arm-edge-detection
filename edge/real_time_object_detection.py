# USAGE
# python real_time_object_detection.py

# import the necessary packages
from imutils.video import VideoStream
from imutils.video import FPS
import numpy as np
import imutils
import time
import cv2
import os
from huggingface_hub import hf_hub_download

# load environment variables
INPUT_RTSP = os.getenv("INPUT_RTSP", "rtsp://host.docker.internal:8554/stream")
PERSON_THRESHOLD = float(os.getenv("PERSON_THRESHOLD", "0.60"))
EVENT_COOLDOWN_SEC = float(os.getenv("EVENT_COOLDOWN_SEC", "3"))
DEVICE_ID = os.getenv("DEVICE_ID", "mac-m4-01")
MODEL = os.getenv("MODEL", "mobilenet-ssd")
IMAGE_TAG = os.getenv("IMAGE_TAG", "ranman01/obj-det:latest")
CLOUD_API_BASE = os.getenv("CLOUD_API_BASE", "")  # empty => dry run (print only)

# --- START: HUGGING FACE DOWNLOAD SECTION ---
HF_TOKEN = os.getenv("HF_TOKEN")
REPO_ID = "my-ml-projects/MobileNetSSD"

if not HF_TOKEN:
    print("[ERROR] HF_TOKEN environment variable not set.")
    exit(1)

print(f"[INFO] Downloading model files from {REPO_ID}...")
try:
    prototxt_path = hf_hub_download(
        repo_id=REPO_ID,
        filename="MobileNetSSD_deploy.prototxt.txt",
        token=HF_TOKEN
    )
    model_path = hf_hub_download(
        repo_id=REPO_ID,
        filename="MobileNetSSD_deploy.caffemodel",
        token=HF_TOKEN
    )
    print("[INFO] Model files downloaded successfully.")
except Exception as e:
    print(f"[ERROR] Failed to download models: {e}")
    exit(1)
# --- END: HUGGING FACE DOWNLOAD SECTION ---

# initialize the list of class labels MobileNet SSD was trained to
CLASSES = ["background", "aeroplane", "bicycle", "bird", "boat",
    "bottle", "bus", "car", "cat", "chair", "cow", "diningtable",
    "dog", "horse", "motorbike", "person", "pottedplant", "sheep",
    "sofa", "train", "tvmonitor"]
COLORS = np.random.uniform(0, 255, size=(len(CLASSES), 3))
PERSON_IDX = CLASSES.index("person")

# load our serialized model
print("[INFO] loading model...")
net = cv2.dnn.readNetFromCaffe(prototxt_path, model_path)

# connect to RTSP stream
print(f"[INFO] connecting to network video stream... {INPUT_RTSP}")
RTSP_URL = INPUT_RTSP
vs = VideoStream(src=RTSP_URL).start()
time.sleep(2.0)

# FPS counter
fps = FPS().start()

last_sent = 0.0  # debounce timer for events

while True:
    frame = vs.read()
    if frame is None:
        print("[WARN] Could not read frame from video stream. Exiting.")
        break

    frame = imutils.resize(frame, width=400)
    (h, w) = frame.shape[:2]
    blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)),
                                 0.007843, (300, 300), 127.5)

    net.setInput(blob)
    detections = net.forward()

    # collect person detections above PERSON_THRESHOLD
    persons = []

    for i in np.arange(0, detections.shape[2]):
        confidence = float(detections[0, 0, i, 2])
        idx = int(detections[0, 0, i, 1])

        # record persons (for event logic)
        if idx == PERSON_IDX and confidence >= PERSON_THRESHOLD:
            persons.append(confidence)

        # draw boxes with a lower visual threshold (0.2) for preview
        if confidence > 0.2:
            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            (startX, startY, endX, endY) = box.astype("int")
            label = "{}: {:.2f}%".format(CLASSES[idx], confidence * 100)
            cv2.rectangle(frame, (startX, startY), (endX, endY), COLORS[idx], 2)
            y = startY - 15 if startY - 15 > 15 else startY + 15
            cv2.putText(frame, label, (startX, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLORS[idx], 2)

    # event logic: if any person(s) above threshold, debounce and send/print
    if persons:
        now = time.time()
        if now - last_sent >= EVENT_COOLDOWN_SEC:
            event = {
                "device_id": DEVICE_ID,
                "ts": int(now * 1000),
                "event": "person_detected",
                "person_count": len(persons),
                "top_confidence": round(max(persons), 4),
                "model": MODEL,
                "image_tag": IMAGE_TAG
            }
            if CLOUD_API_BASE:
                try:
                    import requests  # lazy import; ok if not installed during dry run
                    url = CLOUD_API_BASE.rstrip("/") + "/events"
                    requests.post(url, json=event, timeout=5)
                    print("[EVENT->CLOUD]", event)
                except Exception as e:
                    print("[EVENT SEND FAILED]", e, event)
            else:
                print("[EVENT WOULD SEND]", event)
            last_sent = now

    # update FPS and show frame
    fps.update()
    cv2.imshow("Frame", frame)
    key = cv2.waitKey(1) & 0xFF
    if key == ord("q"):
        break

# cleanup
fps.stop()
print(f"[INFO] elapsed time: {fps.elapsed():.2f}")
print(f"[INFO] approx. FPS: {fps.fps():.2f}")

cv2.destroyAllWindows()
vs.stop()
