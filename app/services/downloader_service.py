import os
import re
import glob
import time
import shutil
import threading
from typing import Dict, List, Optional, Set, Any
from concurrent.futures import ThreadPoolExecutor
import yt_dlp

from app.models.track import TrackItem
from app.services.event_service import event_bus
from app.services.tagger_service import embed_id3_metadata
from app.config import get_settings

class DownloaderService:
    def __init__(self, max_workers: int = 3):
        self.max_workers = max_workers
        self.tracks: Dict[str, TrackItem] = {}
        self.lock = threading.Lock()
        self.cancelled_tracks: Set[str] = set()
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers, thread_name_prefix="dl_worker")
        self.active_futures: Dict[str, Any] = {}

    def add_to_queue(self, tracks: List[TrackItem]):
        with self.lock:
            for t in tracks:
                if t.id not in self.tracks:
                    self.tracks[t.id] = t
                else:
                    # Update metadata but preserve status if already completed
                    if self.tracks[t.id].status not in ("completed", "downloading"):
                        self.tracks[t.id] = t

    def get_track(self, track_id: str) -> Optional[TrackItem]:
        with self.lock:
            return self.tracks.get(track_id)

    def get_all_tracks(self) -> List[TrackItem]:
        with self.lock:
            return list(self.tracks.values())

    def cancel(self, track_id: str):
        with self.lock:
            self.cancelled_tracks.add(track_id)
            if track_id in self.tracks:
                self.tracks[track_id].status = "cancelled"
                self.tracks[track_id].speed = None
                self.tracks[track_id].eta = None

        event_bus.publish({
            "type": "status",
            "track_id": track_id,
            "status": "cancelled"
        })

        # Cleanup incomplete download files for this track
        settings = get_settings()
        self._cleanup_partial_files(track_id, settings.download_folder)

    def _cleanup_partial_files(self, track_id: str, download_folder: str):
        if not os.path.exists(download_folder):
            return
        track = self.get_track(track_id)
        patterns = ["*.part", "*.ytdl", "*.temp"]
        if track:
            sanitized = re.sub(r'[\\/*?:"<>|]', "", track.title)
            patterns.append(f"*{sanitized}*.part")
        for pat in patterns:
            for f in glob.glob(os.path.join(download_folder, pat)):
                try:
                    os.remove(f)
                except Exception:
                    pass

    def start_downloads(self, track_ids: Optional[List[str]] = None, output_folder: Optional[str] = None):
        settings = get_settings()
        folder = output_folder or settings.download_folder
        os.makedirs(folder, exist_ok=True)

        target_ids = track_ids
        if not target_ids:
            with self.lock:
                target_ids = [
                    tid for tid, t in self.tracks.items()
                    if t.status in ("queued", "error", "cancelled") and not t.already_downloaded
                ]

        for tid in target_ids:
            with self.lock:
                if tid in self.cancelled_tracks:
                    self.cancelled_tracks.remove(tid)
                track = self.tracks.get(tid)
                if track:
                    track.status = "queued"
                    track.progress = 0.0
                    track.error_message = None

            self.executor.submit(self._download_worker, tid, folder)

    def _download_worker(self, track_id: str, output_folder: str):
        track = self.get_track(track_id)
        if not track:
            return

        with self.lock:
            if track_id in self.cancelled_tracks:
                return
            track.status = "downloading"
            track.progress = 0.0

        event_bus.publish({
            "type": "status",
            "track_id": track_id,
            "status": "downloading"
        })

        search_query = f"ytsearch1:{track.artist} - {track.title}"
        out_tmpl = os.path.join(output_folder, "%(title)s.%(ext)s")

        def ytdl_progress_hook(d):
            if track_id in self.cancelled_tracks:
                raise Exception("Download cancelled by user")

            status = d.get('status')
            if status == 'downloading':
                total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                downloaded_bytes = d.get('downloaded_bytes', 0)
                speed = d.get('speed', 0)
                eta = d.get('eta', 0)

                percent = 0.0
                if total_bytes > 0:
                    percent = round((downloaded_bytes / total_bytes) * 100, 1)

                speed_str = f"{round(speed / (1024 * 1024), 1)} MB/s" if speed else "N/A"
                eta_str = f"{int(eta)}s" if eta else "N/A"

                with self.lock:
                    track.progress = percent
                    track.speed = speed_str
                    track.eta = eta_str

                event_bus.publish({
                    "type": "progress",
                    "track_id": track_id,
                    "progress": percent,
                    "speed": speed_str,
                    "eta": eta_str
                })

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': out_tmpl,
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'progress_hooks': [ytdl_progress_hook],
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_query, download=True)
                downloaded_title = info.get('title', track.title) if info else track.title
                
            # File converted to mp3
            with self.lock:
                track.status = "tagging"
                track.progress = 95.0
            event_bus.publish({"type": "status", "track_id": track_id, "status": "tagging"})

            # Find generated mp3 file
            expected_file = os.path.join(output_folder, f"{downloaded_title}.mp3")
            if not os.path.exists(expected_file):
                # Search for latest modified mp3 in directory
                mp3s = glob.glob(os.path.join(output_folder, "*.mp3"))
                if mp3s:
                    expected_file = max(mp3s, key=os.path.getmtime)

            if os.path.exists(expected_file):
                embed_id3_metadata(
                    expected_file,
                    title=track.title,
                    artist=track.artist,
                    album=track.album,
                    cover_url=track.thumbnail_url
                )

            with self.lock:
                track.status = "completed"
                track.progress = 100.0
                track.speed = None
                track.eta = None
                track.already_downloaded = True

            event_bus.publish({
                "type": "status",
                "track_id": track_id,
                "status": "completed",
                "progress": 100.0
            })

        except Exception as e:
            err_msg = str(e)
            if "cancelled by user" in err_msg.lower():
                with self.lock:
                    track.status = "cancelled"
                    track.speed = None
                    track.eta = None
                event_bus.publish({"type": "status", "track_id": track_id, "status": "cancelled"})
            else:
                with self.lock:
                    track.status = "error"
                    track.error_message = err_msg
                    track.speed = None
                    track.eta = None
                event_bus.publish({
                    "type": "status",
                    "track_id": track_id,
                    "status": "error",
                    "error_message": err_msg
                })
            self._cleanup_partial_files(track_id, output_folder)

downloader_service = DownloaderService()
