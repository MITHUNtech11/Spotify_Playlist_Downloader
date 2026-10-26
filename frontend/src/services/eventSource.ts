import { ProgressEvent } from '../types';

export class SseEventService {
  private eventSource: EventSource | null = null;
  private listeners: ((event: ProgressEvent) => void)[] = [];
  private isConnecting = false;

  public connect(url: string = '/api/events') {
    if (this.eventSource || this.isConnecting) return;
    this.isConnecting = true;

    try {
      this.eventSource = new EventSource(url);

      this.eventSource.onmessage = (e) => {
        try {
          const data: ProgressEvent = JSON.parse(e.data);
          this.listeners.forEach((listener) => listener(data));
        } catch {
          // Ignore ping or non-json message
        }
      };

      this.eventSource.onerror = () => {
        // Automatically reconnect after a delay
        this.eventSource?.close();
        this.eventSource = null;
        this.isConnecting = false;
        setTimeout(() => this.connect(url), 3000);
      };

      this.eventSource.onopen = () => {
        this.isConnecting = false;
      };
    } catch {
      this.isConnecting = false;
    }
  }

  public subscribe(callback: (event: ProgressEvent) => void): () => void {
    this.listeners.push(callback);
    return () => {
      this.listeners = this.listeners.filter((l) => l !== callback);
    };
  }

  public disconnect() {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
    this.isConnecting = false;
  }
}

export const sseService = new SseEventService();
