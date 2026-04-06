import os
import re
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# Thread-safe output
print_lock = Lock()

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
        with print_lock:
            print(f"    ⚠️  Error fetching {track_url}: {e}")
        return None

def process_track(args):
    """Process a single track - used by thread pool"""
    i, total, track_id = args
    track_url = f"https://open.spotify.com/track/{track_id}"
    
    with print_lock:
        print(f"  [{i}/{total}] Fetching: {track_id}")
    
    song_info = get_song_info_from_url(track_url)
    if song_info:
        with print_lock:
            print(f"          ✓ {song_info}")
        return song_info
    else:
        with print_lock:
            print(f"          ⚠️  Could not fetch info, skipping...")
        return None

def convert_urls_to_songs(input_file='track_urls.txt', output_file='songs.txt', max_workers=12):
    """Convert Spotify track URLs to song list using multithreading"""
    
    print("🎵 Converting Spotify Track URLs (Multi-threaded)\n")
    
    if not os.path.exists(input_file):
        print(f"❌ {input_file} not found!")
        print("\nCreate track_urls.txt and paste your Spotify track links there")
        return False
    
    track_ids = extract_track_ids_from_file(input_file)
    
    if not track_ids:
        print("❌ No track URLs found in track_urls.txt")
        return False
    
    print(f"Found {len(track_ids)} track URLs")
    print(f"Using {max_workers} threads for parallel processing\n")
    print("Fetching song info...\n")
    
    songs = []
    
    # Create task list with indices
    tasks = [(i+1, len(track_ids), track_id) for i, track_id in enumerate(track_ids)]
    
    # Use ThreadPoolExecutor for parallel fetching
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        futures = {executor.submit(process_track, task): task for task in tasks}
        
        # Collect results as they complete
        completed = 0
        for future in as_completed(futures):
            result = future.result()
            if result:
                songs.append(result)
            completed += 1
            # Optional: show progress percentage
            progress = (completed / len(track_ids)) * 100
            if completed % 5 == 0:  # Show every 5 completed
                print(f"  Progress: {completed}/{len(track_ids)} ({progress:.0f}%)")
    
    # Write to file
    if songs:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(songs))
        
        print(f"\n✅ Exported {len(songs)} songs to {output_file}")
        print(f"\nNext step:")
        print(f"  python script_manual_threaded.py")
        return True
    else:
        print("❌ No songs extracted")
        return False

if __name__ == "__main__":
    # Use 12 threads (good balance for 16 logical processors)
    # Adjust this number based on your system performance
    convert_urls_to_songs(max_workers=12)
