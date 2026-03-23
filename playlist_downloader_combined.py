import os
import re
import requests
import yt_dlp
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

load_dotenv()

DOWNLOAD_FOLDER = os.getenv('DOWNLOAD_FOLDER', './Dad_Car_Songs')

# Thread-safe output
print_lock = Lock()

# ============================================================================
# PART 1: CONVERT SPOTIFY TRACK URLs TO SONG NAMES
# ============================================================================

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
            print(f"    ⚠️  Error fetching: {e}")
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
            print(f"          ⚠️  Could not fetch, skipping...")
        return None

def convert_urls_to_songs(input_file='track_urls.txt', output_file='songs.txt', max_workers=12):
    """Convert Spotify track URLs to song list using multithreading"""
    
    print("\n" + "="*60)
    print("🎵 STEP 1: Converting Spotify Track URLs")
    print("="*60 + "\n")
    
    if not os.path.exists(input_file):
        print(f"❌ {input_file} not found!")
        print("\nCreate track_urls.txt and paste your Spotify track links there")
        return []
    
    track_ids = extract_track_ids_from_file(input_file)
    
    if not track_ids:
        print("❌ No track URLs found in track_urls.txt")
        return []
    
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
            # Show progress percentage
            progress = (completed / len(track_ids)) * 100
            if completed % 5 == 0:  # Show every 5 completed
                print(f"  Progress: {completed}/{len(track_ids)} ({progress:.0f}%)")
    
    # Write to file
    if songs:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(songs))
        
        print(f"\n✅ Exported {len(songs)}/{len(track_ids)} songs to {output_file}")
        return songs
    else:
        print("❌ No songs extracted")
        return []

# ============================================================================
# PART 2: DOWNLOAD SONGS FROM YOUTUBE
# ============================================================================

def download_single_song(args):
    """Download a single song - used by thread pool"""
    index, total, song, output_path = args
    
    with print_lock:
        print(f"[{index}/{total}] 🎵 Searching: {song}")
    
    try:
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
            'quiet': True,  # Suppress yt-dlp's verbose output
            'extract_flat': False,
            'socket_timeout': 30,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            query = f"{song} official audio"
            info = ydl.extract_info(f"ytsearch1:{query}", download=True)
            
            if info:
                with print_lock:
                    print(f"  ✅ Downloaded: {info.get('title', song)}\n")
                return True
            else:
                with print_lock:
                    print(f"  ❌ No result found\n")
                return False
                
    except Exception as e:
        with print_lock:
            print(f"  ⚠️  Error: {str(e)[:100]}\n")
        return False

def download_songs_threaded(songs_list, output_path, max_workers=4):
    """Download MP3s from song list using multithreading"""
    
    print("\n" + "="*60)
    print("🎵 STEP 2: Downloading Songs from YouTube")
    print("="*60 + "\n")
    
    if not songs_list:
        print("❌ No songs to download!")
        return
    
    # Create the folder if it doesn't exist
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    print(f"📁 Downloading to: {os.path.abspath(output_path)}")
    print(f"🚀 Using {max_workers} parallel downloads (Total songs: {len(songs_list)})\n")

    # Create task list with indices
    tasks = [(i+1, len(songs_list), song, output_path) for i, song in enumerate(songs_list)]
    
    success_count = 0
    failed_count = 0
    
    # Use ThreadPoolExecutor for parallel downloads
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        futures = {executor.submit(download_single_song, task): task for task in tasks}
        
        # Collect results as they complete
        completed = 0
        for future in as_completed(futures):
            try:
                result = future.result()
                if result:
                    success_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                with print_lock:
                    print(f"❌ Thread error: {e}\n")
                failed_count += 1
            
            completed += 1
            if completed % 5 == 0:  # Show progress every 5 downloads
                progress = (completed / len(songs_list)) * 100
                with print_lock:
                    print(f"📊 Progress: {completed}/{len(songs_list)} ({progress:.0f}%) - ✅{success_count} ❌{failed_count}\n")

    print("\n" + "="*60)
    print(f"🎉 Download Complete!")
    print(f"✅ Successful: {success_count}")
    print(f"❌ Failed: {failed_count}")
    print(f"📊 Success Rate: {(success_count/len(songs_list)*100):.1f}%")
    print("="*60)

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("\n" + "🎧"*30)
    print("     SPOTIFY PLAYLIST DOWNLOADER (COMBINED)")
    print("🎧"*30)
    
    # Step 1: Convert URLs to songs
    songs = convert_urls_to_songs(max_workers=12)
    
    if not songs:
        print("\n❌ Failed to extract songs. Stopping.")
    else:
        # Step 2: Download songs
        download_songs_threaded(songs, DOWNLOAD_FOLDER, max_workers=4)
        
        print("\n" + "="*60)
        print("✨ All steps complete! Your playlist is ready.")
        print("="*60 + "\n")
