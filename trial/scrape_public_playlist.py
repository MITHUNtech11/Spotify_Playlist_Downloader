import os
import requests
import json
from dotenv import load_dotenv
import re

load_dotenv()
PLAYLIST_ID = os.getenv('PLAYLIST_ID')

def fetch_public_playlist(playlist_id, output_file='songs.txt'):
    """
    Fetch songs from a PUBLIC Spotify playlist without authentication
    Uses Spotify's public API endpoints
    """
    
    try:
        print(f"🔗 Fetching public playlist: {playlist_id}")
        
        # Spotify Web API endpoint for public playlists
        url = f"https://api.spotify.com/v1/playlists/{playlist_id}"
        
        # First request - get basic info
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 404:
            print("❌ Playlist not found. Make sure it's public!")
            return False
        
        if response.status_code != 200:
            print(f"❌ Error: {response.status_code}")
            return False
        
        data = response.json()
        
        # Extract songs
        songs = []
        
        if 'tracks' in data and 'items' in data['tracks']:
            for item in data['tracks']['items']:
                if item and 'track' in item:
                    track = item['track']
                    if track:
                        name = track.get('name', 'Unknown')
                        artists = track.get('artists', [])
                        artist_name = artists[0]['name'] if artists else 'Unknown'
                        song = f"{name} - {artist_name}"
                        songs.append(song)
                        print(f"  ✓ {song}")
        
        # Handle pagination if playlist has more than 50 songs
        while data.get('tracks', {}).get('next'):
            next_url = data['tracks']['next']
            response = requests.get(next_url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'items' in data:
                    for item in data['items']:
                        if item and 'track' in item:
                            track = item['track']
                            if track:
                                name = track.get('name', 'Unknown')
                                artists = track.get('artists', [])
                                artist_name = artists[0]['name'] if artists else 'Unknown'
                                song = f"{name} - {artist_name}"
                                songs.append(song)
                                print(f"  ✓ {song}")
        
        # Write to file
        if songs:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(songs))
            
            print(f"\n✅ Exported {len(songs)} songs to {output_file}")
            print(f"\nNext step:")
            print(f"  python script_manual.py")
            return True
        else:
            print("❌ No songs found in playlist")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return False
    except json.JSONDecodeError:
        print("❌ Failed to parse response")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    if not PLAYLIST_ID:
        print("❌ Missing PLAYLIST_ID in .env file!")
        print("\nAdd this to .env:")
        print("  PLAYLIST_ID=6eEDBobRHHtcTkWAtojSiR")
    else:
        success = fetch_public_playlist(PLAYLIST_ID)
        if not success:
            print("\n⚠️  Make sure:")
            print("  1. Playlist ID is correct")
            print("  2. Playlist is PUBLIC (not private)")
            print("  3. You have internet connection")
