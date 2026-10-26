import React, { useState } from 'react';
import { 
  Play, 
  Trash2, 
  Search, 
  CheckCircle2, 
  Layers, 
  ListOrdered 
} from 'lucide-react';
import { TrackItem } from '../types';
import { TrackCard } from './TrackCard';

interface DownloadQueueProps {
  tracks: TrackItem[];
  onStartDownloads: (ids?: string[]) => void;
  onCancel: (id: string) => void;
  onRetry: (id: string) => void;
  onClearCompleted: () => void;
}

export const DownloadQueue: React.FC<DownloadQueueProps> = ({
  tracks,
  onStartDownloads,
  onCancel,
  onRetry,
  onClearCompleted,
}) => {
  const [search, setSearch] = useState('');

  const completedCount = tracks.filter((t) => t.status === 'completed' || t.already_downloaded).length;
  const activeCount = tracks.filter((t) => t.status === 'downloading' || t.status === 'converting' || t.status === 'tagging').length;
  const errorCount = tracks.filter((t) => t.status === 'error').length;
  const queuedCount = tracks.filter((t) => t.status === 'queued' && !t.already_downloaded).length;

  const filteredTracks = tracks.filter((t) => 
    t.title.toLowerCase().includes(search.toLowerCase()) ||
    t.artist.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-4">
      {/* Metrics Banner & Actions Bar */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 bg-zinc-900 border border-zinc-800 rounded-2xl p-4">
        {/* Metric Pills */}
        <div className="flex items-center gap-2 flex-wrap text-xs">
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-zinc-800/80 border border-zinc-700/60 text-zinc-300">
            <Layers className="w-3.5 h-3.5 text-zinc-400" />
            <span className="font-semibold">{tracks.length}</span> Total
          </div>

          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span className="font-semibold">{completedCount}</span> Downloaded
          </div>

          {activeCount > 0 && (
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-400 animate-pulse">
              <span className="font-semibold">{activeCount}</span> In Progress
            </div>
          )}

          {queuedCount > 0 && (
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-zinc-800 border border-zinc-700 text-zinc-400">
              <span className="font-semibold">{queuedCount}</span> Pending
            </div>
          )}

          {errorCount > 0 && (
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400">
              <span className="font-semibold">{errorCount}</span> Failed
            </div>
          )}
        </div>

        {/* Global Batch Action Buttons */}
        <div className="flex items-center gap-2 w-full md:w-auto justify-end">
          {queuedCount > 0 && (
            <button
              onClick={() => onStartDownloads()}
              disabled={activeCount > 0}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 text-black font-semibold text-xs transition shadow-md shadow-emerald-500/10"
            >
              <Play className="w-3.5 h-3.5 fill-black stroke-none" />
              <span>Download Pending ({queuedCount})</span>
            </button>
          )}

          {completedCount > 0 && (
            <button
              onClick={onClearCompleted}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs transition border border-zinc-700/60"
              title="Remove finished songs from queue view"
            >
              <Trash2 className="w-3.5 h-3.5 text-zinc-400" />
              <span>Clear Done</span>
            </button>
          )}
        </div>
      </div>

      {/* Search Filter if more than 5 tracks */}
      {tracks.length > 5 && (
        <div className="relative">
          <Search className="w-4 h-4 text-zinc-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search queued songs by title or artist..."
            className="w-full pl-10 pr-4 py-2 bg-zinc-900 border border-zinc-800 rounded-xl text-zinc-200 text-xs placeholder-zinc-500 focus:outline-none focus:border-emerald-500"
          />
        </div>
      )}

      {/* Cards List or Empty State */}
      {filteredTracks.length === 0 ? (
        <div className="text-center py-16 border-2 border-dashed border-zinc-800/80 rounded-2xl bg-zinc-900/30">
          <ListOrdered className="w-10 h-10 text-zinc-600 mx-auto mb-3" />
          <h4 className="text-sm font-semibold text-zinc-300">No tracks in queue</h4>
          <p className="text-xs text-zinc-500 mt-1 max-w-sm mx-auto">
            Paste a Spotify playlist, album, or track URL above to preview songs and download them as high-quality MP3s.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-2.5">
          {filteredTracks.map((track) => (
            <TrackCard
              key={track.id}
              track={track}
              onCancel={onCancel}
              onRetry={onRetry}
            />
          ))}
        </div>
      )}
    </div>
  );
};
