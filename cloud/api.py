# file: api.py
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from collections import deque, defaultdict
from fastapi.staticfiles import StaticFiles

import json, os

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
STORE = defaultdict(lambda: deque(maxlen=500))  # device_id -> deque of events (newest last)

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
    STORE[device].append(body)              # append newest at the end
    return JSONResponse({"ok": True})

# Frontend -> Cloud: fetch recent events (newest-first)
@app.get("/events")
def get_events(device_id: str, limit: int = 50):
    items = list(STORE[device_id])[-limit:] # newest at end
    items.reverse()                         # return newest-first
    return JSONResponse(items)