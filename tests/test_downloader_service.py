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
