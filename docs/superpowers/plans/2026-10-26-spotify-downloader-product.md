# Spotify Downloader Pro Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the Spotify playlist downloader CLI into an interactive, user-friendly local web application with real-time download streaming, ID3 tagging, and USB pen drive sync.

**Architecture:** Client-Server architecture running locally. A modern React 18 + Vite + Tailwind CSS frontend communicates with an asynchronous FastAPI Python backend via REST APIs and Server-Sent Events (SSE) for zero-lag live download progress.

**Tech Stack:** Python 3.8+, FastAPI, Uvicorn, Pydantic v2, yt-dlp, Mutagen, psutil, React 18, TypeScript, Vite, Tailwind CSS, Lucide React.

**Spec:** `docs/superpowers/specs/2026-10-26-spotify-downloader-product-design.md`

## Global Constraints

- Python compatibility: Python 3.8+ (Windows console UTF-8 safety enforced).
- Frontend framework: React 18 with TypeScript and Vite.
- Styling: Tailwind CSS with dark-mode zinc/emerald palette.
- Real-time transport: Server-Sent Events (SSE) via FastAPI `StreamingResponse`.
- Default download destination: `./Dad_Car_Songs` (configurable via `.env` and `/api/config`).
- Download rate-limit safety: Max concurrent download worker threads defaulted to 3.
- USB deduplication: Must use SHA-256 content hashing to avoid duplicate writes.

## Review Focus

1. **Invalid or malformed Spotify URLs pasted into the input**: Must return a 400 Bad Request with a clear human-readable error without crashing the server or discarding valid URLs in a batch.
2. **Missing FFmpeg on user machine**: App must start successfully, detect that FFmpeg is missing, and broadcast `ffmpeg_available: false` with installation instructions.
3. **Aborted/Cancelled download while in progress**: Must immediately cancel the `yt-dlp` thread and purge any leftover `.part` or `.ytdl` files from the output folder.
4. **USB Drive disconnected during sync analysis**: Must catch `FileNotFoundError` or OS I/O error and report a graceful error banner rather than a 500 crash.
5. **YouTube HTTP 429 Rate Limiting**: Downloader must retry with exponential backoff and transition track status to `retrying` with informative message.

---

### Task 1: Project Setup, Backend Configuration & Pydantic Models

**Files:**
- Modify: `requirements.txt`
- Create: `app/__init__.py`
- Create: `app/config.py`
- Create: `app/models/__init__.py`
- Create: `app/models/track.py`
- Create: `app/models/config.py`
- Create: `app/models/usb.py`
- Test: `tests/test_models_and_config.py`

**Interfaces:**
- Produces:
  - `TrackItem(id: str, title: str, artist: str, album: Optional[str], thumbnail_url: Optional[str], spotify_url: str, status: str, progress: float, speed: Optional[str], eta: Optional[str], error_message: Optional[str], already_downloaded: bool)`
  - `AppConfig(download_folder: str, max_threads: int, ffmpeg_available: bool, ffmpeg_path: Optional[str])`
  - `UsbDrive(drive_letter: str, volume_name: str, total_gb: float, free_gb: float)`
  - `UsbSyncSummary(source_folder: str, drive_letter: str, total_source_tracks: int, already_synced_tracks: int, new_tracks_to_copy: int, estimated_size_mb: float, enough_space: bool)`

- [ ] **Step 1: Write failing test for config and Pydantic models**
```python
# tests/test_models_and_config.py
from app.models.track import TrackItem
from app.models.config import AppConfig
from app.models.usb import UsbDrive, UsbSyncSummary
from app.config import get_settings

def test_track_item_defaults():
    track = TrackItem(id="123", title="Song", artist="Artist", spotify_url="https://open.spotify.com/track/123")
    assert track.status == "queued"
    assert track.progress == 0.0
    assert track.already_downloaded is False

def test_settings_initialization():
    settings = get_settings()
    assert settings.download_folder != ""
    assert settings.max_threads >= 1
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/test_models_and_config.py -v`
Expected: FAIL (No module named `app`)

- [ ] **Step 3: Update `requirements.txt` and install dependencies**
Add `fastapi>=0.110.0`, `uvicorn[standard]>=0.28.0`, `pydantic>=2.6.0`, `psutil>=5.9.0`, `pytest>=8.0.0`, `httpx>=0.27.0`.

