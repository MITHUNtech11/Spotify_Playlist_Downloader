import os
import re
import requests
import yt_dlp
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from datetime import datetime

load_dotenv()

DOWNLOAD_FOLDER = os.getenv('DOWNLOAD_FOLDER', './Dad_Car_Songs')
LOG_FILE = 'download_log.txt'

# Thread-safe output
print_lock = Lock()
log_lock = Lock()

# ============================================================================
# LOGGING SETUP
# ============================================================================

def log_message(message, level="INFO"):
    """Log message to both console and log file with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_text = f"[{timestamp}] [{level}] {message}"
    
    with log_lock:
        # Print to console
        print(log_text)
        
        # Write to log file
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_text + "\n")

# ============================================================================
# PART 1: CONVERT SPOTIFY TRACK URLs TO SONG NAMES
# ============================================================================

def extract_track_ids_from_file(input_file='track_urls.txt'):
    """Extract track IDs from Spotify URLs"""
    track_ids = []
    
    if not os.path.exists(input_file):
        log_message(f"❌ {input_file} not found!", "ERROR")
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
            log_message(f"⚠️  Error fetching {track_url}: {str(e)}", "WARNING")
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
    
    header = "\n" + "="*60 + "\n🎵 STEP 1: Converting Spotify Track URLs\n" + "="*60 + "\n"
    print(header)
    log_message("="*60 + " STEP 1: Converting Spotify Track URLs " + "="*60, "INFO")
    
    if not os.path.exists(input_file):
        error_msg = f"❌ {input_file} not found! Create track_urls.txt with Spotify track links"
        print(error_msg)
        log_message(error_msg, "ERROR")
        return []
    
    track_ids = extract_track_ids_from_file(input_file)
    
    if not track_ids:
        error_msg = "❌ No track URLs found in track_urls.txt"
        print(error_msg)
        log_message(error_msg, "ERROR")
        return []
    
    info_msg = f"Found {len(track_ids)} track URLs, using {max_workers} threads"
    print(info_msg)
    log_message(info_msg, "INFO")
    print("\nFetching song info...\n")
    
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
        
        success_msg = f"✅ Exported {len(songs)}/{len(track_ids)} songs to {output_file}"
        print(f"\n{success_msg}")
        log_message(success_msg, "SUCCESS")
        return songs
    else:
        error_msg = "❌ No songs extracted"
        print(error_msg)
        log_message(error_msg, "ERROR")
        return []

# ============================================================================
# PART 1.5: PREVIEW AND CONFIRM BEFORE DOWNLOAD
# ============================================================================

def preview_and_confirm(songs_list, output_path):
    """
    Show preview of songs to download and ask for user confirmation
    Returns True if user confirms, False if user cancels
    """
    
    print("\n" + "="*60)
    print("📋 PREVIEW: Summary Before Download")
    print("="*60 + "\n")
    
    # Deduplicate songs while preserving order
    seen = set()
    unique_songs = []
    for song in songs_list:
        if song.lower() not in seen:
            unique_songs.append(song)
            seen.add(song.lower())
    
    duplicates_in_list = len(songs_list) - len(unique_songs)
    
    # Create the folder if it doesn't exist
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    
    # Count existing songs in the folder
    existing_count = 0
    for song in unique_songs:
        if song_already_exists(song, output_path):
            existing_count += 1
    
    # Calculate counts
    new_to_download = len(unique_songs) - existing_count
    
    # Display summary table
    print(f"📁 Download folder: {os.path.abspath(output_path)}\n")
    print(f"{'Metric':<30} {'Count':<10}")
    print("-" * 40)
    print(f"{'Total songs from URLs':<30} {len(songs_list):<10}")
    print(f"{'Duplicates in list':<30} {duplicates_in_list:<10}")
    print(f"{'Unique songs':<30} {len(unique_songs):<10}")
    print(f"{'Already downloaded':<30} {existing_count:<10}")
    print(f"{'New to download':<30} {new_to_download:<10}")
    print("-" * 40)
    
    # Log the preview summary
    log_message("="*60 + " PREVIEW SUMMARY " + "="*60, "INFO")
    log_message(f"Total songs: {len(songs_list)}", "INFO")
    log_message(f"Duplicates in list: {duplicates_in_list}", "INFO")
    log_message(f"Unique songs: {len(unique_songs)}", "INFO")
    log_message(f"Already downloaded: {existing_count}", "INFO")
    log_message(f"New to download: {new_to_download}", "INFO")
    
    # Special case: no new songs to download
    if new_to_download == 0:
        print("\n⏭️  All songs are already downloaded!")
        log_message("All songs already downloaded, skipping download step", "WARNING")
        user_input = input("\n🎧 Continue to check for updates? (Y/n): ").strip().lower()
        return user_input != 'n'
    
    # Ask for user confirmation
    print(f"\n🎧 Start downloading {new_to_download} new song(s)?")
    user_input = input("Continue? (Y/n): ").strip().lower()
    
    if user_input in ['n', 'no']:
        log_message("User cancelled download", "INFO")
        return False
    elif user_input in ['y', 'yes', '']:
        log_message("User confirmed to proceed with download", "INFO")
        return True
    else:
        # Invalid input, ask again
        print("⚠️  Please enter 'Y' or 'N'")
        return preview_and_confirm(songs_list, output_path)

# ============================================================================
# PART 2: DOWNLOAD SONGS FROM YOUTUBE
# ============================================================================

def song_already_exists(song_name, output_path):
    """Check if a song file already exists in the output folder (any format)"""
    if not os.path.exists(output_path):
        return False
    
    # Create a sanitized version of the song name for comparison
    sanitized_song = re.sub(r'[<>:"/\|?*]', '', song_name)
    
    # Check for any audio/video files that might match
    audio_extensions = ('.mp3', '.webm', '.m4a', '.aac', '.wav', '.flac', '.opus')
    
    for filename in os.listdir(output_path):
        # Skip partial/incomplete downloads
        if filename.endswith('.part'):
            continue
            
        if filename.lower().endswith(audio_extensions):
            # Simple check: if song name is in the filename
            if sanitized_song.lower() in filename.lower() or filename.lower().startswith(song_name.split('-')[0].lower().strip()):
                return True
    
    return False

def cleanup_incomplete_downloads(output_path):
    """Remove incomplete downloads (.part files) and convert non-MP3 audio files to MP3"""
    if not os.path.exists(output_path):
        return
    
    files_removed = 0
    
    for filename in os.listdir(output_path):
        filepath = os.path.join(output_path, filename)
        
        # Remove incomplete downloads (.part files)
        if filename.endswith('.part'):
            try:
                os.remove(filepath)
                log_message(f"🗑️  Removed incomplete download: {filename}", "INFO")
                files_removed += 1
            except Exception as e:
                log_message(f"⚠️  Could not remove {filename}: {str(e)}", "WARNING")
    
    if files_removed > 0:
        log_message(f"🧹 Cleanup: Removed {files_removed} incomplete file(s)", "INFO")
    
    return files_removed
    """Download a single song - used by thread pool"""
    index, total, song, output_path = args
    
    # Check if song already exists
    if song_already_exists(song, output_path):
        with print_lock:
            print(f"[{index}/{total}] ⏭️  Skipped (already exists): {song}\n")
        return 'skipped'
    
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
                return 'success'
            else:
                with print_lock:
                    print(f"  ❌ No result found\n")
                return 'failed'
                
    except Exception as e:
        with print_lock:
            print(f"  ⚠️  Error: {str(e)[:100]}\n")
        return 'failed'

def download_songs_threaded(songs_list, output_path, max_workers=4):
    """Download MP3s from song list using multithreading"""
    
    header = "\n" + "="*60 + "\n🎵 STEP 2: Downloading Songs from YouTube\n" + "="*60 + "\n"
    print(header)
    log_message("="*60 + " STEP 2: Downloading Songs from YouTube " + "="*60, "INFO")
    
    if not songs_list:
        error_msg = "❌ No songs to download!"
        print(error_msg)
        log_message(error_msg, "ERROR")
        return
    
    # Create the folder if it doesn't exist
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_songs = []
    for song in songs_list:
        if song.lower() not in seen:
            unique_songs.append(song)
            seen.add(song.lower())
    
    if len(unique_songs) < len(songs_list):
        dup_msg = f"⚠️  Removed {len(songs_list) - len(unique_songs)} duplicate entries from list"
        print(f"{dup_msg}\n")
        log_message(dup_msg, "WARNING")

    start_msg = f"📁 Downloading to: {os.path.abspath(output_path)} | 🚀 Using {max_workers} threads | Total: {len(unique_songs)}"
    print(f"{start_msg}\n")
    log_message(start_msg, "INFO")

    # Create task list with indices
    tasks = [(i+1, len(unique_songs), song, output_path) for i, song in enumerate(unique_songs)]
    
    success_count = 0
    failed_count = 0
    skipped_count = 0
    
    # Use ThreadPoolExecutor for parallel downloads
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        futures = {executor.submit(download_single_song, task): task for task in tasks}
        
        # Collect results as they complete
        completed = 0
        for future in as_completed(futures):
            try:
                result = future.result()
                if result == 'success':
                    success_count += 1
                elif result == 'skipped':
                    skipped_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                with print_lock:
                    error_msg = f"❌ Thread error: {str(e)}"
                    print(f"{error_msg}\n")
                    log_message(error_msg, "ERROR")
                failed_count += 1
            
            completed += 1
            if completed % 5 == 0:  # Show progress every 5 downloads
                progress = (completed / len(unique_songs)) * 100
                with print_lock:
                    print(f"📊 Progress: {completed}/{len(unique_songs)} ({progress:.0f}%) - ✅{success_count} ⏭️{skipped_count} ❌{failed_count}\n")

    print("\n" + "="*60)
    print(f"🎉 Download Complete!")
    print(f"✅ Successful: {success_count}")
    print(f"⏭️  Skipped (already exist): {skipped_count}")
    print(f"❌ Failed: {failed_count}")
    total_processed = success_count + skipped_count + failed_count
    if total_processed > 0:
        print(f"📊 Success Rate: {(success_count/total_processed*100):.1f}%")
    print("="*60)
    
    # Log summary statistics
    log_message("="*60 + " DOWNLOAD SUMMARY " + "="*60, "INFO")
    log_message(f"✅ Successful Downloads: {success_count}", "INFO")
    log_message(f"⏭️  Skipped (Already Exist): {skipped_count}", "INFO")
    log_message(f"❌ Failed Downloads: {failed_count}", "INFO")
    if total_processed > 0:
        success_rate = (success_count/total_processed*100)
        log_message(f"📊 Success Rate: {success_rate:.1f}%", "INFO")
    log_message("="*60, "INFO")

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    # Clear log file at the start of each session
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        f.write("")
    
    header = "\n" + "🎧"*30 + "\n     SPOTIFY PLAYLIST DOWNLOADER (COMBINED)\n" + "🎧"*30
    print(header)
    log_message("="*80 + " SESSION START " + "="*80, "INFO")
    log_message(f"Log file created: {os.path.abspath(LOG_FILE)}", "INFO")
    
    songs = convert_urls_to_songs(max_workers=12)
    
    if not songs:
        error_msg = "❌ Failed to extract songs. Stopping."
        print(f"\n{error_msg}")
        log_message(error_msg, "ERROR")
    else:
        # Cleanup: Remove incomplete downloads before preview
        print("\n🧹 Cleaning up incomplete downloads...")
        cleanup_incomplete_downloads(DOWNLOAD_FOLDER)
        
        # Step 1.5: Preview and confirm before downloading
        proceed_with_download = preview_and_confirm(songs, DOWNLOAD_FOLDER)
        
        if proceed_with_download:
            # Step 2: Download songs
            download_songs_threaded(songs, DOWNLOAD_FOLDER, max_workers=10)
            
            print("\n" + "="*60)
            print("✨ All steps complete! Your playlist is ready.")
            print("="*60 + "\n")
            
            completion_msg = f"✨ All steps complete! Check {os.path.abspath(LOG_FILE)} for detailed logs"
            log_message(completion_msg, "SUCCESS")
        else:
            cancel_msg = "❌ Download cancelled by user"
            print(f"\n{cancel_msg}\n")
            log_message(cancel_msg, "INFO")
    
    log_message("="*80 + " SESSION END " + "="*80, "INFO")
