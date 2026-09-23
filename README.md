# Spotify Playlist Downloader 🎵

A powerful Python tool to convert Spotify track URLs into song metadata and automatically download the corresponding audio from YouTube as high-quality MP3s with **embedded ID3 tags (Title, Artist) and Spotify album artwork**.

Designed for batch downloading, playlist archival, and organizing music for car infotainment systems or USB pen drives.

---

## ✨ Features

- **Reliable Spotify Metadata Resolution:** Uses Spotify's official public `oEmbed` API and page metadata (no API keys or credentials required).
- **Embedded ID3 Tags & Album Artwork:** Automatically tags MP3s with song title, artist, and embeds high-resolution Spotify album covers.
- **Batch Downloads with Multi-threading:** Fast parallel downloads via `yt-dlp` with rate-limit protection.
- **Accurate Duplicate Handling:** Skips already-downloaded songs using normalized title comparison without false positives.
- **Interactive Preview & Summary:** Displays a clean metric table before downloading and asks for confirmation.
- **Automated Cleanup:** Automatically purges temporary `.part` files from aborted downloads.
- **CLI & Configuration Options:** Run with CLI arguments (`--urls`, `--output`, `--threads`, `--yes`) or configure defaults via `.env`.
- **USB / Pen Drive Sync Utility:** Companion tool (`copy_to_pendrive.py`) to sync downloaded songs to a USB drive using SHA-256 duplicate detection.

---

## 📋 Requirements

1. **Python 3.8+**
2. **FFmpeg** (Required by `yt-dlp` for extracting and converting audio to MP3):
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

## 🚀 Setup & Installation

### 1. Clone the repository
```bash
git clone https://github.com/MITHUNtech11/Spotify_Playlist_Downloader.git
cd Spotify_Playlist_Downloader
```

### 2. Create and activate a virtual environment (`.venv`)
- **Windows (PowerShell):**
  ```powershell
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  ```
- **macOS / Linux:**
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

---

## 🎯 Usage

### Basic Usage (Interactive)
1. Add Spotify track URLs (one per line) to `track_urls.txt`:
   ```text
   https://open.spotify.com/track/2109dBho14Lqh2wr8goqAP
   https://open.spotify.com/track/3jrOziEVwpJAETyEDZ5HWa
   https://open.spotify.com/track/5HgXSvl2YoBtEY623UsACk
   ```

2. (Optional) Set your preferred download destination in `.env`:
   ```env
   DOWNLOAD_FOLDER=./Dad_Car_Songs
   ```

3. Run the downloader:
   ```bash
   python playlist_downloader_combined.py
   ```
   The script will:
   - Extract track metadata via Spotify oEmbed.
   - Output extracted song titles into `songs.txt`.
   - Display a preview summary table.
   - Ask for confirmation (`Y/n`).
   - Download MP3s with embedded ID3 tags and album cover art.
   - Log all operations to `download_log.txt`.

---

### Command-Line Arguments (Advanced)

You can pass arguments directly without modifying `.env`:

```bash
python playlist_downloader_combined.py --help
```

| Flag | Description | Default |
| :--- | :--- | :--- |
| `-u`, `--urls` | Path to Spotify track URLs file | `track_urls.txt` |
| `-o`, `--output` | Destination directory for downloaded songs | `./Dad_Car_Songs` |
| `-t`, `--threads` | Concurrent download threads | `3` |
| `-y`, `--yes` | Auto-confirm and start download without prompting | `False` |
| `--clean-only` | Only clean up incomplete `.part` files and exit | `False` |

#### Examples:
```bash
# Download with custom folder and URLs:
python playlist_downloader_combined.py -u my_tracks.txt -o "D:/Music/RoadTrip"

# Run non-interactively (ideal for scripts/cron jobs):
python playlist_downloader_combined.py -y
```

---

## 📱 Syncing to USB / Pen Drive

Use `copy_to_pendrive.py` to copy songs to a flash drive without duplicates:
```bash
python copy_to_pendrive.py
```
- Automatically detects connected drive letters and free disk space.
- Calculates **SHA-256 hashes** so files are not copied twice even if they were renamed on the flash drive.

---

## 📂 Project Structure

```text
Playlist_Downloader/
├── .venv/                          # Virtual environment
├── .env.example                    # Example environment configuration
├── requirements.txt                # Project dependencies
├── playlist_downloader_combined.py # Main downloader script
├── copy_to_pendrive.py             # USB sync script with SHA-256 hashing
├── track_urls.txt                  # Input: Spotify track links
├── songs.txt                       # Output: Extracted song titles
├── download_log.txt                # Session execution log
└── README.md                       # Project documentation
```

---

## 🛠️ Troubleshooting

- **`ffprobe or avprobe not found`:**
  Install FFmpeg on your system (see [Requirements](#-requirements)) and restart your terminal.
- **Script skips a song:**
  The song already exists in the destination folder. Check the folder or rename if you want to re-download.
- **YouTube 429 / Rate Limit:**
  Keep the download threads at `3` (the default) or lower (`-t 2`) to ensure YouTube does not throttle requests.

---

## 📄 License

This project is licensed under the MIT License.