- [ ] **Step 4: Implement models and configuration**
Create `app/models/track.py`, `app/models/config.py`, `app/models/usb.py`, and `app/config.py` using `pydantic_settings.BaseSettings` or `pydantic.BaseModel` with FFmpeg detection logic from `playlist_downloader_combined.py`.

- [ ] **Step 5: Run tests to verify they pass**
Run: `pytest tests/test_models_and_config.py -v`
Expected: PASS

- [ ] **Step 6: Commit**
```bash
git add requirements.txt app/ tests/test_models_and_config.py
git commit -m "feat(backend): add models, configuration, and ffmpeg detector"
```

---

### Task 2: Spotify Resolver Service (Track, Playlist, Album extraction)

**Files:**
- Create: `app/services/__init__.py`
- Create: `app/services/spotify_service.py`
- Test: `tests/test_spotify_service.py`

**Interfaces:**
- Consumes: `app.models.track.TrackItem`
- Produces:
  - `parse_spotify_url(url: str) -> Tuple[str, str]` (type: 'track'|'playlist'|'album', id: str)
  - `resolve_track_metadata(track_id_or_url: str) -> Optional[TrackItem]`
  - `resolve_playlist_tracks(playlist_id_or_url: str) -> List[TrackItem]`
  - `resolve_album_tracks(album_id_or_url: str) -> List[TrackItem]`
  - `resolve_input_batch(raw_input: Union[str, List[str]], download_folder: str) -> List[TrackItem]`

- [ ] **Step 1: Write failing tests for Spotify URL parsing and resolution**
```python
# tests/test_spotify_service.py
import pytest
from app.services.spotify_service import parse_spotify_url, resolve_input_batch

def test_parse_spotify_urls():
    assert parse_spotify_url("https://open.spotify.com/track/2109dBho14Lqh2wr8goqAP") == ("track", "2109dBho14Lqh2wr8goqAP")
    assert parse_spotify_url("https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M") == ("playlist", "37i9dQZF1DXcBWIGoYBM5M")
    assert parse_spotify_url("https://open.spotify.com/album/4m2880jivSbbyEGAKfITCa") == ("album", "4m2880jivSbbyEGAKfITCa")
    assert parse_spotify_url("invalid-url") == (None, None)

def test_duplicate_check_flag(tmp_path):
    # simulate existing mp3 file in folder
    (tmp_path / "Artist - Song.mp3").write_text("dummy")
    # check that resolve_input_batch flags already_downloaded == True
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/test_spotify_service.py -v`
Expected: FAIL (No module named `app.services.spotify_service`)

- [ ] **Step 3: Implement `app/services/spotify_service.py`**
Port and enhance the oEmbed resolver, HTML fallback scraping, and playlist/album track link extraction from `playlist_downloader_combined.py`. Include duplicate checking against normalized filenames in `download_folder`.

- [ ] **Step 4: Run tests to verify they pass**
Run: `pytest tests/test_spotify_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add app/services/spotify_service.py tests/test_spotify_service.py
git commit -m "feat(backend): add spotify metadata and playlist resolution service"
```

---

### Task 3: Download Service with yt-dlp, Mutagen ID3 Tagger & SSE Event Bus

**Files:**
- Create: `app/services/event_service.py`
- Create: `app/services/tagger_service.py`
- Create: `app/services/downloader_service.py`
- Test: `tests/test_downloader_service.py`

**Interfaces:**
- Consumes: `TrackItem`, `AppConfig`
- Produces:
  - `event_bus.publish(event: dict)` & `event_bus.subscribe() -> AsyncGenerator[dict, None]`
  - `embed_id3_metadata(file_path: str, title: str, artist: str, album: Optional[str], cover_url: Optional[str]) -> bool`
  - `DownloaderService.enqueue(tracks: List[TrackItem], output_folder: str)`
  - `DownloaderService.cancel(track_id: str)`
  - `DownloaderService.get_status(track_id: str) -> Optional[TrackItem]`

