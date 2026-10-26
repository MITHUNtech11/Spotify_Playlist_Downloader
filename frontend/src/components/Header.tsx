import React from 'react';
import { Music, Folder, Usb, Settings, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { AppConfig } from '../types';

interface HeaderProps {
  config: AppConfig | null;
  onOpenSettings: () => void;
  onOpenUsbSync: () => void;
  activeCount: number;
}

export const Header: React.FC<HeaderProps> = ({
  config,
  onOpenSettings,
  onOpenUsbSync,
  activeCount,
}) => {
  return (
    <header className="border-b border-zinc-800 bg-zinc-900/60 backdrop-blur-md sticky top-0 z-30 px-6 py-4">
      <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
        {/* Logo and Brand */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-600 to-green-400 flex items-center justify-center shadow-lg shadow-emerald-500/20">
            <Music className="w-5 h-5 text-black stroke-[2.5]" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-white">Spotify Downloader Pro</h1>
              <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                v1.0
              </span>
            </div>
            <p className="text-xs text-zinc-400">High-Fidelity Audio Extractor & USB Sync</p>
          </div>
        </div>

        {/* Global Controls & Status */}
        <div className="flex items-center gap-3 flex-wrap justify-end">
          {/* FFmpeg Warning if Missing */}
          {config && !config.ffmpeg_available && (
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-400 text-xs">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>FFmpeg missing</span>
            </div>
          )}

          {/* Folder Indicator */}
          <button
            onClick={onOpenSettings}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-zinc-800/80 hover:bg-zinc-800 border border-zinc-700/60 text-zinc-300 text-xs transition"
            title="Click to change folder"
          >
            <Folder className="w-3.5 h-3.5 text-emerald-400" />
            <span className="max-w-[140px] truncate">{config?.download_folder || 'Select folder'}</span>
          </button>

          {/* USB Sync Trigger Button */}
          <button
            onClick={onOpenUsbSync}
            className="flex items-center gap-2 px-3.5 py-1.5 rounded-lg bg-gradient-to-r from-emerald-600 to-green-500 hover:from-emerald-500 hover:to-green-400 text-black font-semibold text-xs shadow-md shadow-emerald-600/20 transition active:scale-95"
          >
            <Usb className="w-3.5 h-3.5 stroke-[2.5]" />
            <span>Sync to Pen Drive</span>
          </button>

          {/* Settings Button */}
          <button
            onClick={onOpenSettings}
            className="p-2 rounded-lg bg-zinc-800/80 hover:bg-zinc-800 border border-zinc-700/60 text-zinc-400 hover:text-zinc-200 transition"
            title="Application Settings"
          >
            <Settings className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
};
