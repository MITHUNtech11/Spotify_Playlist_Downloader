import os
import json
import asyncio
from typing import List, Optional, Union
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.config import get_settings, update_settings
from app.models.track import TrackItem
from app.models.config import AppConfig, UpdateConfigRequest
from app.models.usb import UsbDrive, UsbSyncSummary
from app.services.spotify_service import resolve_input_batch
from app.services.downloader_service import downloader_service
from app.services.event_service import event_bus
from app.services.usb_service import list_usb_drives, analyze_usb_sync, sync_to_usb

app = FastAPI(
    title="Spotify Downloader Pro",
    description="High-performance Spotify downloader and USB synchronization web product",
    version="1.0.0"
)

# Enable CORS for frontend local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ResolveRequest(BaseModel):
    urls: Optional[List[str]] = None
    input: Optional[str] = None

class StartDownloadRequest(BaseModel):
    track_ids: Optional[List[str]] = None
    output_folder: Optional[str] = None

class UsbActionRequest(BaseModel):
    drive_letter: str
    target_subfolder: Optional[str] = None

# ============================================================================
# CONFIGURATION
# ============================================================================

@app.get("/api/config", response_model=AppConfig)
async def get_configuration():
    return get_settings()

@app.post("/api/config", response_model=AppConfig)
async def update_configuration(req: UpdateConfigRequest):
    settings = update_settings(download_folder=req.download_folder, max_threads=req.max_threads)
    if req.max_threads is not None:
        downloader_service.max_workers = req.max_threads
    return settings

# ============================================================================
# RESOLVE SPOTIFY LINKS
# ============================================================================

@app.post("/api/resolve", response_model=List[TrackItem])
async def resolve_urls(req: ResolveRequest):
    settings = get_settings()
    raw = req.urls if req.urls is not None else (req.input or "")
    tracks = resolve_input_batch(raw, download_folder=settings.download_folder)
    downloader_service.add_to_queue(tracks)
    return tracks

# ============================================================================
# DOWNLOAD QUEUE
# ============================================================================

@app.get("/api/downloads/queue", response_model=List[TrackItem])
async def get_queue():
    return downloader_service.get_all_tracks()

@app.post("/api/downloads/start")
async def start_downloads(req: Optional[StartDownloadRequest] = None):
    track_ids = req.track_ids if req else None
    output_folder = req.output_folder if req else None
    downloader_service.start_downloads(track_ids=track_ids, output_folder=output_folder)
    return {"status": "started", "target_tracks": track_ids or "all"}

@app.post("/api/downloads/cancel/{track_id}")
async def cancel_download(track_id: str):
    downloader_service.cancel(track_id)
    return {"status": "cancelled", "track_id": track_id}

# ============================================================================
# REAL-TIME SSE EVENT STREAM
# ============================================================================

@app.get("/api/events")
async def stream_events(request: Request):
    """Server-Sent Events endpoint pushing real-time download and sync progress."""
    async def event_generator():
        queue = event_bus.subscribe()
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=20.0)
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    # Ping to keep connection alive
                    yield ": ping\n\n"
        finally:
            event_bus.unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

# ============================================================================
# USB PEN DRIVE SYNC
# ============================================================================

@app.get("/api/usb/drives", response_model=List[UsbDrive])
async def get_usb_drives():
    return list_usb_drives()

@app.post("/api/usb/analyze", response_model=UsbSyncSummary)
async def analyze_usb(req: UsbActionRequest):
    settings = get_settings()
    dest = req.drive_letter
    if req.target_subfolder:
        dest = os.path.join(req.drive_letter, req.target_subfolder.lstrip("\\/"))
    return analyze_usb_sync(source_folder=settings.download_folder, destination_folder=dest)

@app.post("/api/usb/sync")
async def start_usb_sync(req: UsbActionRequest, background_tasks: BackgroundTasks):
    settings = get_settings()
    dest = req.drive_letter
    if req.target_subfolder:
        dest = os.path.join(req.drive_letter, req.target_subfolder.lstrip("\\/"))

    background_tasks.add_task(sync_to_usb, settings.download_folder, dest)
    return {"status": "sync_started", "destination": dest}

# ============================================================================
# STATIC FRONTEND MOUNTING (FOR PRODUCTION / SINGLE-COMMAND APP)
# ============================================================================

frontend_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
