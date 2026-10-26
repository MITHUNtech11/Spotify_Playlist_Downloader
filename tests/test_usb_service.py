import pytest
from app.services.usb_service import compute_file_hash, analyze_usb_sync, list_usb_drives, sync_to_usb
from app.models.usb import UsbDrive, UsbSyncSummary

def test_compute_file_hash(tmp_path):
    test_file = tmp_path / "song.mp3"
    test_file.write_bytes(b"sample audio content")
    h1 = compute_file_hash(str(test_file))
    assert len(h1) == 64  # SHA-256 hex string
    
    # Same content produces identical hash
    test_file_2 = tmp_path / "renamed_song.mp3"
    test_file_2.write_bytes(b"sample audio content")
    assert compute_file_hash(str(test_file_2)) == h1

def test_analyze_usb_sync(tmp_path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir(); dst.mkdir()
    
    # 1 identical file in both, 1 new file in src
    (src / "track1.mp3").write_bytes(b"content 1")
    (dst / "renamed_track1.mp3").write_bytes(b"content 1")
    (src / "track2.mp3").write_bytes(b"content 2")
    
    summary = analyze_usb_sync(str(src), str(dst))
    assert summary.total_source_tracks == 2
    assert summary.already_synced_tracks == 1
    assert summary.new_tracks_to_copy == 1
    assert summary.estimated_size_mb > 0
    assert summary.enough_space is True

def test_list_usb_drives():
    drives = list_usb_drives()
    assert isinstance(drives, list)

def test_usb_missing_drive_handling():
    summary = analyze_usb_sync("./Dad_Car_Songs", "Z:\\NonExistentDrive")
    assert summary.enough_space is False

def test_sync_to_usb_nonexistent_drive_reports_error():
    res = sync_to_usb("./Dad_Car_Songs", "Z:\\NonExistentDrive\\Music")
    assert res.get("status") == "error"
    assert len(res.get("errors", [])) > 0

