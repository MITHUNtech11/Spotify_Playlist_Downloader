from pydantic import BaseModel

class UsbDrive(BaseModel):
    drive_letter: str
    volume_name: str
    total_gb: float
    free_gb: float

class UsbSyncSummary(BaseModel):
    source_folder: str
    drive_letter: str
    total_source_tracks: int
    already_synced_tracks: int
    new_tracks_to_copy: int
    estimated_size_mb: float
    enough_space: bool
