import React, { useState, useEffect } from 'react';
import { 
  Usb, 
  X, 
  RotateCw, 
  HardDrive, 
  CheckCircle2, 
  AlertTriangle, 
  ArrowRight,
  ShieldCheck,
  Loader2
} from 'lucide-react';
import { UsbDrive, UsbSyncSummary, ProgressEvent } from '../types';
import { fetchUsbDrives, analyzeUsbSync, startUsbSync } from '../services/api';

interface UsbSyncModalProps {
  isOpen: boolean;
  onClose: () => void;
  syncProgress: ProgressEvent | null;
}

export const UsbSyncModal: React.FC<UsbSyncModalProps> = ({ isOpen, onClose, syncProgress }) => {
  const [drives, setDrives] = useState<UsbDrive[]>([]);
  const [selectedDrive, setSelectedDrive] = useState<string>('');
  const [targetSubfolder, setTargetSubfolder] = useState<string>('');
  const [summary, setSummary] = useState<UsbSyncSummary | null>(null);
  const [loadingDrives, setLoadingDrives] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      loadDrives();
    }
  }, [isOpen]);

  // Track completion of sync
  useEffect(() => {
    if (syncProgress?.status === 'completed') {
      setSyncing(false);
      // Refresh analysis
      if (selectedDrive) {
        handleAnalyze(selectedDrive);
      }
    }
  }, [syncProgress]);

  const loadDrives = async () => {
    setLoadingDrives(true);
    setError(null);
    try {
      const list = await fetchUsbDrives();
      setDrives(list);
      if (list.length > 0 && !selectedDrive) {
        setSelectedDrive(list[0].drive_letter);
        handleAnalyze(list[0].drive_letter);
      }
    } catch (e: any) {
      setError(e.message || 'Failed to detect drives');
    } finally {
      setLoadingDrives(false);
    }
  };

  const handleAnalyze = async (driveLetter: string) => {
    setAnalyzing(true);
    setError(null);
    try {
      const res = await analyzeUsbSync(driveLetter, targetSubfolder || undefined);
      setSummary(res);
    } catch (e: any) {
      setError(e.message || 'Analysis failed');
    } finally {
      setAnalyzing(false);
    }
  };

  const handleStartSync = async () => {
    if (!selectedDrive) return;
    setSyncing(true);
    setError(null);
    try {
      await startUsbSync(selectedDrive, targetSubfolder || undefined);
    } catch (e: any) {
      setError(e.message || 'Sync failed to start');
      setSyncing(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-xl overflow-hidden shadow-2xl animate-in fade-in zoom-in-95 duration-200">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-zinc-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
              <Usb className="w-5 h-5 stroke-[2.5]" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white">Sync to Pen Drive / USB</h2>
              <p className="text-xs text-zinc-400">Smart SHA-256 deduplicated file sync for car music</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg bg-zinc-800 text-zinc-400 hover:text-white transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-5">
          {error && (
            <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Drive Selector */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs font-medium text-zinc-300">
              <label>Select Target Drive Letter</label>
              <button
                onClick={loadDrives}
                disabled={loadingDrives}
                className="flex items-center gap-1 text-emerald-400 hover:text-emerald-300 transition"
              >
                <RotateCw className={`w-3 h-3 ${loadingDrives ? 'animate-spin' : ''}`} />
                <span>Refresh Drives</span>
              </button>
            </div>

            {drives.length === 0 ? (
              <div className="p-4 rounded-xl bg-zinc-950/80 border border-dashed border-zinc-800 text-center">
                <HardDrive className="w-8 h-8 text-zinc-600 mx-auto mb-2" />
                <p className="text-xs text-zinc-400">No external or pen drives detected</p>
                <p className="text-[11px] text-zinc-500 mt-1">Plug in your USB flash drive and click Refresh.</p>
              </div>
            ) : (
              <select
                value={selectedDrive}
                onChange={(e) => {
                  setSelectedDrive(e.target.value);
                  handleAnalyze(e.target.value);
                }}
                disabled={syncing}
                className="w-full px-3.5 py-2.5 bg-zinc-950 border border-zinc-800 rounded-xl text-zinc-200 text-sm focus:outline-none focus:border-emerald-500"
              >
                {drives.map((d) => (
                  <option key={d.drive_letter} value={d.drive_letter}>
                    {d.drive_letter} ({d.volume_name}) - {d.free_gb} GB free of {d.total_gb} GB
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* Target subfolder on drive */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-zinc-300">Target Folder on Drive (Optional)</label>
            <input
              type="text"
              value={targetSubfolder}
              onChange={(e) => setTargetSubfolder(e.target.value)}
              placeholder="e.g. Music or leave blank for root"
              disabled={syncing}
              className="w-full px-3.5 py-2 bg-zinc-950 border border-zinc-800 rounded-xl text-zinc-200 text-xs placeholder-zinc-600 focus:outline-none focus:border-emerald-500"
            />
          </div>

          {/* Deduplication & Capacity Analysis Card */}
          {analyzing ? (
            <div className="p-4 rounded-xl bg-zinc-950/60 border border-zinc-800 text-center text-xs text-zinc-400 flex items-center justify-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin text-emerald-400" />
              <span>Analyzing USB contents with SHA-256...</span>
            </div>
          ) : summary ? (
            <div className="p-4 rounded-xl bg-zinc-950 border border-zinc-800 space-y-3">
              <div className="flex items-center justify-between text-xs pb-2 border-b border-zinc-800/80">
                <span className="text-zinc-400">Source Library Songs</span>
                <span className="font-semibold text-zinc-200">{summary.total_source_tracks} tracks</span>
              </div>

              <div className="flex items-center justify-between text-xs">
                <span className="text-zinc-400 flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  Already on Drive (Will Skip)
                </span>
                <span className="font-semibold text-emerald-400">{summary.already_synced_tracks} tracks</span>
              </div>

              <div className="flex items-center justify-between text-xs">
                <span className="text-zinc-400 flex items-center gap-1.5">
                  <ArrowRight className="w-3.5 h-3.5 text-green-400" />
                  New Songs to Copy
                </span>
                <span className="font-semibold text-white">
                  {summary.new_tracks_to_copy} tracks ({summary.estimated_size_mb} MB)
                </span>
              </div>

              {!summary.enough_space && (
                <div className="p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 shrink-0" />
                  <span>Not enough free space on the selected drive!</span>
                </div>
              )}
            </div>
          ) : null}

          {/* Sync Progress Bar */}
          {syncing && syncProgress && (
            <div className="space-y-2 p-4 rounded-xl bg-zinc-950 border border-emerald-500/30">
              <div className="flex justify-between items-center text-xs">
                <span className="text-emerald-400 font-medium truncate max-w-[300px]">
                  {syncProgress.current_file || 'Copying files...'}
                </span>
                <span className="text-zinc-400 font-semibold">{syncProgress.percent || 0}%</span>
              </div>
              <div className="w-full bg-zinc-800 h-2 rounded-full overflow-hidden">
                <div
                  className="bg-emerald-500 h-full rounded-full transition-all duration-200"
                  style={{ width: `${syncProgress.percent || 0}%` }}
                />
              </div>
              <div className="text-[11px] text-zinc-500 text-right">
                Copied {syncProgress.copied || 0} of {syncProgress.total || 0}
              </div>
            </div>
          )}

          {/* Deduplication Guarantee Note */}
          <div className="flex items-center gap-2 text-[11px] text-zinc-500 bg-zinc-800/40 p-2.5 rounded-xl border border-zinc-800">
            <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>Files are compared via SHA-256 hashes so songs are never duplicated, even if renamed on your pen drive.</span>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-4 bg-zinc-950/80 border-t border-zinc-800 flex justify-end gap-3">
          <button
            onClick={onClose}
            disabled={syncing}
            className="px-4 py-2 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs font-medium transition"
          >
            Close
          </button>

          <button
            onClick={handleStartSync}
            disabled={syncing || !summary || summary.new_tracks_to_copy === 0 || !summary.enough_space}
            className="flex items-center gap-2 px-5 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 disabled:opacity-40 disabled:cursor-not-allowed text-black font-semibold text-xs transition shadow-md shadow-emerald-500/10 active:scale-95"
          >
            {syncing ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Syncing...</span>
              </>
            ) : (
              <>
                <Usb className="w-3.5 h-3.5 stroke-[2.5]" />
                <span>Sync {summary?.new_tracks_to_copy || 0} Songs</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
