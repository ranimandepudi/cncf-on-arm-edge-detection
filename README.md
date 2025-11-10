## **CNCF on Arm: Edge-Cloud Person Detection (Harbor-ready + OPA)**

<img width="1486" height="730" alt="image" src="https://github.com/user-attachments/assets/d55c3797-16d5-4580-a0e5-db9a29286642" />

**Goal.** Run a privacy-friendly demo on `arm64` where an edge device detects people (no images leave the device — only JSON events) and a cloud **FastAPI** dashboard shows detections in real time.  
Container startup on the edge is gated by **OPA** policies (allowed registry, CPU arch, approved cloud API URL).  
**Harbor-ready:** the image can live on **Harbor** (preferred) or **Docker Hub** for convenience. The policy is already structured to switch to Harbor by changing one variable and the allow-list.

---

## 1) Architecture (what’s happening)

- **Camera - RTSP (edge)**  
  `ffmpeg` captures your laptop webcam and publishes **H.264** video to a local RTSP server (**MediaMTX**).

- **Detector (edge container)**  
  A Docker container reads the RTSP stream, runs **MobileNet-SSD** with **OpenCV DNN**, and emits **JSON** whenever a person is detected.

- **OPA policy (edge)**  
  Before the container starts, OPA checks:
  - the image registry is approved (Hub/Harbor)
  - the host arch is `arm64`/`aarch64`
  - the cloud API base URL is allow-listed

- **Cloud API + UI (cloud)**  
  A FastAPI app exposes:
  - `POST /events` (edge sends JSON events)
  - `GET /events?device_id=...&limit=...` (dashboard polls 1/s)
  - `GET /` serves a sleek HTML dashboard

---


**2) Repository layout**
   
cncf-on-arm-edge-detection/
├─ cloud/                       # Cloud FastAPI + dashboard (run on EC2 or any host)
│  ├─ api.py
│  ├─ index.html
│  └─ static/
│     └─ arm.png
├─ edge/                        # Edge runtime (run on your arm64 laptop/box)
│  ├─ Dockerfile
│  ├─ requirements.txt
│  ├─ real_time_object_detection.py
│  ├─ mediamtx.yml              # MediaMTX RTSP server config
│  ├─ edge-run.sh               # OPA-gated container runner
│  ├─ variables.example.sh      # copy to variables.sh and edit
│  └─ policies/
│     ├─ policy.rego
│     └─ data.json
└─ README.md

---

## 3) Prerequisites

### Cloud (Ubuntu 22.04+ recommended)
- Python **3.10+**
- Inbound **TCP 8080** opened in the security group (from your public IP or `0.0.0.0/0` while testing)
- Git

### Edge (Apple Silicon macOS or any ARM64 Linux)
- Docker (**Docker Desktop** or **Colima**; *Docker Desktop is simplest*)
- **MediaMTX** (RTSP server) and **FFmpeg**
- **OPA** binary
- (macOS) **XQuartz** (for OpenCV preview window)
  - XQuartz ▸ Preferences ▸ Security ▸ **Allow connections from network clients**
  - Then: `xhost + $(ipconfig getifaddr en0)`
- **Hugging Face token** (read-only) to pull the MobileNet-SSD model

> **Headless option:** If you don’t want the OpenCV preview window, you can run headless (see **Troubleshooting**).

---

## 4) Cloud setup (FastAPI + dashboard)

Run these on your EC2 (or any Linux host):

```bash
# 1) clone
git clone https://github.com/ranimandepudi/cncf-on-arm-edge-detection.git
cd cncf-on-arm-edge-detection/cloud

# 2) python venv
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install fastapi uvicorn redis

# 3) run (foreground)
uvicorn api:app --host 0.0.0.0 --port 8080

# (Optional, run in background)
# nohup uvicorn api:app --host 0.0.0.0 --port 8080 > server.log 2>&1 & disown
```

