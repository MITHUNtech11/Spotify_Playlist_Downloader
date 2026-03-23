import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import yt_dlp

# --- Configuration ---
# Treat these like your backend environment variables
SPOTIPY_CLIENT_ID = 'YOUR_CLIENT_ID'
SPOTIPY_CLIENT_SECRET = 'YOUR_CLIENT_SECRET'

# The ID of your dad's playlist (found in the Spotify URL)
# Example: https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M -> ID is 37i9dQZF1DXcBWIGoYBM5M
PLAYLIST_ID = 'YOUR_PLAYLIST_ID' 
DOWNLOAD_FOLDER = './Dad_Car_Songs'

# --- 1. Fetch Songs from Spotify ---
def get_playlist_tracks(client_id, client_secret, playlist_id):
    print("Authenticating with Spotify API...")
    auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
    sp = spotipy.Spotify(auth_manager=auth_manager)

    print("Fetching playlist data...")
    results = sp.playlist_tracks(playlist_id)
    tracks = results['items']
    
    # Handle pagination if the playlist has more than 100 songs
    while results['next']:
        results = sp.next(results)
        tracks.extend(results['items'])

    song_queries = []
    for item in tracks:
        track = item['track']
        if track: # Ensure track exists
            name = track['name']
            artist = track['artists'][0]['name']
            # Create a highly specific search query for YouTube
            query = f"{name} {artist} official audio"
            song_queries.append(query)
            
    return song_queries

# --- 2. Download MP3s using yt-dlp ---
def download_songs(song_queries, output_path):
    # Create the folder if it doesn't exist
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    # yt-dlp configuration options
    ydl_opts = {
        'format': 'bestaudio/best', # Grab the best audio quality available
        'outtmpl': f'{output_path}/%(title)s.%(ext)s', # Output filename template
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192', # Good quality for car speakers
        }],
        'noplaylist': True,
        'quiet': False, # Set to True if you want less text in the terminal
        'extract_flat': False
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for query in song_queries:
            print(f"\n--- Searching and downloading: {query} ---")
            try:
                # The 'ytsearch1:' tells yt-dlp to grab the top 1 result from YouTube search
                ydl.extract_info(f"ytsearch1:{query}", download=True)
            except Exception as e:
                print(f"Error downloading {query}: {e}")
                # The script will skip the broken song and continue

# --- Main Execution ---
if __name__ == "__main__":
    songs_to_download = get_playlist_tracks(SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, PLAYLIST_ID)
    
    print(f"Found {len(songs_to_download)} songs. Starting download...\n")
    download_songs(songs_to_download, DOWNLOAD_FOLDER)
    print("\nAll downloads complete!")