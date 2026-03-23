import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SPOTIPY_CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
SPOTIPY_CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')
PLAYLIST_ID = os.getenv('PLAYLIST_ID')

def export_playlist_to_txt(client_id, client_secret, playlist_id, output_file='songs.txt'):
    """Export Spotify playlist to a text file"""
    
    try:
        print("🔐 Authenticating with Spotify...")
        auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
        sp = spotipy.Spotify(auth_manager=auth_manager)
        
        print(f"📂 Fetching playlist ({playlist_id})...")
        results = sp.playlist_tracks(playlist_id)
        tracks = results['items']
        
        # Handle pagination
        while results['next']:
            results = sp.next(results)
            tracks.extend(results['items'])
        
        # Extract song info
        songs = []
        for item in tracks:
            track = item['track']
            if track:
                name = track['name']
                artist = track['artists'][0]['name']
                song = f"{name} - {artist}"
                songs.append(song)
                print(f"  ✓ {song}")
        
        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(songs))
        
        print(f"\n✅ Exported {len(songs)} songs to {output_file}")
        print("\nNow run: python script_manual.py")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"\nMake sure your .env file has:")
        print(f"  SPOTIPY_CLIENT_ID")
        print(f"  SPOTIPY_CLIENT_SECRET")
        print(f"  PLAYLIST_ID")

if __name__ == "__main__":
    if not SPOTIPY_CLIENT_ID or not SPOTIPY_CLIENT_SECRET or not PLAYLIST_ID:
        print("❌ Missing credentials in .env file!")
        print("\nAdd these to .env:")
        print("  SPOTIPY_CLIENT_ID=your_id")
        print("  SPOTIPY_CLIENT_SECRET=your_secret")
        print("  PLAYLIST_ID=your_playlist_id")
    else:
        export_playlist_to_txt(SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, PLAYLIST_ID)
