import React, { useState, useEffect, useCallback } from 'react';
import { 
  fetchConfig, 
  updateConfig, 
  resolveSpotifyLinks, 
  fetchQueue, 
  startDownloads, 
  cancelDownload 
} from './services/api';
import { sseService } from './services/eventSource';
import { TrackItem, AppConfig, ProgressEvent } from './types';
import { Header } from './components/Header';
import { UrlInputBar } from './components/UrlInputBar';
import { DownloadQueue } from './components/DownloadQueue';
import { UsbSyncModal } from './components/UsbSyncModal';
import { SettingsModal } from './components/SettingsModal';
import { CheckCircle2, AlertCircle, Info, X } from 'lucide-react';

interface Toast {
  message: string;
  type: 'success' | 'error' | 'info';
}

export default function App() {
  const [tracks, setTracks] = useState<TrackItem[]>([]);
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [syncProgress, setSyncProgress] = useState<ProgressEvent | null>(null);
  
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isUsbModalOpen, setIsUsbModalOpen] = useState(false);
  const [isResolving, setIsResolving] = useState(false);
  const [toast, setToast] = useState<Toast | null>(null);

  const showToast = (message: string, type: 'success' | 'error' | 'info' = 'info') => {
    setToast({ message, type });
    setTimeout(() => {
      setToast((prev) => (prev?.message === message ? null : prev));
    }, 4500);
  };

  // Initial bootstrap
  useEffect(() => {
    const bootstrap = async () => {
      try {
        const [loadedConfig, loadedQueue] = await Promise.all([
          fetchConfig(),
          fetchQueue(),
        ]);
        setConfig(loadedConfig);
        setTracks(loadedQueue);
      } catch (err: any) {
        showToast(err.message || 'Failed to connect to backend', 'error');
      }
    };

    bootstrap();

    // Connect SSE stream
    sseService.connect('/api/events');

    const unsubscribe = sseService.subscribe((event: ProgressEvent) => {
      if (event.type === 'usb_sync_progress') {
        setSyncProgress(event);
      } else if (event.track_id) {
        setTracks((prevTracks) =>
          prevTracks.map((t) => {
            if (t.id === event.track_id) {
              return {
                ...t,
                progress: event.progress !== undefined ? event.progress : t.progress,
                speed: event.speed !== undefined ? event.speed : t.speed,
                eta: event.eta !== undefined ? event.eta : t.eta,
                status: event.status !== undefined ? event.status : t.status,
                error_message: event.error_message !== undefined ? event.error_message : t.error_message,
              };
            }
            return t;
          })
        );
      }
    });

    return () => {
      unsubscribe();
      sseService.disconnect();
    };
  }, []);

  const handleResolve = async (input: string) => {
    setIsResolving(true);
    try {
      const resolved = await resolveSpotifyLinks(input);
      if (resolved.length === 0) {
        showToast('No valid Spotify track, album, or playlist links found.', 'info');
      } else {
        // Merge into existing tracks without duplicate IDs
        setTracks((prev) => {
          const map = new Map<string, TrackItem>();
          prev.forEach((t) => map.set(t.id, t));
          resolved.forEach((t) => map.set(t.id, t));
          return Array.from(map.values());
        });
        showToast(`Loaded and queued ${resolved.length} track(s)!`, 'success');
      }
    } catch (err: any) {
      showToast(err.message || 'Failed to resolve links', 'error');
    } finally {
      setIsResolving(false);
    }
  };

  const handleStartDownloads = async (ids?: string[]) => {
    try {
      await startDownloads(ids);
      showToast('Download started in background!', 'success');
    } catch (err: any) {
      showToast(err.message || 'Failed to start downloads', 'error');
    }
  };

  const handleCancel = async (id: string) => {
    try {
      await cancelDownload(id);
      showToast('Download cancelled', 'info');
    } catch (err: any) {
      showToast(err.message || 'Failed to cancel', 'error');
    }
  };

  const handleRetry = async (id: string) => {
    await handleStartDownloads([id]);
  };

  const handleClearCompleted = () => {
    setTracks((prev) => prev.filter((t) => t.status !== 'completed' && !t.already_downloaded));
    showToast('Cleared completed downloads from queue view', 'info');
  };

  const handleSaveConfig = async (data: { download_folder?: string; max_threads?: number }) => {
    try {
      const updated = await updateConfig(data);
      setConfig(updated);
      showToast('Settings saved successfully', 'success');
    } catch (err: any) {
      showToast(err.message || 'Failed to save settings', 'error');
      throw err;
    }
  };

  const activeCount = tracks.filter((t) => t.status === 'downloading' || t.status === 'converting' || t.status === 'tagging').length;

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 flex flex-col font-sans">
      {/* Toast Notification */}
      {toast && (
        <div className="fixed bottom-6 right-6 z-50 flex items-center gap-2.5 px-4 py-3 rounded-xl shadow-2xl border text-xs font-medium animate-in slide-in-from-bottom-5 duration-200 backdrop-blur-md bg-zinc-900/95 border-zinc-700">
          {toast.type === 'success' && <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />}
          {toast.type === 'error' && <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />}
          {toast.type === 'info' && <Info className="w-4 h-4 text-blue-400 shrink-0" />}
          <span className="text-zinc-200 max-w-sm">{toast.message}</span>
          <button onClick={() => setToast(null)} className="ml-2 text-zinc-500 hover:text-zinc-300">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Main Top Header */}
      <Header
        config={config}
        onOpenSettings={() => setIsSettingsOpen(true)}
        onOpenUsbSync={() => setIsUsbModalOpen(true)}
        activeCount={activeCount}
      />

      {/* Main Container */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-4 sm:px-6 py-6 sm:py-8 space-y-6">
        {/* Link Input Section */}
        <UrlInputBar onResolve={handleResolve} isLoading={isResolving} />

        {/* Download Queue Section */}
        <DownloadQueue
          tracks={tracks}
          onStartDownloads={handleStartDownloads}
          onCancel={handleCancel}
          onRetry={handleRetry}
          onClearCompleted={handleClearCompleted}
        />
      </main>

      {/* Modals */}
      <UsbSyncModal
        isOpen={isUsbModalOpen}
        onClose={() => setIsUsbModalOpen(false)}
        syncProgress={syncProgress}
      />

      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        config={config}
        onSave={handleSaveConfig}
      />
    </div>
  );
}