Open the dashboard in your browser:
http://<CLOUD_PUBLIC_IP>:8080/
You should see CONNECTED and an empty timeline.


**5) Edge setup (stream + detector + OPA)**
Run these on your arm64 machine (Apple Silicon mac is perfect).

5.1 Install tools

macOS (Homebrew):
```
brew install ffmpeg
brew install --cask xquartz
brew install openpolicyagent
```
# MediaMTX: download a release tarball from mediamtx and place the 'mediamtx' binary on PATH,
# or `brew install mediamtx` if available in your tap.

Start XQuartz, then allow network clients and your local IP:
```
xhost + $(ipconfig getifaddr en0)
```
Docker Desktop: install and make sure docker ps works.

5.2 Stream your webcam to RTSP

In one terminal (from edge/):
```
# Start RTSP server
mediamtx mediamtx.yml
```
In a second terminal:
```
#Publish your webcam to RTSP (macOS '0' picks default camera)
ffmpeg -f avfoundation -pix_fmt uyvy422 -framerate 30 -video_size 640x480 -i "0" \
  -c:v libx264 -preset ultrafast -tune zerolatency \
  -f rtsp rtsp://localhost:8554/stream
```
5.3 Configure edge variables + run detector (OPA-gated)

In a third terminal (still inside edge/):
```
#Copy example and edit
cp variables.example.sh variables.sh
 Edit variables.sh:
   - HF_TOKEN="hf_..."              (your Hugging Face token)
   - CLOUD_API_BASE="http://<CLOUD_PUBLIC_IP>:8080"
   - IMAGE="ranichowdary/obj-det:latest"   # change to Harbor later
   - DISPLAY="$(ipconfig getifaddr en0):0" # if you want the preview window

#Load variables
source ./variables.sh

#Run with policy enforcement
./edge-run.sh
```
What happens:
	•	edge-run.sh builds OPA input and evaluates policies/policy.rego.
	•	If allowed, it starts docker run ... real_time_object_detection.py.
	•	The detector downloads model weights (via Hugging Face token), reads RTSP, and posts JSON events to CLOUD_API_BASE.

Switch back to the browser — you should see events flowing in the timeline, and the architecture “cards” lighting up.


**6) Harbor (optional-Docker Hub)**
For Harbor, you can setup locally and push the image.

To use Harbor:
	1.	Build and push the image to your Harbor:
```
docker build -t harbor.arm.example.com/yourproj/obj-det:latest edge/
docker login harbor.arm.example.com
docker push harbor.arm.example.com/yourproj/obj-det:latest
```
	2.	Update the edge config:
```
#variables.sh
export IMAGE="harbor.arm.example.com/yourproj/obj-det:latest"
```
	3.	Ensure data.json includes your Harbor hostname in allowed_registries.
	4.	Re-run ./edge-run.sh — OPA will allow only if the registry is approved.
  
Now, if the image is pulled from Docker Hub:
	•	edge/variables.sh
export IMAGE="ranichowdary/obj-det:latest"

	•	edge/policies/data.json
{
  "allowed_registries": ["docker.io", "harbor.arm.example.com"],
  "allowed_cloud_targets": ["http://<CLOUD_PUBLIC_IP>:8080"]
}
  
**7) What the key files do**

edge/edge-run.sh
	•	Loads environment from variables.sh.
	•	Derives the registry from IMAGE and composes an OPA input (/tmp/edge-input.json).
	•	Evaluates OPA:
  data.edge.allow
  data.edge.deny

  On allow > docker run with the right env:
	•	HF_TOKEN, DISPLAY, INPUT_RTSP, CLOUD_API_BASE, etc.

