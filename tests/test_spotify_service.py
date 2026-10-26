import pytest
from app.services.spotify_service import (
    parse_spotify_url,
    normalize_title,
    is_song_downloaded,
    resolve_input_batch
)
from app.models.track import TrackItem

def test_parse_spotify_urls():
    assert parse_spotify_url("https://open.spotify.com/track/2109dBho14Lqh2wr8goqAP") == ("track", "2109dBho14Lqh2wr8goqAP")
    assert parse_spotify_url("https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M?si=12345") == ("playlist", "37i9dQZF1DXcBWIGoYBM5M")
    assert parse_spotify_url("https://open.spotify.com/album/4m2880jivSbbyEGAKfITCa") == ("album", "4m2880jivSbbyEGAKfITCa")
    assert parse_spotify_url("not-a-spotify-link") == (None, None)

def test_normalize_title():
    assert normalize_title("Song Title (Official Music Video)") == "song title"
    assert normalize_title("Song Title [Official Audio]") == "song title"
    assert normalize_title("Artist - Song Title") == "song title"

def test_duplicate_check(tmp_path):
    # simulate an already downloaded mp3
    (tmp_path / "My Favorite Song.mp3").write_text("audio")
    assert is_song_downloaded("My Favorite Song", str(tmp_path)) is True
    assert is_song_downloaded("Different Song", str(tmp_path)) is False

def test_resolve_input_batch_with_duplicates(tmp_path, monkeypatch):
    # Mock resolving a track
    (tmp_path / "Believer.mp3").write_text("audio")
    
    def mock_resolve_track(track_id):
        return TrackItem(
            id=track_id,
            title="Believer",
            artist="Imagine Dragons",
            spotify_url=f"https://open.spotify.com/track/{track_id}"
        )
        
    monkeypatch.setattr("app.services.spotify_service.resolve_track_metadata", mock_resolve_track)
    
    results = resolve_input_batch(["https://open.spotify.com/track/test12345"], download_folder=str(tmp_path))
    assert len(results) == 1
    assert results[0].title == "Believer"
    assert results[0].already_downloaded is True
