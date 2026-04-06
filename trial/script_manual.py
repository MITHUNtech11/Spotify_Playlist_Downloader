import os
import yt_dlp
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

DOWNLOAD_FOLDER = os.getenv('DOWNLOAD_FOLDER', './Dad_Car_Songs')

# --- Songs List (manually enter from your Spotify playlist) ---
SONGS = [
    # Format: "Song Name | Artist Name"
    # Example:
    # "Bohemian Rhapsody | Queen",
    # "Hotel California | Eagles",
]

def load_songs_from_file(filename='songs.txt'):
    """Load songs from a text file if it exists"""
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            songs = [line.strip() for line in f if line.strip()]
            return songs
    return SONGS

def download_songs(songs_list, output_path):
    """Download MP3s from song list"""
    if not songs_list:
        print("❌ No songs provided!")
        print("\nOption 1: Create songs.txt file with songs (one per line)")
        print("  Format: Song Name - Artist Name")
        print("\nOption 2: Edit this script and add songs to SONGS list")
        return
    
    # Create the folder if it doesn't exist
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    # yt-dlp configuration
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'{output_path}/%(title)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'noplaylist': True,
        'quiet': False,
        'extract_flat': False
    }

    print(f"📁 Downloading to: {os.path.abspath(output_path)}\n")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for i, song in enumerate(songs_list, 1):
            print(f"[{i}/{len(songs_list)}] 🎵 Searching: {song}")
            try:
                # Search YouTube for the song
                query = f"{song} official audio"
                ydl.extract_info(f"ytsearch1:{query}", download=True)
                print(f"  ✅ Downloaded!\n")
            except Exception as e:
                print(f"  ⚠️  Error: {e}\n")

# --- Main ---
if __name__ == "__main__":
    # Try loading from songs.txt, fall back to hardcoded list
    songs = load_songs_from_file('songs.txt')
    
    if not songs:
        print("❌ No songs found!")
        print("\nCreate a songs.txt file in this folder with one song per line:")
        print("  Song Name - Artist Name")
        print("  Song Name 2 - Artist Name 2")
    else:
        print(f"🎵 Found {len(songs)} songs\n")
        download_songs(songs, DOWNLOAD_FOLDER)
        print("\n✅ All done!")
