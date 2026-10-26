import os
import re
import html
import requests
from bs4 import BeautifulSoup
from typing import Optional, Tuple, List, Union
from app.models.track import TrackItem

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
}

SPOTIFY_URL_PATTERNS = {
    'track': re.compile(r'open\.spotify\.com/(?:intl-[a-z]{2}/)?track/([a-zA-Z0-9]+)'),
    'playlist': re.compile(r'open\.spotify\.com/(?:intl-[a-z]{2}/)?playlist/([a-zA-Z0-9]+)'),
    'album': re.compile(r'open\.spotify\.com/(?:intl-[a-z]{2}/)?album/([a-zA-Z0-9]+)')
}

def parse_spotify_url(url: str) -> Tuple[Optional[str], Optional[str]]:
    """Parse a Spotify URL into (type, id).
    Types: 'track', 'playlist', 'album', or (None, None).
    """
    if not url or not isinstance(url, str):
        return None, None
        
    for link_type, pattern in SPOTIFY_URL_PATTERNS.items():
        match = pattern.search(url)
        if match:
            return link_type, match.group(1)
            
    return None, None

def normalize_title(title: str) -> str:
    """Normalize song title for duplicate detection."""
    if not title:
        return ""
    # Strip common suffixes like (Official Music Video), [Lyric Video], etc.
    cleaned = re.sub(r'[\(\[].*?(?:official|video|audio|lyric|remastered|version|edit).*?[\)\]]', '', title, flags=re.IGNORECASE)
    # If "Artist - Title", strip before dash
    if ' - ' in cleaned:
        cleaned = cleaned.split(' - ', 1)[1]
    # Remove non-alphanumeric except spaces
    cleaned = re.sub(r'[^\w\s]', '', cleaned).strip().lower()
    return re.sub(r'\s+', ' ', cleaned)

def is_song_downloaded(song_name: str, download_folder: str) -> bool:
    """Check if a song is already downloaded in download_folder."""
    if not os.path.exists(download_folder):
        return False
        
    target_norm = normalize_title(song_name)
    if not target_norm:
        return False
        
    for item in os.listdir(download_folder):
        if item.lower().endswith(('.mp3', '.m4a', '.flac', '.wav')):
            filename_without_ext = os.path.splitext(item)[0]
            existing_norm = normalize_title(filename_without_ext)
            # Strict equality after normalization avoids false positives on common words
            if target_norm == existing_norm:
                return True
    return False

def resolve_track_metadata(track_id: str) -> Optional[TrackItem]:
    """Resolve a single track's metadata via Spotify oEmbed and HTML fallback."""
    track_url = f"https://open.spotify.com/track/{track_id}"
    
    # 1. Try Spotify Official Public oEmbed API
    try:
        oembed_url = f"https://open.spotify.com/oembed?url={track_url}"
        resp = requests.get(oembed_url, headers=HEADERS, timeout=6)
        if resp.status_code == 200:
            data = resp.json()
            raw_title = data.get('title', '')
            thumbnail = data.get('thumbnail_url', '')
            
            # Format usually: "Song Title" by Artist or Artist - Song Title
            title, artist = "", ""
            if ' by ' in raw_title:
                parts = raw_title.split(' by ', 1)
                title = parts[0].strip().strip('"\'')
                artist = parts[1].strip()
            elif ' - ' in raw_title:
                parts = raw_title.split(' - ', 1)
                artist = parts[0].strip()
                title = parts[1].strip()
            else:
                title = raw_title
                artist = "Unknown Artist"
                
            return TrackItem(
                id=track_id,
                title=title,
                artist=artist,
                thumbnail_url=thumbnail,
                spotify_url=track_url
            )
    except Exception:
        pass
        
    # 2. Fallback to HTML Scraping
    try:
        resp = requests.get(track_url, headers=HEADERS, timeout=6)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            og_title = soup.find('meta', property='og:title')
            og_desc = soup.find('meta', property='og:description')
            og_image = soup.find('meta', property='og:image')
            
            title = og_title['content'] if og_title else f"Track {track_id}"
            artist = og_desc['content'] if og_desc else "Unknown Artist"
            thumbnail = og_image['content'] if og_image else None
            
            # og:description may say "Artist · Song · Year"
            if ' · ' in artist:
                artist = artist.split(' · ')[0]
                
            return TrackItem(
                id=track_id,
                title=html.unescape(title),
                artist=html.unescape(artist),
                thumbnail_url=thumbnail,
                spotify_url=track_url
            )
    except Exception:
        pass
        
    return None

