import os
import shutil
import hashlib
import psutil
from typing import List, Dict, Set, Optional, Tuple, Any
from app.models.usb import UsbDrive, UsbSyncSummary
from app.services.event_service import event_bus

AUDIO_EXTENSIONS = ('.mp3', '.m4a', '.flac', '.wav', '.ogg')

def compute_file_hash(filepath: str, chunk_size: int = 65536) -> str:
    """Calculate SHA-256 hash of a file for exact duplicate detection."""
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(chunk_size):
            sha256.update(chunk)
    return sha256.hexdigest()

def list_usb_drives() -> List[UsbDrive]:
    """List connected removable / external storage drives on the system."""
    drives: List[UsbDrive] = []
    
    try:
        partitions = psutil.disk_partitions(all=False)
        for p in partitions:
            # On Windows, skip system drive C:\ or partitions that aren't ready
            mount = p.mountpoint
            if os.name == 'nt' and mount.upper().startswith('C:'):
                continue
            
            # Check if drive is removable or external, or has valid usage
            try:
                usage = shutil.disk_usage(mount)
                total_gb = round(usage.total / (1024 ** 3), 2)
                free_gb = round(usage.free / (1024 ** 3), 2)
                
                # Filter out tiny optical discs or empty virtual drives
                if total_gb > 0:
                    vol_name = p.device
                    if os.name == 'nt':
                        # Clean drive letter display
                        vol_name = f"Removable ({mount})"
                    
                    drives.append(UsbDrive(
                        drive_letter=mount,
                        volume_name=vol_name,
                        total_gb=total_gb,
                        free_gb=free_gb
                    ))
            except (PermissionError, FileNotFoundError, OSError):
                continue
    except Exception:
        pass
        
    return drives

def scan_directory_hashes(directory: str) -> Dict[str, str]:
    """Scan directory for audio files and map SHA-256 hash -> filename."""
    hash_map: Dict[str, str] = {}
    if not os.path.exists(directory):
        return hash_map
        
    for root, _, files in os.walk(directory):
        for f in files:
            if f.lower().endswith(AUDIO_EXTENSIONS):
                full_path = os.path.join(root, f)
                try:
                    f_hash = compute_file_hash(full_path)
                    hash_map[f_hash] = full_path
                except Exception:
                    pass
    return hash_map

def analyze_usb_sync(source_folder: str, destination_folder: str) -> UsbSyncSummary:
    """Analyze source and target USB destination for missing tracks and capacity."""
    if not os.path.exists(source_folder):
        return UsbSyncSummary(
            source_folder=source_folder,
            drive_letter=destination_folder,
            total_source_tracks=0,
            already_synced_tracks=0,
            new_tracks_to_copy=0,
            estimated_size_mb=0.0,
            enough_space=True
        )

    # Hashes already on destination
    dest_hashes = scan_directory_hashes(destination_folder)
    
    total_source = 0
    already_synced = 0
    new_tracks = 0
    needed_bytes = 0

    for item in os.listdir(source_folder):
        if item.lower().endswith(AUDIO_EXTENSIONS):
            full_src = os.path.join(source_folder, item)
            total_source += 1
            try:
                src_hash = compute_file_hash(full_src)
                if src_hash in dest_hashes:
                    already_synced += 1
                else:
                    new_tracks += 1
                    needed_bytes += os.path.getsize(full_src)
            except Exception:
                pass

    needed_mb = round(needed_bytes / (1024 * 1024), 2)
    if needed_bytes > 0 and needed_mb == 0.0:
        needed_mb = 0.01
    
    enough_space = True
    try:
        usage = shutil.disk_usage(destination_folder)
        enough_space = usage.free >= needed_bytes
    except Exception:
        pass

    return UsbSyncSummary(
        source_folder=source_folder,
        drive_letter=destination_folder,
        total_source_tracks=total_source,
        already_synced_tracks=already_synced,
        new_tracks_to_copy=new_tracks,
        estimated_size_mb=needed_mb,
        enough_space=enough_space
    )

def sync_to_usb(source_folder: str, destination_folder: str) -> Dict[str, Any]:
    """Copy missing audio files from source to destination drive, emitting progress events."""
    os.makedirs(destination_folder, exist_ok=True)
    dest_hashes = scan_directory_hashes(destination_folder)
    
    files_to_copy: List[str] = []
    for item in os.listdir(source_folder):
        if item.lower().endswith(AUDIO_EXTENSIONS):
            full_src = os.path.join(source_folder, item)
            try:
                src_hash = compute_file_hash(full_src)
                if src_hash not in dest_hashes:
                    files_to_copy.append(item)
            except Exception:
                pass

    total = len(files_to_copy)
    copied = 0
    errors: List[str] = []

    for idx, filename in enumerate(files_to_copy, 1):
        src_path = os.path.join(source_folder, filename)
        dst_path = os.path.join(destination_folder, filename)

        event_bus.publish({
            "type": "usb_sync_progress",
            "current_file": filename,
            "copied": copied,
            "total": total,
            "percent": round((copied / total) * 100, 1) if total > 0 else 100.0
        })

        try:
            shutil.copy2(src_path, dst_path)
            copied += 1
        except Exception as e:
            errors.append(f"{filename}: {str(e)}")

    event_bus.publish({
        "type": "usb_sync_progress",
        "current_file": "Sync Complete",
        "copied": copied,
        "total": total,
        "percent": 100.0,
        "status": "completed"
    })

    return {
        "synced": copied,
        "skipped": len(dest_hashes),
        "total": total,
        "errors": errors
    }
