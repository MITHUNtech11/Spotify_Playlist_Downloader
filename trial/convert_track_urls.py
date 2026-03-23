import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv
import re

load_dotenv()

SPOTIPY_CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
SPOTIPY_CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')

def extract_track_ids_from_file(input_file='track_urls.txt'):
    """Extract track IDs from Spotify URLs"""
    track_ids = []
    
    if not os.path.exists(input_file):
        print(f"❌ {input_file} not found!")
        print("\nCreate track_urls.txt and paste your Spotify track links there")
        return track_ids
    
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            # Extract track ID from URL
            # Format: https://open.spotify.com/track/TRACK_ID or TRACK_ID
            match = re.search(r'track/([a-zA-Z0-9]+)', line)
            if match:
                track_ids.append(match.group(1))
            elif len(line) == 22 and line.isalnum():
                # Direct track ID
                track_ids.append(line)
    
    return track_ids

def fetch_track_info(track_ids, output_file='songs.txt'):
    """Fetch song info from Spotify track IDs"""
    
    if not SPOTIPY_CLIENT_ID or not SPOTIPY_CLIENT_SECRET:
        print("❌ Missing Spotify credentials in .env!")
        return False
    
    try:
        print("🔐 Authenticating with Spotify...")
        auth_manager = SpotifyClientCredentials(
            client_id=SPOTIPY_CLIENT_ID,
            client_secret=SPOTIPY_CLIENT_SECRET
        )
        sp = spotipy.Spotify(auth_manager=auth_manager)
        
        songs = []
        print(f"\n🎵 Fetching {len(track_ids)} track info...\n")
        
        for i, track_id in enumerate(track_ids, 1):
            try:
                track = sp.track(track_id)
                name = track['name']
                artist = track['artists'][0]['name']
                song = f"{name} - {artist}"
                songs.append(song)
                print(f"  [{i}/{len(track_ids)}] ✓ {song}")
            except Exception as e:
                print(f"  [{i}/{len(track_ids)}] ❌ Error fetching {track_id}: {e}")
        
        # Write to file
        if songs:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(songs))
            
            print(f"\n✅ Exported {len(songs)} songs to {output_file}")
            print(f"\nNext step:")
            print(f"  python script_manual.py")
            return True
        else:
            print("❌ No songs extracted")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("🎧 Spotify Track URL Converter\n")
    
    # Check for input file
    if not os.path.exists('track_urls.txt'):
        print("ℹ️  Create a file named 'track_urls.txt' in this folder")
        print("Paste your Spotify track links, one per line:")
        print("  https://open.spotify.com/track/2109dBho14Lqh2wr8goqAP")
        print("  https://open.spotify.com/track/3jrOziEVwpJAETyEDZ5HWa")
        print("  ...")
    else:
        track_ids = extract_track_ids_from_file('track_urls.txt')
        
        if not track_ids:
            print("❌ No track IDs found in track_urls.txt")
        else:
            print(f"Found {len(track_ids)} track URLs\n")
            fetch_track_info(track_ids)