def resolve_playlist_tracks(playlist_id: str) -> List[TrackItem]:
    """Extract tracks from a public Spotify playlist embed or page."""
    embed_url = f"https://open.spotify.com/embed/playlist/{playlist_id}"
    tracks: List[TrackItem] = []
    
    try:
        resp = requests.get(embed_url, headers=HEADERS, timeout=8)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            # Look for track links in the embed
            track_links = soup.find_all('a', href=re.compile(r'/track/([a-zA-Z0-9]+)'))
            seen_ids = set()
            for link in track_links:
                href = link.get('href', '')
                match = re.search(r'/track/([a-zA-Z0-9]+)', href)
                if match:
                    tid = match.group(1)
                    if tid not in seen_ids:
                        seen_ids.add(tid)
                        track_item = resolve_track_metadata(tid)
                        if track_item:
                            tracks.append(track_item)
    except Exception:
        pass
        
    return tracks

def resolve_album_tracks(album_id: str) -> List[TrackItem]:
    """Extract tracks from a public Spotify album embed or page."""
    embed_url = f"https://open.spotify.com/embed/album/{album_id}"
    tracks: List[TrackItem] = []
    
    try:
        resp = requests.get(embed_url, headers=HEADERS, timeout=8)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            track_links = soup.find_all('a', href=re.compile(r'/track/([a-zA-Z0-9]+)'))
            seen_ids = set()
            for link in track_links:
                href = link.get('href', '')
                match = re.search(r'/track/([a-zA-Z0-9]+)', href)
                if match:
                    tid = match.group(1)
                    if tid not in seen_ids:
                        seen_ids.add(tid)
                        track_item = resolve_track_metadata(tid)
                        if track_item:
                            tracks.append(track_item)
    except Exception:
        pass
        
    return tracks

def resolve_input_batch(raw_input: Union[str, List[str]], download_folder: str = "./Dad_Car_Songs") -> List[TrackItem]:
    """Resolve a collection of raw inputs (lines or list of URLs) into TrackItems with duplicate detection."""
    urls = []
    if isinstance(raw_input, str):
        urls = [line.strip() for line in raw_input.splitlines() if line.strip() and not line.strip().startswith('#')]
    elif isinstance(raw_input, list):
        urls = [u.strip() for u in raw_input if u and isinstance(u, str) and u.strip() and not u.strip().startswith('#')]
        
    resolved: List[TrackItem] = []
    seen_ids = set()
    
    for url in urls:
        link_type, item_id = parse_spotify_url(url)
        if not link_type or not item_id:
            continue
            
        if link_type == 'track':
            if item_id not in seen_ids:
                seen_ids.add(item_id)
                track = resolve_track_metadata(item_id)
                if track:
                    track.already_downloaded = is_song_downloaded(f"{track.artist} - {track.title}", download_folder) or is_song_downloaded(track.title, download_folder)
                    resolved.append(track)
        elif link_type == 'playlist':
            playlist_tracks = resolve_playlist_tracks(item_id)
            for track in playlist_tracks:
                if track.id not in seen_ids:
                    seen_ids.add(track.id)
                    track.already_downloaded = is_song_downloaded(f"{track.artist} - {track.title}", download_folder) or is_song_downloaded(track.title, download_folder)
                    resolved.append(track)
        elif link_type == 'album':
            album_tracks = resolve_album_tracks(item_id)
            for track in album_tracks:
                if track.id not in seen_ids:
                    seen_ids.add(track.id)
                    track.already_downloaded = is_song_downloaded(f"{track.artist} - {track.title}", download_folder) or is_song_downloaded(track.title, download_folder)
                    resolved.append(track)
                    
    return resolved
