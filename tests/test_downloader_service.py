import pytest
import asyncio
from app.services.event_service import EventBus
from app.services.tagger_service import embed_id3_metadata
from app.services.downloader_service import DownloaderService
from app.models.track import TrackItem

@pytest.mark.asyncio
async def test_event_bus_publish_subscribe():
    bus = EventBus()
    queue = bus.subscribe()
    bus.publish({"type": "progress", "track_id": "t1", "progress": 50.0})
    event = await asyncio.wait_for(queue.get(), timeout=1.0)
    assert event["type"] == "progress"
    assert event["track_id"] == "t1"
    assert event["progress"] == 50.0
    bus.unsubscribe(queue)
    assert len(bus.subscribers) == 0

def test_downloader_service_queue_and_cancel():
    service = DownloaderService(max_workers=2)
    track = TrackItem(id="test_id", title="Title", artist="Artist", spotify_url="https://open.spotify.com/track/test_id")
    service.add_to_queue([track])
    
    assert service.get_track("test_id") is not None
    assert service.get_track("test_id").status == "queued"
    
    service.cancel("test_id")
    assert service.get_track("test_id").status == "cancelled"

def test_embed_id3_metadata_nonexistent_file():
    # Should safely return False if file does not exist
    result = embed_id3_metadata("non_existent_file.mp3", "Title", "Artist", None, None)
    assert result is False

def test_cleanup_partial_files_does_not_delete_other_tracks(tmp_path):
    service = DownloaderService()
    track_a = TrackItem(id="a", title="Song Alpha", artist="Artist", spotify_url="https://open.spotify.com/track/a")
    track_b = TrackItem(id="b", title="Song Beta", artist="Artist", spotify_url="https://open.spotify.com/track/b")
    service.add_to_queue([track_a, track_b])
    
    file_a = tmp_path / "Song Alpha.mp3.part"
    file_b = tmp_path / "Song Beta.mp3.part"
    file_a.write_text("data")
    file_b.write_text("data")
    
    service._cleanup_partial_files("a", str(tmp_path))
    assert not file_a.exists(), "Track A partial should be deleted"
    assert file_b.exists(), "Track B partial MUST NOT be deleted by track A cleanup"

def test_downloader_429_retry_logic(monkeypatch, tmp_path):
    service = DownloaderService(max_workers=1)
    track = TrackItem(id="rate_429", title="Song 429", artist="Artist", spotify_url="https://open.spotify.com/track/rate_429")
    service.add_to_queue([track])
    
    attempts = 0
    statuses_seen = []
    
    class MockYDL:
        def __init__(self, opts):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def extract_info(self, *args, **kwargs):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise Exception("HTTP Error 429: Too Many Requests")
            return {"title": "Song 429"}
        def prepare_filename(self, info):
            return str(tmp_path / "Song 429.mp3")

    monkeypatch.setattr("yt_dlp.YoutubeDL", MockYDL)
    monkeypatch.setattr("time.sleep", lambda s: None)
    
    # Run worker directly
    service._download_worker("rate_429", str(tmp_path))
    
    assert attempts == 2
    assert service.get_track("rate_429").status == "completed"


