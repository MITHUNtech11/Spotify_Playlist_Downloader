# Spotify Downloader Pro - Product Design Specification

**Date:** 2026-10-26  
**Status:** Approved  
**Author:** Antigravity & User  

---

## 1. Executive Summary

This specification defines the transformation of the existing CLI-based `Spotify Playlist Downloader` into **Spotify Downloader Pro**, a modern, responsive web application running locally. The product enables users to paste Spotify track, album, and playlist links, resolves rich metadata and artwork, provides real-time per-song download progress with ID3 tagging and cover embedding, and features an integrated USB Flash Drive Sync manager using SHA-256 deduplication.

---

## 2. Goals & Non-Goals

### Goals
- **Intuitive Web UI**: Modern dark-mode Spotify-inspired interface (React 18 + Vite + Tailwind CSS + Lucide icons).
- **Full Link Support**: Automatic ingestion and track unpacking for Spotify Tracks (`/track/`), Albums (`/album/`), and Playlists (`/playlist/`), plus multi-line raw text paste.
- **Real-Time Visual Feedback**: Streaming per-track download progress, transfer speed, and ETA via Server-Sent Events (SSE).
- **High-Quality Audio & Metadata**: Automatic extraction via `yt-dlp` to MP3 format with embedded ID3 tags (Title, Artist, Album) and embedded high-res cover artwork.
- **Smart Duplicate Prevention**: Normalized title comparison against the destination library to prevent unnecessary re-downloads.
- **USB Pen Drive Sync Manager**: Auto-detection of connected flash drives on Windows, SHA-256 duplicate checking, capacity checks, and one-click sync.
- **Single-Command Launch**: Easy one-click startup script that launches the FastAPI backend and opens the web application in the default browser.

### Non-Goals
- Cloud hosting or multi-user authentication (designed as a local desktop web app for personal and car infotainment workflows).
- Real-time peer-to-peer audio streaming or Spotify DRM decryption (audio is ethically sourced and downloaded from public YouTube matches via `yt-dlp`).

---

## 3. System Architecture & Tech Stack

```
┌────────────────────────────────────────────────────────┐
│             Frontend (Browser Web UI)                  │
│       React 18 + Vite + Tailwind CSS + Lucide          │
└──────────────────────────▲─────────────────────────────┘
                           │ HTTP REST (Controls/Config)
                           │ Server-Sent Events (SSE) (Live Progress)
┌──────────────────────────▼─────────────────────────────┐
│             Backend Service (Python)                   │
│             FastAPI + Uvicorn Local Server             │
├────────────────────────────────────────────────────────┤
│ • SpotifyService: oEmbed & HTML Scraper (No Auth Req)  │
│ • DownloaderService: yt-dlp Queue + Mutagen ID3        │
│ • UsbService: Windows Drive Detector + SHA-256 Sync    │
│ • LibraryService: Existing File & Duplicate Scanner    │
└────────────────────────────────────────────────────────┘
```

### Technology Choices
- **Frontend**:
  - React 18, Vite (fast bundling and HMR), Tailwind CSS (responsive dark styling), Lucide-React (clean icons).
  - Axios or native `fetch` for REST; native `EventSource` for SSE streaming.
- **Backend**:
  - Python 3.8+ / 3.10+, FastAPI (asynchronous API framework), Uvicorn (ASGI server), Pydantic v2 (schema validation).
  - Existing core dependencies: `yt-dlp`, `requests`, `beautifulsoup4`, `mutagen`, `python-dotenv`.
- **System Utilities**:
  - `ffmpeg`: Audio conversion to MP3. Auto-detected from PATH or WinGet packages.
  - `psutil` / Windows API / PowerShell: Removable drive detection.

---

## 4. Directory Structure

```text
Playlist_Downloader/
├── app/                              # Backend Application Package
│   ├── __init__.py
│   ├── main.py                       # FastAPI entry point & routes
│   ├── config.py                     # App settings, paths, env vars
│   ├── models/                       # Pydantic data schemas
│   │   ├── __init__.py
│   │   ├── track.py
│   │   ├── config.py
│   │   └── usb.py
│   └── services/                     # Modular business logic
│       ├── __init__.py
│       ├── spotify_service.py        # Spotify oEmbed & playlist unpacking
│       ├── downloader_service.py     # yt-dlp queue & progress hooks
│       ├── tagger_service.py         # Mutagen ID3 and artwork embedder
│       ├── usb_service.py            # Windows drive detector & SHA-256 sync
│       └── event_service.py          # SSE event bus for real-time streaming
│
├── frontend/                         # Modern React Frontend
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx                   # Main Dashboard Layout
│   │   ├── components/
│   │   │   ├── Header.tsx            # App bar & status
│   │   │   ├── UrlInputBar.tsx       # Link paste & inspect
│   │   │   ├── DownloadQueue.tsx     # Active & queued track cards
│   │   │   ├── TrackCard.tsx         # Individual song item with progress
│   │   │   ├── UsbSyncModal.tsx      # Pen drive sync drawer & progress
│   │   │   └── SettingsModal.tsx     # Download folder & thread settings
│   │   └── services/
│   │       ├── api.ts                # REST client
│   │       └── eventSource.ts        # SSE stream listener
│   └── index.html
│
├── tests/                            # Automated Tests
│   ├── test_spotify_service.py
│   ├── test_downloader.py
│   ├── test_usb_service.py
│   └── test_api.py
│
├── run_app.py                        # Single-command launcher (FastAPI + browser open)
├── start_app.bat                     # Windows double-click runner
├── requirements.txt                  # Updated dependencies
└── README.md                         # Documentation
```

