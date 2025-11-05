cat > edge/variables.example.sh <<'EOF'
# Copy this file to variables.sh and fill in your own values.
# Do NOT commit variables.sh.

# Hugging Face token for model downloads
export HF_TOKEN="hf_xxxxxxxx"

# XQuartz display (Mac IP address + :0)
export DISPLAY="$(ipconfig getifaddr en0):0"

# Cloud API base (your FastAPI URL)
export CLOUD_API_BASE="http://<your-ec2-ip>:8080"

# Image to run (Harbor recommended)
# export IMAGE="harbor.mycompany.com/edge/obj-det:latest"
# For testing you can use Docker Hub:
export IMAGE="ranman01/obj-det:latest"

# Optional overrides
export DEVICE_ID="mac-m4-01"
export PERSON_THRESHOLD="0.60"
export EVENT_COOLDOWN_SEC="3"
export MODEL="mobilenet-ssd"
EOF
