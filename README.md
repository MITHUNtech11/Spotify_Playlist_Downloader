# Spotify Downloader Pro 🎵

A commercial-grade, interactive web application and local desktop tool to convert Spotify track, playlist, and album links into high-quality MP3s with **embedded ID3 tags (Title, Artist, Album) and high-resolution Spotify album artwork**, paired with a **One-Click USB Pen Drive Sync Manager** featuring SHA-256 deduplication.

Designed for music enthusiasts, playlist archival, and organizing audio collections for car infotainment systems or USB flash drives.

---

## ✨ Features

- **🎨 Modern Interactive Web UI:**
  - Built with **React 18 + Vite + Tailwind CSS + Lucide Icons**.
  - Sleek Spotify-inspired dark aesthetic with responsive layouts and real-time toast alerts.
- **🔗 Universal Spotify Ingestion:**
  - Paste **Playlist URLs**, **Album URLs**, or **individual Track URLs** (or multi-line batches).
  - Automatically unpacks full playlists into individual songs with album artwork previews.
- **⚡ Real-Time Streaming Progress:**
  - Zero-polling Server-Sent Events (SSE) stream live percentage, download speed (e.g. `3.2 MB/s`), and ETA directly to each song card.
- **🏷️ Automatic ID3 Tagging & Artwork Embedding:**
  - Uses `mutagen` to embed high-res cover art, song title, and artist directly into each MP3.
- **🛡️ Smart Duplicate Protection:**
  - Compares normalized song titles against your library to prevent duplicate downloads.
- **💾 One-Click USB / Pen Drive Sync:**
  - Auto-detects connected removable drives on Windows.
  - Computes **SHA-256 hashes** to copy only new or modified songs (saving time and flash memory wear even if files were renamed on the flash drive).
- **🚀 One-Click Launch:**
  - Simply double-click `start_app.bat` or run `python run_app.py` to start the backend and open the product in your browser automatically.

---

## 🛠️ Architecture

```text
┌────────────────────────────────────────────────────────┐
│             Frontend (Browser Web UI)                  │
│       React 18 + Vite + Tailwind CSS + Lucide          │
└──────────────────────────▲─────────────────────────────┘
                           │ HTTP REST (Controls/Config)
                           │ Server-Sent Events (SSE) (Live Progress Stream)
┌──────────────────────────▼─────────────────────────────┐
│             Backend Service (Python)                   │
│             FastAPI + Uvicorn Local Server             │
├────────────────────────────────────────────────────────┤
│ • SpotifyService: oEmbed & Playlist/Album Unpacker     │
│ • DownloaderService: Async yt-dlp Queue + Mutagen ID3  │
│ • UsbService: Drive Detector & SHA-256 Sync            │
│ • EventBus: Real-time SSE progress broadcaster         │
└────────────────────────────────────────────────────────┘
```

---

## 📋 Requirements

1. **Python 3.8+**
2. **FFmpeg** (Required by `yt-dlp` for extracting audio and converting to MP3):
   - **Windows (PowerShell):**
     ```powershell
     winget install Gyan.FFmpeg
     ```
   - **macOS (Homebrew):**
     ```bash
     brew install ffmpeg
     ```
   - **Linux (Debian/Ubuntu):**
     ```bash
     sudo apt update && sudo apt install ffmpeg
     ```

---

## 🚀 Quick Start (One-Click)

### 1. Launch the Application
Simply double-click:
```text
start_app.bat
```
Or run from your terminal:
```bash
python run_app.py
```
This automatically starts the local FastAPI server at `http://127.0.0.1:8000` and launches your default web browser!

---

## 🧑‍💻 Developer Setup (Frontend + Backend Development)

If you wish to modify or build the React frontend:

### 1. Backend (FastAPI)
```bash
# In project root
python -m venv .venv
.\.venv\Scripts\activate   # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend (React + Vite)
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser. Vite proxies all `/api` requests to the FastAPI backend.

### 3. Build Production Assets
```bash
cd frontend
npm run build
```
This generates optimized static files in `frontend/dist/` which FastAPI serves directly at `http://localhost:8000`.

---

## 🧪 Running Automated Tests

Run the complete backend test suite:
```bash
pytest -v
```
All unit and integration tests (URL parsers, metadata resolvers, download queue, USB sync, and API endpoints) will run with full coverage.

---

## 📄 License

This project is licensed under the MIT License.
