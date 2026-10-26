import React, { useState } from 'react';
import { Settings, X, Folder, Cpu, AlertTriangle, CheckCircle2, Save, Terminal } from 'lucide-react';
import { AppConfig } from '../types';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  config: AppConfig | null;
  onSave: (data: { download_folder?: string; max_threads?: number }) => Promise<void>;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  config,
  onSave,
}) => {
  const [downloadFolder, setDownloadFolder] = useState(config?.download_folder || './Dad_Car_Songs');
  const [maxThreads, setMaxThreads] = useState(config?.max_threads || 3);
  const [saving, setSaving] = useState(false);

  if (!isOpen) return null;

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await onSave({ download_folder: downloadFolder, max_threads: Number(maxThreads) });
      onClose();
    } catch {
      // error handled in parent
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl animate-in fade-in zoom-in-95 duration-200">
        <div className="px-6 py-4 border-b border-zinc-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-zinc-800 text-zinc-300">
              <Settings className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white">Application Settings</h2>
              <p className="text-xs text-zinc-400">Configure storage directory and download parameters</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg bg-zinc-800 text-zinc-400 hover:text-white">
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSave} className="p-6 space-y-5">
          {/* Download Folder */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-zinc-300 flex items-center gap-1.5">
              <Folder className="w-3.5 h-3.5 text-emerald-400" />
              Download Destination Directory
            </label>
            <input
              type="text"
              value={downloadFolder}
              onChange={(e) => setDownloadFolder(e.target.value)}
              placeholder="./Dad_Car_Songs"
              className="w-full px-3.5 py-2.5 bg-zinc-950 border border-zinc-800 rounded-xl text-zinc-200 text-sm focus:outline-none focus:border-emerald-500 font-mono"
            />
            <p className="text-[11px] text-zinc-500">
              High-quality MP3s with embedded album artwork and ID3 tags are saved here.
            </p>
          </div>

          {/* Concurrent Threads */}
          <div className="space-y-1.5">
            <div className="flex justify-between items-center text-xs font-medium text-zinc-300">
              <label className="flex items-center gap-1.5">
                <Cpu className="w-3.5 h-3.5 text-blue-400" />
                Concurrent Download Threads
              </label>
              <span className="text-emerald-400 font-semibold">{maxThreads} parallel downloads</span>
            </div>
            <input
              type="range"
              min={1}
              max={8}
              value={maxThreads}
              onChange={(e) => setMaxThreads(Number(e.target.value))}
              className="w-full accent-emerald-500 bg-zinc-800 h-2 rounded-lg"
            />
            <p className="text-[11px] text-zinc-500">
              Recommended: 3 threads to prevent YouTube 429 rate-limiting.
            </p>
          </div>

          {/* FFmpeg Status Banner */}
          <div className="p-3.5 rounded-xl bg-zinc-950 border border-zinc-800 space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-zinc-400 font-medium">FFmpeg Audio Extraction Engine</span>
              {config?.ffmpeg_available ? (
                <span className="flex items-center gap-1 text-emerald-400 text-[11px] font-semibold">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Installed & Active
                </span>
              ) : (
                <span className="flex items-center gap-1 text-amber-400 text-[11px] font-semibold">
                  <AlertTriangle className="w-3.5 h-3.5" /> Missing
                </span>
              )}
            </div>

            {config?.ffmpeg_available ? (
              <p className="text-[11px] text-zinc-500 font-mono truncate">
                Path: {config.ffmpeg_path || 'System PATH'}
              </p>
            ) : (
              <div className="space-y-1">
                <p className="text-[11px] text-amber-300/80">
                  FFmpeg is required for MP3 conversion. Install it on Windows using PowerShell:
                </p>
                <div className="flex items-center gap-2 p-2 rounded bg-zinc-900 border border-zinc-800 font-mono text-[11px] text-zinc-300">
                  <Terminal className="w-3 h-3 text-zinc-500" />
                  <code>winget install Gyan.FFmpeg</code>
                </div>
              </div>
            )}
          </div>

          {/* Footer actions */}
          <div className="pt-2 flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs font-medium transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="flex items-center gap-2 px-5 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-black font-semibold text-xs transition shadow-md shadow-emerald-500/10 active:scale-95"
            >
              <Save className="w-3.5 h-3.5 stroke-[2.5]" />
              <span>{saving ? 'Saving...' : 'Save Settings'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