- [ ] **Step 1: Write failing tests for event bus and tagger service**
```python
# tests/test_downloader_service.py
import pytest
import asyncio
from app.services.event_service import event_bus
from app.services.tagger_service import embed_id3_metadata

@pytest.mark.asyncio
async def test_event_bus_publish_subscribe():
    queue = event_bus.subscribe()
    event_bus.publish({"type": "test", "data": 123})
    event = await asyncio.wait_for(queue.get(), timeout=1.0)
    assert event["type"] == "test"
    event_bus.unsubscribe(queue)
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/test_downloader_service.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `event_service.py`, `tagger_service.py`, and `downloader_service.py`**
- `event_service.py`: Thread-safe broadcast bus supporting SSE listeners.
- `tagger_service.py`: Mutagen ID3 tagger embedding title, artist, album, and high-res cover artwork.
- `downloader_service.py`: `ThreadPoolExecutor` worker manager with `yt-dlp` hook broadcasting progress (`percent`, `speed`, `eta`) to `event_bus`. Handles cancellation and cleanup of `.part` files.

- [ ] **Step 4: Run tests to verify they pass**
Run: `pytest tests/test_downloader_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add app/services/event_service.py app/services/tagger_service.py app/services/downloader_service.py tests/test_downloader_service.py
git commit -m "feat(backend): add downloader service with yt-dlp, mutagen tagging, and sse event bus"
```

---

### Task 4: USB Pen Drive Detection & SHA-256 Deduplicated Sync Service

**Files:**
- Create: `app/services/usb_service.py`
- Test: `tests/test_usb_service.py`

**Interfaces:**
- Consumes: `UsbDrive`, `UsbSyncSummary`
- Produces:
  - `list_usb_drives() -> List[UsbDrive]`
  - `compute_file_hash(filepath: str) -> str` (SHA-256)
  - `analyze_usb_sync(source_folder: str, drive_letter: str) -> UsbSyncSummary`
  - `sync_to_usb(source_folder: str, drive_letter: str) -> AsyncGenerator[dict, None]`

- [ ] **Step 1: Write failing tests for hash calculation and sync analysis**
```python
# tests/test_usb_service.py
import pytest
from app.services.usb_service import compute_file_hash, analyze_usb_sync

def test_compute_file_hash(tmp_path):
    test_file = tmp_path / "song.mp3"
    test_file.write_bytes(b"sample audio content")
    h1 = compute_file_hash(str(test_file))
    assert len(h1) == 64  # SHA-256 hex string

