import os
import shutil
from typing import Optional
from dotenv import load_dotenv
from app.models.config import AppConfig

load_dotenv()

def detect_ffmpeg_dir() -> Optional[str]:
    """Locate ffmpeg binary on the system (PATH or common WinGet install dirs)."""
    ffmpeg_bin = shutil.which('ffmpeg')
    if ffmpeg_bin:
        return os.path.dirname(ffmpeg_bin)
    
    if os.name == 'nt':
        local_app_data = os.getenv('LOCALAPPDATA', '')
        if local_app_data:
            winget_pkgs = os.path.join(local_app_data, 'Microsoft', 'WinGet', 'Packages')
            if os.path.isdir(winget_pkgs):
                for pkg in os.listdir(winget_pkgs):
                    if 'ffmpeg' in pkg.lower():
                        pkg_path = os.path.join(winget_pkgs, pkg)
                        for root, _, files in os.walk(pkg_path):
                            if 'ffmpeg.exe' in files:
                                return root
    return None

# Ensure FFmpeg is on PATH if found
_ffmpeg_dir = detect_ffmpeg_dir()
if _ffmpeg_dir and _ffmpeg_dir not in os.environ.get('PATH', ''):
    os.environ['PATH'] = f"{_ffmpeg_dir};{os.environ.get('PATH', '')}"

_current_config = AppConfig(
    download_folder=os.getenv('DOWNLOAD_FOLDER', './Dad_Car_Songs'),
    max_threads=int(os.getenv('DOWNLOAD_THREADS', '3')),
    ffmpeg_available=_ffmpeg_dir is not None,
    ffmpeg_path=_ffmpeg_dir
)

def get_settings() -> AppConfig:
    global _current_config
    return _current_config

def update_settings(download_folder: Optional[str] = None, max_threads: Optional[int] = None) -> AppConfig:
    global _current_config
    if download_folder is not None:
        _current_config.download_folder = download_folder
    if max_threads is not None:
        _current_config.max_threads = max_threads
    return _current_config
