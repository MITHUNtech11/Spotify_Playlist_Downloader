from typing import Optional
from pydantic import BaseModel, Field

class TrackItem(BaseModel):
    id: str
    title: str
    artist: str
    album: Optional[str] = None
    thumbnail_url: Optional[str] = None
    spotify_url: str
    status: str = Field(default="queued")  # queued, downloading, converting, tagging, completed, duplicate, error
    progress: float = 0.0
    speed: Optional[str] = None
    eta: Optional[str] = None
    error_message: Optional[str] = None
    already_downloaded: bool = False
