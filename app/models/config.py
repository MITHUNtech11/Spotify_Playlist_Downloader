from typing import Optional
from pydantic import BaseModel, Field

class AppConfig(BaseModel):
    download_folder: str = "./Dad_Car_Songs"
    max_threads: int = Field(default=3, ge=1, le=10)
    ffmpeg_available: bool = False
    ffmpeg_path: Optional[str] = None

class UpdateConfigRequest(BaseModel):
    download_folder: Optional[str] = None
    max_threads: Optional[int] = Field(default=None, ge=1, le=10)
