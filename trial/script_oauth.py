import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import yt_dlp
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
SPOTIPY_CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
SPOTIPY_CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')
PLAYLIST_ID = os.getenv('PLAYLIST_ID')
DOWNLOAD_FOLDER = os.getenv('DOWNLOAD_FOLDER', './Dad_Car_Songs')

# Validate required environment variables
if not SPOTIPY_CLIENT_ID or not SPOTIPY_CLIENT_SECRET:
    raise ValueError("Missing SPOTIPY_CLIENT_ID or SPOTIPY_CLIENT_SECRET in .env file")

# OAuth scopes needed to access user's playlists
SCOPES = ['playlist-read-private', 'playlist-read-collaborative']

# --- 1. Fetch Songs from Spotify using OAuth ---
def get_playlist_tracks(client_id, client_secret, playlist_id):
    print("Authenticating with Spotify API (OAuth)...")
    
    # Create OAuth auth manager
    # This will open a browser on first run for user authorization
    sp_oauth = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri="http://127.0.0.1:8888/callback",
        scope=SCOPES,
        cache_path=".cache"
    )
    
    sp = spotipy.Spotify(auth_manager=sp_oauth)
    
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
        if track:  # Ensure track exists
            name = track['name']
            artist = track['artists'][0]['name']
            # Create a highly specific search query for YouTube
            query = f"{name} {artist} official audio"
            song_queries.append(query)
            print(f"  Added: {query}")
    
    return song_queries

# --- 2. Download MP3s using yt-dlp ---
def download_songs(song_queries, output_path):
    # Create the folder if it doesn't exist
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    # yt-dlp configuration options
    ydl_opts = {
        'format': 'bestaudio/best',  # Grab the best audio quality available
        'outtmpl': f'{output_path}/%(title)s.%(ext)s',  # Output filename template
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',  # Good quality for car speakers
        }],
        'noplaylist': True,
        'quiet': False,  # Set to True if you want less text in the terminal
        'extract_flat': False
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for i, query in enumerate(song_queries, 1):
            print(f"\n[{i}/{len(song_queries)}] Searching and downloading: {query}")
            try:
                # The 'ytsearch1:' tells yt-dlp to grab the top 1 result from YouTube search
                ydl.extract_info(f"ytsearch1:{query}", download=True)
            except Exception as e:
                print(f"⚠️  Error downloading {query}: {e}")
                # The script will skip the broken song and continue

# --- Main Execution ---
if __name__ == "__main__":
    try:
        songs_to_download = get_playlist_tracks(SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, PLAYLIST_ID)
        
        print(f"\n✅ Found {len(songs_to_download)} songs. Starting download...\n")
        download_songs(songs_to_download, DOWNLOAD_FOLDER)
        print("\n✅ All downloads complete!")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Make sure your .env file has valid SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, and PLAYLIST_ID")
