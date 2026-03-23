import os
import re
import requests
from bs4 import BeautifulSoup

def extract_track_ids_from_file(input_file='track_urls.txt'):
    """Extract track IDs from Spotify URLs"""
    track_ids = []
    
    if not os.path.exists(input_file):
        print(f"❌ {input_file} not found!")
        return track_ids
    
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            # Extract track ID from URL
            match = re.search(r'track/([a-zA-Z0-9]+)', line)
            if match:
                track_ids.append(match.group(1))
    
    return track_ids

def get_song_info_from_url(track_url):
    """Get song info by scraping the Spotify web page (no auth needed)"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(track_url, headers=headers, timeout=5)
        response.encoding = 'utf-8'
        
        if response.status_code == 200:
            # Extract title from page title meta tag
            # Format: "Song Name - Artist Name - Originally by Artist - Spotify"
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try to get from og:title
            og_title = soup.find('meta', property='og:title')
            if og_title:
                title = og_title.get('content', '').strip()
                # Format: "Song Name • Artist Name"
                if '•' in title:
                    parts = title.split('•')
                    song_name = parts[0].strip()
                    artist = parts[1].strip().split('·')[0].strip() if len(parts) > 1 else 'Unknown'
                    return f"{song_name} - {artist}"
            
            # Fallback: extract from page title
            page_title = soup.find('title')
            if page_title:
                title = page_title.string or ''
                # Remove Spotify suffix
                title = title.replace(' - Song by ', ' - ').replace(' - Spotify', '')
                if title:
                    return title
        
        return None
        
    except Exception as e:
        print(f"    ⚠️  Error fetching {track_url}: {e}")
        return None

def convert_urls_to_songs(input_file='track_urls.txt', output_file='songs.txt'):
    """Convert Spotify track URLs to song list"""
    
    print("🎵 Converting Spotify Track URLs\n")
    
    if not os.path.exists(input_file):
        print(f"❌ {input_file} not found!")
        print("\nCreate track_urls.txt and paste your Spotify track links there")
        return False
    
    track_ids = extract_track_ids_from_file(input_file)
    
    if not track_ids:
        print("❌ No track URLs found in track_urls.txt")
        return False
    
    print(f"Found {len(track_ids)} track URLs\n")
    print("Fetching song info...\n")
    
    songs = []
    for i, track_id in enumerate(track_ids, 1):
        track_url = f"https://open.spotify.com/track/{track_id}"
        print(f"  [{i}/{len(track_ids)}] Fetching: {track_id}")
        
        song_info = get_song_info_from_url(track_url)
        if song_info:
            songs.append(song_info)
            print(f"          ✓ {song_info}")
        else:
            print(f"          ⚠️  Could not fetch info, skipping...")
    
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

if __name__ == "__main__":
    convert_urls_to_songs()
