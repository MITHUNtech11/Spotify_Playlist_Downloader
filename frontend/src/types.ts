export type DownloadStatus = 
  | 'queued' 
  | 'downloading' 
  | 'retrying'
  | 'converting' 
  | 'tagging' 
  | 'completed' 
  | 'cancelled' 
  | 'error';

export interface TrackItem {
  id: string;
  title: string;
  artist: string;
  album?: string | null;
  thumbnail_url?: string | null;
  spotify_url: string;
  status: DownloadStatus;
  progress: number;
  speed?: string | null;
  eta?: string | null;
  error_message?: string | null;
  already_downloaded: boolean;
}

export interface AppConfig {
  download_folder: string;
  max_threads: number;
  ffmpeg_available: boolean;
  ffmpeg_path?: string | null;
}

export interface UsbDrive {
  drive_letter: string;
  volume_name: string;
  total_gb: number;
  free_gb: number;
}

export interface UsbSyncSummary {
  source_folder: string;
  drive_letter: string;
  total_source_tracks: number;
  already_synced_tracks: number;
  new_tracks_to_copy: number;
  estimated_size_mb: number;
  enough_space: boolean;
}

export interface ProgressEvent {
  type: 'progress' | 'status' | 'usb_sync_progress';
  track_id?: string;
  progress?: number;
  speed?: string;
  eta?: string;
  status?: DownloadStatus;
  error_message?: string;
  // USB sync fields
  current_file?: string;
  copied?: number;
  total?: number;
  percent?: number;
}
