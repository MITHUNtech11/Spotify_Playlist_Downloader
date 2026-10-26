import { TrackItem, AppConfig, UsbDrive, UsbSyncSummary } from '../types';

const BASE_URL = import.meta.env.VITE_API_BASE || '';

export async function fetchConfig(): Promise<AppConfig> {
  const res = await fetch(`${BASE_URL}/api/config`);
  if (!res.ok) throw new Error('Failed to load configuration');
  return res.json();
}

export async function updateConfig(data: { download_folder?: string; max_threads?: number }): Promise<AppConfig> {
  const res = await fetch(`${BASE_URL}/api/config`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Failed to update configuration');
  return res.json();
}

export async function resolveSpotifyLinks(input: string | string[]): Promise<TrackItem[]> {
  const payload = Array.isArray(input) ? { urls: input } : { input };
  const res = await fetch(`${BASE_URL}/api/resolve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error('Failed to resolve Spotify links');
  return res.json();
}

export async function fetchQueue(): Promise<TrackItem[]> {
  const res = await fetch(`${BASE_URL}/api/downloads/queue`);
  if (!res.ok) throw new Error('Failed to fetch download queue');
  return res.json();
}

export async function startDownloads(trackIds?: string[]): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/downloads/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(trackIds ? { track_ids: trackIds } : {}),
  });
  if (!res.ok) throw new Error('Failed to start downloads');
}

export async function cancelDownload(trackId: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/downloads/cancel/${trackId}`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to cancel download');
}

export async function fetchUsbDrives(): Promise<UsbDrive[]> {
  const res = await fetch(`${BASE_URL}/api/usb/drives`);
  if (!res.ok) throw new Error('Failed to scan USB drives');
  return res.json();
}

export async function analyzeUsbSync(driveLetter: string, targetSubfolder?: string): Promise<UsbSyncSummary> {
  const res = await fetch(`${BASE_URL}/api/usb/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ drive_letter: driveLetter, target_subfolder: targetSubfolder }),
  });
  if (!res.ok) throw new Error('Failed to analyze USB drive');
  return res.json();
}

export async function startUsbSync(driveLetter: string, targetSubfolder?: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/usb/sync`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ drive_letter: driveLetter, target_subfolder: targetSubfolder }),
  });
  if (!res.ok) throw new Error('Failed to start USB sync');
}
