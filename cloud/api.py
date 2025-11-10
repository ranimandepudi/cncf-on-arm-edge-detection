# file: api.py
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from collections import deque, defaultdict
from fastapi.staticfiles import StaticFiles

import json, os, redis
from redis.commands.json.path import Path

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve your frontend
@app.get("/")
def index():
    # index.html must be in the same folder as this api.py
    return FileResponse("index.html")

# Edge -> Cloud: receive text-only events
@app.post("/events")
async def post_events(req: Request):
    body = await req.json()
    device = body.get("device_id", "unknown")
    r = redis.Redis(host='redis', port=6379, decode_responses=True, password=os.getenv("REDIS_PASSWORD", ""))
    events = r.json().get(device, ".events")
    if len(events) == 0:
        r.json().set(device, Path.root_path(), {"events": []})
    r.json().arrinsert(device, Path('.events'), 0, body)
    return JSONResponse({"ok": True})

# Frontend -> Cloud: fetch recent events (newest-first)
@app.get("/eventsRead")
def get_events(device_id: str, limit: int = 50):
    events = r.json().get(device, ".events")
    return JSONResponse(events)

print(f"Git Sha: {os.getenv('GIT_COMMIT', 'main')}")
print(f"Version: {os.getenv('VERSION', 'main')}")