def test_analyze_usb_sync(tmp_path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir(); dst.mkdir()
    (src / "track1.mp3").write_bytes(b"content 1")
    (dst / "track1.mp3").write_bytes(b"content 1")
    summary = analyze_usb_sync(str(src), str(dst))
    assert summary.total_source_tracks == 1
    assert summary.already_synced_tracks == 1
    assert summary.new_tracks_to_copy == 0
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/test_usb_service.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `app/services/usb_service.py`**
Port logic from `copy_to_pendrive.py` into a clean modular service using `psutil.disk_partitions` for Windows drive detection, SHA-256 hash comparison, and progress-reporting copy logic.

- [ ] **Step 4: Run tests to verify they pass**
Run: `pytest tests/test_usb_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add app/services/usb_service.py tests/test_usb_service.py
git commit -m "feat(backend): add usb drive detection and sha256 sync service"
```

---

### Task 5: FastAPI Application & REST / SSE Endpoints

**Files:**
- Create: `app/main.py`
- Test: `tests/test_api_routes.py`

**Interfaces:**
- Produces:
  - `POST /api/resolve`
  - `POST /api/downloads/start`
  - `POST /api/downloads/cancel/{track_id}`
  - `GET /api/events` (SSE streaming)
  - `GET /api/config` & `POST /api/config`
  - `GET /api/usb/drives`
  - `POST /api/usb/analyze`
  - `POST /api/usb/sync`

- [ ] **Step 1: Write failing tests for API endpoints**
```python
# tests/test_api_routes.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_get_config():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    assert "download_folder" in data
    assert "ffmpeg_available" in data
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/test_api_routes.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `app/main.py`**
Configure FastAPI with CORS, instantiate router endpoints, connect `event_service` SSE `StreamingResponse`, wire USB and downloader services, and mount static files if the frontend build exists.

- [ ] **Step 4: Run tests to verify they pass**
Run: `pytest tests/test_api_routes.py -v`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add app/main.py tests/test_api_routes.py
git commit -m "feat(backend): implement fastapi rest and sse endpoints"
```

---

### Task 6: Frontend Scaffolding with React, Vite, Tailwind & Lucide

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tailwind.config.js`
- Create: `frontend/postcss.config.js`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/index.css`
- Create: `frontend/src/services/api.ts`
- Create: `frontend/src/services/eventSource.ts`
- Create: `frontend/src/types.ts`

**Interfaces:**
- Produces:
  - TypeScript types: `TrackItem`, `AppConfig`, `UsbDrive`, `UsbSyncSummary`
  - API Client: `resolveUrls()`, `startDownloads()`, `cancelDownload()`, `fetchConfig()`, `updateConfig()`, `fetchUsbDrives()`, `analyzeUsb()`, `syncUsb()`
  - Event Stream hook: `useEventStream()` for live updates

- [ ] **Step 1: Initialize `frontend/` package.json and configuration**
Setup dependencies: `react`, `react-dom`, `lucide-react`, `tailwindcss`, `vite`, `@vitejs/plugin-react`, `typescript`.

- [ ] **Step 2: Configure Tailwind CSS with dark theme Spotify color palette**
Define colors: `spotify-green: #1db954`, `zinc-900`, `zinc-800`, `zinc-700`.

- [ ] **Step 3: Implement API client and SSE listener in `frontend/src/services/`**
Implement typed `fetch` wrapper and `EventSource` subscriber with automatic reconnection.

- [ ] **Step 4: Verify build works**
Run: `cd frontend && npm install && npm run build`
Expected: Vite build succeeds and generates `frontend/dist/`.

- [ ] **Step 5: Commit**
```bash
git add frontend/
git commit -m "feat(frontend): scaffold react, vite, tailwind, and api service"
```

---

### Task 7: Interactive Frontend Components & Dashboard Assembly

**Files:**
- Create: `frontend/src/components/Header.tsx`
- Create: `frontend/src/components/UrlInputBar.tsx`
- Create: `frontend/src/components/DownloadQueue.tsx`
- Create: `frontend/src/components/TrackCard.tsx`
- Create: `frontend/src/components/UsbSyncModal.tsx`
- Create: `frontend/src/components/SettingsModal.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `api.ts`, `eventSource.ts`, `types.ts`
- Produces: Complete responsive SPA UI

- [ ] **Step 1: Implement `Header.tsx` & `SettingsModal.tsx`**
App title, connection status pill, download destination folder indicator, USB sync trigger button, and folder settings dialog.

- [ ] **Step 2: Implement `UrlInputBar.tsx`**
Smart input supporting single or multi-line Spotify links, "Inspect & Add" button with loading spinner, and quick badges.

- [ ] **Step 3: Implement `TrackCard.tsx` & `DownloadQueue.tsx`**
Queue statistics bar ("Download All", "Clear Completed"), song cards showing album artwork, title, artist, status badge, live progress bar, speed indicator, and cancel/retry buttons.

- [ ] **Step 4: Implement `UsbSyncModal.tsx`**
Drive selector dropdown, free space meter, SHA-256 analysis diff summary, and live copy progress bar.

- [ ] **Step 5: Wire up state and live SSE events in `App.tsx`**
Connect real-time progress events from `/api/events` directly into track state cards.

- [ ] **Step 6: Build and verify frontend compilation**
Run: `cd frontend && npm run build`
Expected: Build passes with zero errors.

- [ ] **Step 7: Commit**
```bash
git add frontend/src/
git commit -m "feat(frontend): implement dashboard components, live queue, and usb sync modal"
```

---

### Task 8: Production Single-Command Launcher & End-to-End Verification

**Files:**
- Create: `run_app.py`
- Create: `start_app.bat`
- Modify: `app/main.py` (mount `frontend/dist` as static files for single-command mode)
- Modify: `README.md`
- Test: `tests/test_e2e_launch.py`

**Interfaces:**
- Produces:
  - Single-click desktop experience: double-clicking `start_app.bat` or running `python run_app.py` starts server and opens `http://localhost:8000`.

- [ ] **Step 1: Write verification test for static assets and launcher**
Verify that `app/main.py` serves the SPA index when `frontend/dist` is built.

- [ ] **Step 2: Implement `run_app.py` & `start_app.bat`**
Script checks python virtual environment, starts `uvicorn app.main:app`, and opens default browser with `webbrowser.open("http://localhost:8000")`.

- [ ] **Step 3: Run full backend test suite**
Run: `pytest -v`
Expected: All backend unit and integration tests PASS.

- [ ] **Step 4: Update README.md with product guide and screenshots/instructions**
Document the new modern Web UI, how to launch with one click, how to paste playlists, and how to sync to USB.

- [ ] **Step 5: Commit**
```bash
git add run_app.py start_app.bat app/main.py README.md tests/
git commit -m "feat(product): add one-click launcher and update documentation"
```