---

## 5. Backend Specifications & API Contracts

### Data Schemas

#### `TrackItem`
```python
class TrackItem(BaseModel):
    id: str  # Spotify ID or sanitized unique string
    title: str
    artist: str
    album: Optional[str] = None
    thumbnail_url: Optional[str] = None
    spotify_url: str
    status: str = "queued"  # queued, downloading, converting, tagging, completed, duplicate, error
    progress: float = 0.0
    speed: Optional[str] = None
    eta: Optional[str] = None
    error_message: Optional[str] = None
    already_downloaded: bool = False
```

#### `UsbDrive`
```python
class UsbDrive(BaseModel):
    drive_letter: str  # e.g. "E:\"
    volume_name: str
    total_gb: float
    free_gb: float
```

### Endpoints

1. **`POST /api/resolve`**
   - **Request**: `{ "urls": ["https://open.spotify.com/playlist/..."] }`
   - **Action**: Detects link type. Unpacks tracks if playlist or album. Extracts Title, Artist, Album, and Thumbnail URL. Compares each against the target folder to mark `already_downloaded`.
   - **Response**: `List[TrackItem]`

2. **`POST /api/downloads/start`**
   - **Request**: `{ "track_ids": ["..."] }` (or empty to start all queued)
   - **Action**: Enqueues tracks into `downloader_service` background thread pool (default 3 concurrent workers).

3. **`POST /api/downloads/cancel/{track_id}`**
   - **Action**: Flags the track cancellation event, stops `yt-dlp` download, cleans up any `.part` / `.ytdl` files.

4. **`GET /api/events` (Server-Sent Events)**
   - **Action**: Streams live JSON updates:
     - `{"type": "progress", "track_id": "...", "progress": 45.2, "speed": "2.4 MB/s", "eta": "00:15"}`
     - `{"type": "status", "track_id": "...", "status": "tagging"}`
     - `{"type": "complete", "track_id": "...", "filepath": "..."}`
     - `{"type": "error", "track_id": "...", "error_message": "..."}`

5. **`GET /api/config` & `POST /api/config`**
   - **Fields**: `download_folder` (string), `max_threads` (int), `ffmpeg_available` (bool), `ffmpeg_path` (string).

6. **`GET /api/usb/drives`**
   - **Action**: Scans removable physical drives, returns `List[UsbDrive]`.

7. **`POST /api/usb/analyze`**
   - **Request**: `{ "drive_letter": "E:\\" }`
   - **Action**: Checks free space, hashes local tracks and pen drive tracks (SHA-256), returns count of new files to copy and estimated size.

8. **`POST /api/usb/sync`**
   - **Request**: `{ "drive_letter": "E:\\" }`
   - **Action**: Copies missing songs sequentially, broadcasting progress over `/api/events`.

---

## 6. Frontend UI/UX Architecture

- **Color Theme**:
  - Dark Slate / Zinc Background (`#09090b` / `#18181b`)
  - Elevated Cards (`#27272a`)
  - Accent / Primary (`#22c55e` - Spotify Green)
  - Text: High-contrast white (`#fafafa`) and muted zinc (`#a1a1aa`)
- **Key Views**:
  - **Header**: Live connection dot, storage path display, "Sync to USB" trigger.
  - **Input Box**: Expandable textarea supporting multi-line paste with "Analyze Links" button.
  - **Queue Header**: Statistics bar (e.g. `14 Tracks | 3 Completed | 1 Downloading | 0 Failed`) and batch action buttons ("Download All", "Clear Finished").
  - **Track Cards**: Grid or stacked list showing cover art image, song title, artist, live progress meter, transfer speed, and cancel/retry buttons.
  - **USB Sync Modal**: Visual drive selector, capacity meter, diff preview, and transfer progress bar.

---

## 7. Error Handling, Resilience & Edge Cases

1. **Missing FFmpeg**:
   - Backend scans PATH and LocalAppData WinGet directories on startup.
   - If missing, `/api/config` sets `ffmpeg_available: false`. The frontend renders a warning banner with the WinGet command `winget install Gyan.FFmpeg`.
2. **YouTube 429 Rate Limiting**:
   - The thread pool limits concurrency (default: 3). `yt-dlp` options include sleep intervals between extractions and automatic retry on HTTP 429.
3. **Aborted Downloads**:
   - Temporary files (`*.part`, `*.ytdl`) are automatically cleaned up when a track is cancelled or on startup.
4. **Invalid or Private Spotify Links**:
   - Individual track failures do not fail the batch. The specific card transitions to `error` state with a descriptive message and retry button.

---

## 8. Verification & Testing Strategy

1. **Backend Tests (`pytest`)**:
   - Unit tests for Spotify link parsing (single track, playlist, album).
   - Mocked metadata extraction and duplicate detection.
   - SHA-256 hashing and USB comparison logic tests.
   - REST endpoints validation with `httpx.AsyncClient`.
2. **Frontend Build & Integration**:
   - TypeScript compilation and Vite production build (`npm run build`).
   - Browser smoke test with live SSE progress event reception and track download verification.

---

## 9. Launch & Deployment

- **One-Click Startup (`run_app.py` & `start_app.bat`)**:
  - Automatically installs/checks dependencies if needed.
  - Starts FastAPI with Uvicorn.
  - Launches default web browser pointing to `http://localhost:8000`.
