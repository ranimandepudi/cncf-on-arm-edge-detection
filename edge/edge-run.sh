#!/usr/bin/env bash
set -euo pipefail

# Auto-load variables if the file exists
if [ -f "./variables.sh" ]; then
  set -a                  # auto-export all variables read
  . ./variables.sh
  set +a
fi

# ---------- EDITABLE DEFAULTS ----------
IMAGE="${IMAGE:-ranman01/obj-det:latest}"           # for now: Docker Hub
CLOUD_API_BASE="${CLOUD_API_BASE:-http://34.228.231.124:8080}"
DEVICE_ID="${DEVICE_ID:-mac-m4-01}"
PERSON_THRESHOLD="${PERSON_THRESHOLD:-0.60}"
EVENT_COOLDOWN_SEC="${EVENT_COOLDOWN_SEC:-3}"
MODEL="${MODEL:-mobilenet-ssd}"
DISPLAY="${DISPLAY:-}"                               # set from your environment
HF_TOKEN="${HF_TOKEN:-}"                             # set from your environment

# ---------- derive registry host from IMAGE ----------
# If first path part looks like a registry (has '.' or ':' or equals 'localhost'),
# use it. Otherwise default to Docker Hub 'docker.io'.
first_part="${IMAGE%%/*}"
if [[ "$first_part" == *.* || "$first_part" == *:* || "$first_part" == "localhost" ]]; then
  REGISTRY="$first_part"
else
  REGISTRY="docker.io"
fi

ARCH="$(uname -m)"

# ---------- build OPA input ----------
cat > /tmp/edge-input.json <<EOF
{
  "image": {
    "name": "${IMAGE}",
    "registry": "${REGISTRY}"
  },
  "host": {
    "arch": "${ARCH}"
  },
  "env": {
    "CLOUD_API_BASE": "${CLOUD_API_BASE}"
  }
}
EOF

# ---------- evaluate policies ----------
POL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/policies" && pwd)"
ALLOW="$(opa eval -f raw -d "${POL_DIR}" -i /tmp/edge-input.json 'data.edge.allow' || echo false)"

if [[ "${ALLOW}" != "true" ]]; then
  echo "Policy check failed. Reasons:"
  opa eval -f pretty -d "${POL_DIR}" -i /tmp/edge-input.json 'data.edge.deny'
  echo "Contact admin."
  exit 1
fi

echo "Policy check passed for:"
echo "   IMAGE=${IMAGE}"
echo "   REGISTRY=${REGISTRY}"
echo "   ARCH=${ARCH}"
echo "   CLOUD_API_BASE=${CLOUD_API_BASE}"

# ---------- sanity: required envs ----------
: "${HF_TOKEN:?HF_TOKEN required (HuggingFace token)}"
: "${DISPLAY:?DISPLAY required for XQuartz (e.g. 192.168.1.141:0)}"

# ---------- run the container ----------
docker run -it --rm \
  -e HF_TOKEN="${HF_TOKEN}" \
  -e DISPLAY="${DISPLAY}" \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -e INPUT_RTSP="rtsp://host.docker.internal:8554/stream" \
  -e PERSON_THRESHOLD="${PERSON_THRESHOLD}" \
  -e EVENT_COOLDOWN_SEC="${EVENT_COOLDOWN_SEC}" \
  -e DEVICE_ID="${DEVICE_ID}" \
  -e MODEL="${MODEL}" \
  -e IMAGE_TAG="${IMAGE}" \
  -e CLOUD_API_BASE="${CLOUD_API_BASE}" \
  "${IMAGE}"
