import os
import sys
import time
import webbrowser
import threading
import uvicorn

# Configure console for UTF-8
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

def open_browser():
    time.sleep(1.2)
    url = "http://127.0.0.1:8000"
    print(f"\n🚀 Opening Spotify Downloader Pro in your browser: {url}")
    webbrowser.open(url)

def main():
    print("=" * 60)
    print("       🎵 SPOTIFY DOWNLOADER PRO (WEB PRODUCT) 🎵")
    print("=" * 60)
    print("Starting local backend server...")

    # Launch browser automatically in a background daemon thread
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()

    # Run Uvicorn server
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        log_level="info",
        reload=False
    )

if __name__ == "__main__":
    main()
