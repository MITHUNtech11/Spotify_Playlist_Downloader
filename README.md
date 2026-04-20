# Spotify Playlist Downloader

A Python tool to convert Spotify playlist track URLs into song names and automatically download the corresponding audio from YouTube, saving them as MP3 files. Designed for easy batch downloading and organization of your favorite playlists.

## Features

- **Convert Spotify Track URLs:** Extracts song names and artists from Spotify track URLs (no API key required).
- **Batch Download:** Downloads songs from YouTube using multithreading for speed.
- **Duplicate Handling:** Skips already-downloaded songs and removes duplicates.
- **Logging:** Detailed logs for every session and step.
- **Preview & Confirmation:** Shows a summary before downloading and asks for user confirmation.
- **Cleanup:** Removes incomplete downloads automatically.
- **Custom Download Folder:** Set your preferred download location via `.env` or defaults.

## Requirements

- Python 3.8+
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [requests](https://pypi.org/project/requests/)
- [beautifulsoup4](https://pypi.org/project/beautifulsoup4/)
- [python-dotenv](https://pypi.org/project/python-dotenv/)

Install dependencies (if using a virtual environment, activate it first):

```bash
pip install yt-dlp requests beautifulsoup4 python-dotenv
```

## Usage

1. **Prepare Your Track URLs:**
   - Add Spotify track URLs (one per line) to `track_urls.txt`.

2. **Configure Download Folder (Optional):**
   - Create a `.env` file and set:
     ```
     DOWNLOAD_FOLDER=./Dad_Car_Songs
     ```
   - Or use the default folder.

3. **Run the Downloader:**
   ```bash
   python playlist_downloader_combined.py
   ```
   - The script will:
     - Convert Spotify URLs to song names (`songs.txt`).
     - Show a preview and ask for confirmation.
     - Download new songs as MP3s to your chosen folder.
     - Log all actions in `download_log.txt`.

4. **Check Your Songs:**
   - Downloaded songs are saved in the specified folder.
   - See `songs.txt` for the list of extracted song names.

## File Structure

- `playlist_downloader_combined.py` — Main script for the full workflow.
- `track_urls.txt` — Input: Spotify track URLs.
- `songs.txt` — Output: Extracted song names.
- `download_log.txt` — Log file for all actions.
- `Dad_Car_Songs/` — Default download folder (can be changed).
- `copy_to_pendrive.py` — (Optional) Utility to copy downloaded songs to a USB drive, avoiding duplicates.

## Example

**track_urls.txt:**
```
https://open.spotify.com/track/2109dBho14Lqh2wr8goqAP
https://open.spotify.com/track/3jrOziEVwpJAETyEDZ5HWa
```

**songs.txt (output):**
```
Athi Kaalai Kaatre Nillu - S. Janaki
Kadhalikum Pennin - A.R. Rahman, S. P. Balasubrahmanyam
...
```

## Notes

- The script scrapes Spotify web pages for song info (no API key needed).
- Downloads use YouTube search for best match (may not always be perfect).
- For large playlists, the process may take time depending on your internet speed.

## Troubleshooting

- If you see errors about missing modules, ensure all dependencies are installed.
- If downloads fail, check your internet connection and YouTube accessibility.
- For permission issues, try running the terminal as administrator.

## License

MIT License
