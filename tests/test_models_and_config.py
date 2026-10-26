from app.models.track import TrackItem
from app.models.config import AppConfig
from app.models.usb import UsbDrive, UsbSyncSummary
from app.config import get_settings

def test_track_item_defaults():
    track = TrackItem(id="123", title="Song", artist="Artist", spotify_url="https://open.spotify.com/track/123")
    assert track.status == "queued"
    assert track.progress == 0.0
    assert track.already_downloaded is False
    assert track.album is None
    assert track.thumbnail_url is None

def test_settings_initialization():
    settings = get_settings()
    assert settings.download_folder != ""
    assert settings.max_threads >= 1

def test_usb_models():
    drive = UsbDrive(drive_letter="E:\\", volume_name="SANDISK", total_gb=32.0, free_gb=14.5)
    assert drive.drive_letter == "E:\\"
    
    summary = UsbSyncSummary(
        source_folder="./Dad_Car_Songs",
        drive_letter="E:\\",
        total_source_tracks=10,
        already_synced_tracks=6,
        new_tracks_to_copy=4,
        estimated_size_mb=28.5,
        enough_space=True
    )
    assert summary.new_tracks_to_copy == 4
    assert summary.enough_space is True
