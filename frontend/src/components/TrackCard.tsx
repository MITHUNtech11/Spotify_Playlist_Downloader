import React from 'react';
import { 
  Music, 
  CheckCircle2, 
  Loader2, 
  AlertCircle, 
  X, 
  RotateCw, 
  ExternalLink,
  Tag,
  FileAudio
} from 'lucide-react';
import { TrackItem } from '../types';

interface TrackCardProps {
  track: TrackItem;
  onCancel: (id: string) => void;
  onRetry: (id: string) => void;
}

export const TrackCard: React.FC<TrackCardProps> = ({ track, onCancel, onRetry }) => {
  const getStatusBadge = () => {
    if (track.already_downloaded && track.status === 'queued') {
      return (
        <span className="flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          <CheckCircle2 className="w-3 h-3" /> Already Downloaded
        </span>
      );
    }

    switch (track.status) {
      case 'downloading':
        return (
          <span className="flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20 animate-pulse">
            <Loader2 className="w-3 h-3 animate-spin" /> Downloading
          </span>
        );
      case 'retrying':
        return (
          <span className="flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse">
            <RotateCw className="w-3 h-3 animate-spin" /> Rate limited (Retrying...)
          </span>
        );
      case 'converting':
        return (
          <span className="flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-400 border border-purple-500/20">
            <FileAudio className="w-3 h-3" /> Converting to MP3
          </span>
        );
      case 'tagging':
        return (
          <span className="flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <Tag className="w-3 h-3" /> Tagging ID3
          </span>
        );
      case 'completed':
        return (
          <span className="flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-3 h-3" /> Ready
          </span>
        );
      case 'error':
        return (
          <span className="flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20" title={track.error_message || ''}>
            <AlertCircle className="w-3 h-3" /> Failed
          </span>
        );
      case 'cancelled':
        return (
          <span className="text-[11px] font-medium px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-400 border border-zinc-700">
            Cancelled
          </span>
        );
      default:
        return (
          <span className="text-[11px] font-medium px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-400 border border-zinc-700">
            Queued
          </span>
        );
    }
  };

  const isDownloading = track.status === 'downloading' || track.status === 'retrying' || track.status === 'converting' || track.status === 'tagging';

  return (
    <div className="bg-zinc-900/90 border border-zinc-800/80 rounded-xl p-3.5 flex flex-col gap-2.5 hover:border-zinc-700 transition">
      <div className="flex items-center justify-between gap-3">
        {/* Thumbnail & Title/Artist */}
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-12 h-12 rounded-lg bg-zinc-800 shrink-0 overflow-hidden border border-zinc-700/60 flex items-center justify-center">
            {track.thumbnail_url ? (
              <img src={track.thumbnail_url} alt={track.title} className="w-full h-full object-cover" />
            ) : (
              <Music className="w-5 h-5 text-zinc-500" />
            )}
          </div>

          <div className="min-w-0">
            <div className="flex items-center gap-1.5">
              <h3 className="text-sm font-semibold text-zinc-100 truncate">{track.title}</h3>
              <a 
                href={track.spotify_url} 
                target="_blank" 
                rel="noreferrer" 
                className="text-zinc-500 hover:text-emerald-400 transition shrink-0"
                title="Open on Spotify"
              >
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>
            <p className="text-xs text-zinc-400 truncate">{track.artist}</p>
          </div>
        </div>

        {/* Status Badge & Actions */}
        <div className="flex items-center gap-2 shrink-0">
          {getStatusBadge()}

          {/* Action buttons */}
          {isDownloading ? (
            <button
              onClick={() => onCancel(track.id)}
              className="p-1.5 rounded-lg bg-zinc-800 hover:bg-rose-500/20 hover:text-rose-400 text-zinc-400 transition"
              title="Cancel download"
            >
              <X className="w-4 h-4" />
            </button>
          ) : track.status === 'error' || track.status === 'cancelled' ? (
            <button
              onClick={() => onRetry(track.id)}
              className="p-1.5 rounded-lg bg-zinc-800 hover:bg-emerald-500/20 hover:text-emerald-400 text-zinc-400 transition"
              title="Retry download"
            >
              <RotateCw className="w-4 h-4" />
            </button>
          ) : null}
        </div>
      </div>

      {/* Progress Bar & Speed Indicator */}
      {isDownloading && (
        <div className="space-y-1">
          <div className="w-full bg-zinc-800 h-1.5 rounded-full overflow-hidden">
            <div
              className="bg-gradient-to-r from-emerald-500 to-green-400 h-full rounded-full transition-all duration-300"
              style={{ width: `${Math.max(track.progress, 5)}%` }}
            />
          </div>
          <div className="flex justify-between items-center text-[10px] text-zinc-400">
            <span>{track.progress.toFixed(0)}%</span>
            <div className="flex gap-2">
              {track.speed && <span>{track.speed}</span>}
              {track.eta && <span>ETA: {track.eta}</span>}
            </div>
          </div>
        </div>
      )}

      {/* Error message detail if present */}
      {track.status === 'error' && track.error_message && (
        <p className="text-[11px] text-rose-400/90 bg-rose-500/5 px-2.5 py-1 rounded border border-rose-500/10 truncate">
          {track.error_message}
        </p>
      )}
    </div>
  );
};