edge/policies/policy.rego
```
package edge
default allow := false
allowed_arches := {"arm64", "aarch64"}

#1) image registry must be allow-listed
deny contains msg if {
  not approved_registry
  msg := sprintf("Image registry %q is not approved. Allowed: %v",
                 [input.image.registry, data.allowed_registries])
}
approved_registry if { data.allowed_registries[_] == input.image.registry }

#2) host arch must be arm64/aarch64
deny contains msg if {
  not allowed_arches[input.host.arch]
  msg := sprintf("Host arch %q not allowed. Require arm64/aarch64.",
                 [input.host.arch])
}

#3) cloud API base must be allow-listed
deny contains msg if {
  not approved_cloud
  msg := sprintf("CLOUD_API_BASE %q is not approved. Allowed: %v",
                 [input.env.CLOUD_API_BASE, data.allowed_cloud_targets])
}
approved_cloud if { data.allowed_cloud_targets[_] == input.env.CLOUD_API_BASE }

allow if { count(deny) == 0 }
```

edge/real_time_object_detection.py
	•	Downloads MobileNet-SSD prototxt + caffemodel from Hugging Face (needs HF_TOKEN).
	•	Reads RTSP frames, runs inference; if a person is detected above PERSON_THRESHOLD, sends:
  ```
  {
  "device_id": "...",
  "ts": 1699999999999,
  "event": "person_detected",
  "person_count": 1,
  "top_confidence": 0.98,
  "model": "mobilenet-ssd",
  "image_tag": "..."
}
```
to POST /events on the cloud.
cloud/api.py
	•	POST /events — writes an in-memory ring buffer keyed by device_id.
	•	GET /events?device_id=&limit= — returns latest events (newest first).
	•	GET / — serves index.html.

**8) Quick verification checklist**
```
	Cloud:
	•	uvicorn api:app --host 0.0.0.0 --port 8080
	•	Security Group inbound 8080 allowed from your IP.
	•	curl http://127.0.0.1:8080/ returns HTML.
	•	Edge:
	•	docker ps works (Docker Desktop running).
	•	mediamtx mediamtx.yml is running.
	•	ffmpeg ... rtsp://localhost:8554/stream prints FPS (no errors).
	•	xhost + $(ipconfig getifaddr en0) was run (if you want preview window).
	•	HF_TOKEN present; variables.sh loaded; ./edge-run.sh shows “Policy check passed”.
```
**9) Troubleshooting**

Can't reach dashboard from laptop
	•	Open inbound security group rule for port 8080 (from your IP).
	•	On the instance:
ss -ltnp | grep 8080 should show uvicorn listening on 0.0.0.0:8080.

Detector exits with Qt/XCB display error (macOS)
	•	XQuartz not open or permission missing.
Start XQuartz - Preferences - Security - Allow connections from network clients
Then in a terminal:

```
xhost + $(ipconfig getifaddr en0)
export DISPLAY="$(ipconfig getifaddr en0):0"
```

OPA denies
	•	./edge-run.sh prints reasons. Check edge/policies/data.json:
	•	allowed_registries contains your IMAGE registry host,
	•	allowed_cloud_targets matches your CLOUD_API_BASE.

Docker context confusion (Colima vs Desktop)
	•	Prefer Docker Desktop for simplicity:
  ```
docker context ls
docker ps
```
If Cannot connect to the Docker daemon, open Docker Desktop.

**10) Stop / clean up**

Cloud
```
#foreground run: Ctrl+C
#background run:
pkill -f 'uvicorn.*api:app' || true
```
Edge
```
#Stop detector run: Ctrl+C
#Stop ffmpeg and mediamtx terminals: Ctrl+C in each
```

**Next steps**
	•	Switch IMAGE to your Harbor registry and update allowed_registries.(once harbor on arm is official)
	•	Add more OPA checks (e.g: required envs, minimum version tag).
	•	Package the cloud app in a container and deploy behind a small reverse proxy.


**Credits**
	•	Detector: OpenCV DNN (MobileNet-SSD)
	•	RTSP server: MediaMTX
	•	Policy: Open Policy Agent (OPA)
	•	UI/API: FastAPI + vanilla JS





