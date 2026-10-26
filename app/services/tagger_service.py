import os
import requests
from typing import Optional

try:
    from mutagen.id3 import ID3, TIT2, TPE1, TALB, APIC, ID3NoHeaderError
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False

def embed_id3_metadata(
    file_path: str,
    title: str,
    artist: str,
    album: Optional[str] = None,
    cover_url: Optional[str] = None
) -> bool:
    """Embed Title, Artist, Album, and Cover Art into an MP3 file."""
    if not MUTAGEN_AVAILABLE or not os.path.exists(file_path):
        return False

    try:
        try:
            audio = ID3(file_path)
        except ID3NoHeaderError:
            audio = ID3()

        if title:
            audio.add(TIT2(encoding=3, text=title))
        if artist:
            audio.add(TPE1(encoding=3, text=artist))
        if album:
            audio.add(TALB(encoding=3, text=album))

        # Embed Album Artwork if available
        if cover_url:
            try:
                resp = requests.get(cover_url, timeout=8)
                if resp.status_code == 200:
                    mime = 'image/jpeg'
                    if cover_url.lower().endswith('.png'):
                        mime = 'image/png'
                    audio.add(APIC(
                        encoding=3,
                        mime=mime,
                        type=3,  # Front cover
                        desc='Cover',
                        data=resp.content
                    ))
            except Exception:
                pass

        audio.save(file_path)
        return True
    except Exception:
        return False
