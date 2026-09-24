import os
import re
import sys
import shutil
import argparse
import requests
import yt_dlp
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from datetime import datetime
import time

# Configure Windows console encoding for Unicode/emojis
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Audio tagging support
try:
    from mutagen.id3 import ID3, TIT2, TPE1, TALB, APIC, ID3NoHeaderError
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False

load_dotenv()

DEFAULT_DOWNLOAD_FOLDER = os.getenv('DOWNLOAD_FOLDER', './Dad_Car_Songs')
LOG_FILE = 'download_log.txt'

# Thread-safe output locks
print_lock = Lock()
log_lock = Lock()

# ============================================================================
# LOGGING SETUP
# ============================================================================

def log_message(message, level="INFO"):
    """Log message to both console and log file with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_text = f"[{timestamp}] [{level}] {message}"
    
    with log_lock:
        print(log_text)
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_text + "\n")

# ============================================================================
# FFmpeg DETECTION
# ============================================================================

def get_ffmpeg_dir():
    """Locate ffmpeg binary on the system (PATH or common WinGet install dirs)."""
    ffmpeg_bin = shutil.which('ffmpeg')
    if ffmpeg_bin:
        return os.path.dirname(ffmpeg_bin)
    
    if os.name == 'nt':
        local_app_data = os.getenv('LOCALAPPDATA', '')
        if local_app_data:
            winget_pkgs = os.path.join(local_app_data, 'Microsoft', 'WinGet', 'Packages')
            if os.path.isdir(winget_pkgs):
                for root, _, files in os.walk(winget_pkgs):
                    if 'ffmpeg.exe' in files:
                        return root
    return None

# ============================================================================
# PART 1: CONVERT SPOTIFY TRACK URLs TO SONG METADATA
# ============================================================================

def extract_track_ids_from_file(input_file='track_urls.txt'):
    """Extract Spotify track IDs from a text file or URL list."""
    track_ids = []
    
    if not os.path.exists(input_file):
        log_message(f"❌ {input_file} not found!", "ERROR")
        return track_ids
    
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Match standard URL, shortlink, or URI
            match = re.search(r'track[/:]([a-zA-Z0-9]{22})', line)
            if match:
                track_ids.append(match.group(1))
            else:
                # Fallback for plain 22-character track IDs
                plain_id = re.match(r'^[a-zA-Z0-9]{22}$', line)
                if plain_id:
                    track_ids.append(plain_id.group(0))
    
    return track_ids

def get_song_info_from_url(track_url):
    """
    Get song info and metadata using Spotify's official public oEmbed endpoint,
    with an HTML metadata scraping fallback.
    Returns a dict with title, artist, display_name, and cover_url.
    """
    metadata = {
        'title': None,
        'artist': None,
        'display_name': None,
        'cover_url': None
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    # 1. Try Spotify Official Public oEmbed API (Fast & Reliable, No Auth Needed)
    try:
        oembed_url = f"https://open.spotify.com/oembed?url={track_url}"
        oembed_resp = requests.get(oembed_url, headers=headers, timeout=6)
        if oembed_resp.status_code == 200:
            data = oembed_resp.json()
            raw_title = data.get('title', '').strip()
            cover = data.get('thumbnail_url')
            if cover:
                metadata['cover_url'] = cover
            
            if raw_title:
                metadata['title'] = raw_title
                metadata['display_name'] = raw_title
    except Exception:
        pass
    
    # 2. Query Track Page for Artist, Album, and High-Resolution Cover
    try:
        page_resp = requests.get(track_url, headers=headers, timeout=6)
        if page_resp.status_code == 200:
            soup = BeautifulSoup(page_resp.text, 'html.parser')
            
            # Musician / Artist meta tags
            artist_meta = soup.find('meta', property='music:musician_description')
            if artist_meta and artist_meta.get('content'):
                metadata['artist'] = artist_meta.get('content').strip()
            
            # High-res cover image
            og_image = soup.find('meta', property='og:image')
            if og_image and og_image.get('content'):
                metadata['cover_url'] = og_image.get('content').strip()
            
            # og:title typically has "Song • Artist"
            og_title = soup.find('meta', property='og:title')
            if og_title and og_title.get('content'):
                content = og_title.get('content').strip()
                if '•' in content:
                    parts = content.split('•')
                    song_name = parts[0].strip()
                    artist_name = parts[1].strip().split('·')[0].strip() if len(parts) > 1 else 'Unknown'
                    metadata['title'] = song_name
                    if not metadata['artist']:
                        metadata['artist'] = artist_name
                    metadata['display_name'] = f"{song_name} - {artist_name}"
            
            # Description fallback: "Listen to Song on Spotify. Song · Artist · Year"
            if not metadata['artist']:
                desc_meta = soup.find('meta', attrs={'name': 'description'})
                if desc_meta and desc_meta.get('content'):
                    desc_text = desc_meta.get('content')
                    match = re.search(r'Song\s+[·•\-]\s+([^·•\-]+)\s+[·•\-]', desc_text)
                    if match:
                        metadata['artist'] = match.group(1).strip()
    except Exception as e:
        with print_lock:
            log_message(f"⚠️  Error fetching HTML details for {track_url}: {str(e)}", "WARNING")
    
    # Finalize display name and title
    if metadata['title'] and metadata['artist'] and ' - ' not in (metadata.get('display_name') or ''):
        metadata['display_name'] = f"{metadata['title']} - {metadata['artist']}"
    elif metadata['title'] and not metadata.get('display_name'):
        metadata['display_name'] = metadata['title']
    
    if metadata['display_name']:
        return metadata
    return None

def process_track(args):
    """Process a single track in the thread pool."""
    i, total, track_id = args
    track_url = f"https://open.spotify.com/track/{track_id}"
    
    with print_lock:
        print(f"  [{i}/{total}] Fetching: {track_id}")
    
    info = None
    for attempt in range(4):
        try:
            info = get_song_info_from_url(track_url)
            if info and info.get('display_name'):
                break
        except Exception:
            pass
        if not info and attempt < 3:
            time.sleep(1.5 * (attempt + 1))
            
    if info:
        display_name = info['display_name']
        with print_lock:
            print(f"          ✓ {display_name}")
        return info
    else:
        with print_lock:
            print(f"          ⚠️  Could not fetch {track_id}, skipping...")
        return None

def convert_urls_to_songs(input_file='track_urls.txt', output_file='songs.txt', max_workers=8):
    """Convert Spotify track URLs to song list and metadata mapping."""
    header = "\n" + "="*60 + "\n🎵 STEP 1: Converting Spotify Track URLs\n" + "="*60 + "\n"
    print(header)
    log_message("="*60 + " STEP 1: Converting Spotify Track URLs " + "="*60, "INFO")
    
    if not os.path.exists(input_file):
        error_msg = f"❌ {input_file} not found! Create {input_file} with Spotify track links"
        print(error_msg)
        log_message(error_msg, "ERROR")
        return [], {}
    
    track_ids = extract_track_ids_from_file(input_file)
    
    if not track_ids:
        error_msg = f"❌ No valid track URLs found in {input_file}"
        print(error_msg)
        log_message(error_msg, "ERROR")
        return [], {}
    
    info_msg = f"Found {len(track_ids)} track URLs, using {max_workers} threads"
    print(info_msg)
    log_message(info_msg, "INFO")
    print("\nFetching song info via Spotify oEmbed & metadata API...\n")
    
    tasks = [(i+1, len(track_ids), track_id) for i, track_id in enumerate(track_ids)]
    results = [None] * len(track_ids)
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_track, task): idx for idx, task in enumerate(tasks)}
        completed = 0
        for future in as_completed(futures):
            idx = futures[future]
            try:
                res = future.result()
                results[idx] = res
            except Exception as e:
                with print_lock:
                    log_message(f"⚠️ Error processing track #{idx+1}: {e}", "WARNING")
            completed += 1
            progress = (completed / len(track_ids)) * 100
            if completed % 5 == 0 or completed == len(track_ids):
                with print_lock:
                    print(f"  Progress: {completed}/{len(track_ids)} ({progress:.0f}%)")
    
    # Second pass for any tracks that encountered temporary connection issues
    missing_indices = [idx for idx, res in enumerate(results) if res is None]
    if missing_indices:
        with print_lock:
            print(f"\n🔄 Retrying {len(missing_indices)} tracks that encountered temporary connection issues...")
        time.sleep(2)
        retry_tasks = [(idx+1, len(track_ids), track_ids[idx]) for idx in missing_indices]
        with ThreadPoolExecutor(max_workers=4) as retry_executor:
            retry_futures = {retry_executor.submit(process_track, task): idx for idx, task in zip(missing_indices, retry_tasks)}
            for future in as_completed(retry_futures):
                idx = retry_futures[future]
                try:
                    res = future.result()
                    if res:
                        results[idx] = res
                except Exception:
                    pass
    
    songs = []
    metadata_map = {}
    for res in results:
        if res:
            disp = res['display_name']
            songs.append(disp)
            metadata_map[disp] = res
    
    if songs:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(songs))
        
        success_msg = f"✅ Exported {len(songs)}/{len(track_ids)} songs to {output_file}"
        print(f"\n{success_msg}")
        log_message(success_msg, "SUCCESS")
        return songs, metadata_map
    else:
        error_msg = "❌ No songs extracted from track URLs"
        print(error_msg)
        log_message(error_msg, "ERROR")
        return [], {}

# ============================================================================
# PART 1.5: PREVIEW AND CONFIRM BEFORE DOWNLOAD
# ============================================================================

def preview_and_confirm(songs_list, output_path, auto_confirm=False):
    """
    Show preview summary before downloading and ask for user confirmation.
    Returns True if confirmed, False if cancelled.
    """
    print("\n" + "="*60)
    print("📋 PREVIEW: Summary Before Download")
    print("="*60 + "\n")
    
    # Deduplicate while preserving order
    seen = set()
    unique_songs = []
    for song in songs_list:
        norm = song.lower().strip()
        if norm not in seen:
            unique_songs.append(song)
            seen.add(norm)
    
    duplicates_in_list = len(songs_list) - len(unique_songs)
    
    if not os.path.exists(output_path):
        os.makedirs(output_path, exist_ok=True)
    
    existing_count = sum(1 for s in unique_songs if song_already_exists(s, output_path))
    new_to_download = len(unique_songs) - existing_count
    
    # Summary Table
    print(f"📁 Download folder: {os.path.abspath(output_path)}\n")
    print(f"{'Metric':<30} {'Count':<10}")
    print("-" * 40)
    print(f"{'Total songs from URLs':<30} {len(songs_list):<10}")
    print(f"{'Duplicates in list':<30} {duplicates_in_list:<10}")
    print(f"{'Unique songs':<30} {len(unique_songs):<10}")
    print(f"{'Already downloaded':<30} {existing_count:<10}")
    print(f"{'New to download':<30} {new_to_download:<10}")
    print("-" * 40)
    
    log_message("="*60 + " PREVIEW SUMMARY " + "="*60, "INFO")
    log_message(f"Total: {len(songs_list)}, Unique: {len(unique_songs)}, Already downloaded: {existing_count}, New: {new_to_download}", "INFO")
    
    if new_to_download == 0:
        print("\n⏭️  All songs are already downloaded!")
        log_message("All songs already downloaded, skipping download step", "WARNING")
        if auto_confirm:
            return True
        user_input = input("\n🎧 Continue to check for updates? (Y/n): ").strip().lower()
        return user_input not in ['n', 'no']
    
    if auto_confirm:
        print("\n⚡ Auto-confirm enabled. Starting download...")
        return True
    
    print(f"\n🎧 Start downloading {new_to_download} new song(s)?")
    while True:
        user_input = input("Continue? (Y/n): ").strip().lower()
        
        if user_input in ['n', 'no']:
            log_message("User cancelled download", "INFO")
            return False
        elif user_input in ['y', 'yes', '']:
            log_message("User confirmed to proceed with download", "INFO")
            return True
        else:
            print("⚠️  Please enter 'Y' or 'N'")

# ============================================================================
# PART 2: DOWNLOAD SONGS FROM YOUTUBE WITH ID3 TAGGING
# ============================================================================

def song_already_exists(song_name, output_path):
    """
    Check if a song already exists in the output folder.
    Avoids aggressive substring matching to prevent false positives.
    """
    if not os.path.exists(output_path):
        return False
    
    sanitized_song = re.sub(r'[<>:"/\\|?*]', '', song_name).strip().lower()
    audio_extensions = ('.mp3', '.webm', '.m4a', '.aac', '.wav', '.flac', '.opus')
    
    # Split title and artist if available
    title_part = sanitized_song
    artist_part = ""
    if ' - ' in sanitized_song:
        parts = sanitized_song.split(' - ', 1)
        title_part = parts[0].strip()
        artist_part = parts[1].strip()
    
    for filename in os.listdir(output_path):
        if filename.endswith('.part'):
            continue
            
        if filename.lower().endswith(audio_extensions):
            base_filename = os.path.splitext(filename)[0].lower()
            
            # Exact base match
            if sanitized_song == base_filename or title_part == base_filename:
                return True
            
            # If both title and primary artist are present in the filename
            if title_part and title_part in base_filename:
                if not artist_part:
                    return True
                # Check first artist name
                primary_artist = artist_part.split(',')[0].strip()
                if primary_artist and primary_artist in base_filename:
                    return True
    
    return False

def cleanup_incomplete_downloads(output_path):
    """Remove incomplete download files (.part, .ytdl)."""
    if not os.path.exists(output_path):
        return 0
    
    files_removed = 0
    for filename in os.listdir(output_path):
        if filename.endswith(('.part', '.ytdl')):
            filepath = os.path.join(output_path, filename)
            try:
                os.remove(filepath)
                log_message(f"🗑️  Removed incomplete download: {filename}", "INFO")
                files_removed += 1
            except Exception as e:
                log_message(f"⚠️  Could not remove {filename}: {str(e)}", "WARNING")
    
    if files_removed > 0:
        log_message(f"🧹 Cleanup: Removed {files_removed} incomplete file(s)", "INFO")
    return files_removed

def embed_id3_tags(file_path, song_metadata):
    """Embed ID3 metadata (Title, Artist, and Spotify Album Art) into MP3."""
    if not MUTAGEN_AVAILABLE or not os.path.exists(file_path):
        return
    
    try:
        try:
            audio = ID3(file_path)
        except ID3NoHeaderError:
            audio = ID3()
        
        title = song_metadata.get('title')
        artist = song_metadata.get('artist')
        cover_url = song_metadata.get('cover_url')
        
        if title:
            audio['TIT2'] = TIT2(encoding=3, text=title)
        if artist:
            audio['TPE1'] = TPE1(encoding=3, text=artist)
        
        # Download and embed cover image
        if cover_url:
            try:
                img_resp = requests.get(cover_url, timeout=5)
                if img_resp.status_code == 200:
                    mime = 'image/jpeg' if 'jpeg' in cover_url or 'jpg' in cover_url else 'image/png'
                    audio['APIC'] = APIC(
                        encoding=3,
                        mime=mime,
                        type=3,  # Cover (front)
                        desc='Cover',
                        data=img_resp.content
                    )
            except Exception:
                pass
        
        audio.save(file_path)
    except Exception as e:
        with print_lock:
            log_message(f"⚠️  Could not embed ID3 tags for {os.path.basename(file_path)}: {e}", "WARNING")

def find_existing_song_in_library(song_name, library_folders):
    """Check if song exists in local libraries (e.g. Dad_Car_Songs, Spotify songs)."""
    sanitized_song = re.sub(r'[<>:"/\\|?*]', '', song_name).strip().lower()
    audio_extensions = ('.mp3', '.webm', '.m4a', '.aac', '.wav', '.flac', '.opus')
    
    title_part = sanitized_song
    artist_part = ""
    if ' - ' in sanitized_song:
        parts = sanitized_song.split(' - ', 1)
        title_part = parts[0].strip()
        artist_part = parts[1].strip()
    
    for folder in library_folders:
        if not os.path.exists(folder):
            continue
        for filename in os.listdir(folder):
            if filename.endswith(('.part', '.ytdl')):
                continue
            if filename.lower().endswith(audio_extensions):
                base_filename = os.path.splitext(filename)[0].lower()
                matched = False
                if sanitized_song == base_filename or title_part == base_filename:
                    matched = True
                elif title_part and len(title_part) > 3 and title_part in base_filename:
                    if not artist_part:
                        matched = True
                    else:
                        primary_artist = artist_part.split(',')[0].strip()
                        if primary_artist and len(primary_artist) > 2 and primary_artist in base_filename:
                            matched = True
                if matched:
                    return os.path.join(folder, filename)
    return None

def download_single_song(args):
    """Download a single song from YouTube using yt-dlp, reusing local library if present."""
    index, total, song, output_path, metadata = args
    
    # Check if song already exists in destination
    if song_already_exists(song, output_path):
        with print_lock:
            print(f"[{index}/{total}] ⏭️  Skipped (already exists): {song}\n")
        return 'skipped'
    
    # Check local library folders first to accelerate downloads
    local_libs = ['./Dad_Car_Songs', './Spotify songs']
    local_libs = [lib for lib in local_libs if os.path.abspath(lib) != os.path.abspath(output_path)]
    existing_lib_file = find_existing_song_in_library(song, local_libs)
    if existing_lib_file:
        try:
            dest_file = os.path.join(output_path, os.path.basename(existing_lib_file))
            shutil.copy2(existing_lib_file, dest_file)
            if metadata:
                embed_id3_tags(dest_file, metadata)
            with print_lock:
                print(f"[{index}/{total}] 📂 Reused from library: {os.path.basename(dest_file)}\n")
            return 'success'
        except Exception as e:
            with print_lock:
                print(f"[{index}/{total}] ⚠️ Could not copy from library: {e}, falling back to YouTube")
    
    with print_lock:
        print(f"[{index}/{total}] 🎵 Searching: {song}")
    
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'socket_timeout': 30,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web']
                }
            }
        }
        
        ffmpeg_dir = get_ffmpeg_dir()
        if ffmpeg_dir:
            ydl_opts['ffmpeg_location'] = ffmpeg_dir
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            query = f"{song} official audio"
            info = None
            try:
                info = ydl.extract_info(f"ytsearch1:{query}", download=True)
            except Exception:
                info = None
            
            # Fallback query if official audio yielded no results
            if not info or not info.get('entries'):
                try:
                    info = ydl.extract_info(f"ytsearch1:{song}", download=True)
                except Exception:
                    info = None
            
            if info:
                entry = info['entries'][0] if ('entries' in info and info['entries']) else info
                downloaded_title = entry.get('title', song)
                
                # Accurately resolve output mp3 file path
                downloaded_file = None
                
                # 1. Check requested_downloads from yt-dlp post-processing
                if 'requested_downloads' in entry and entry['requested_downloads']:
                    for req in reversed(entry['requested_downloads']):
                        fp = req.get('filepath')
                        if fp and fp.lower().endswith('.mp3') and os.path.exists(fp):
                            downloaded_file = fp
                            break
                
                # 2. Check filepath field directly
                if not downloaded_file:
                    fp = entry.get('filepath')
                    if fp and fp.lower().endswith('.mp3') and os.path.exists(fp):
                        downloaded_file = fp
                
                # 3. Check prepared filename with .mp3 extension
                if not downloaded_file:
                    prep = os.path.splitext(ydl.prepare_filename(entry))[0] + '.mp3'
                    if os.path.exists(prep):
                        downloaded_file = prep
                
                # 4. Conservative exact sanitized title match in output directory
                if not downloaded_file:
                    sanitized_base = re.sub(r'[<>:"/\\|?*]', '', downloaded_title).strip().lower()
                    for f in os.listdir(output_path):
                        if f.lower().endswith('.mp3'):
                            f_base = os.path.splitext(f)[0].lower()
                            if f_base == sanitized_base:
                                downloaded_file = os.path.join(output_path, f)
                                break
                
                # Verify file exists; fail safely rather than guessing or modifying the wrong MP3
                if not downloaded_file or not os.path.exists(downloaded_file):
                    with print_lock:
                        print(f"  ❌ Output MP3 file could not be verified for: {song}\n")
                    return 'failed'
                
                # Embed ID3 tags & Album artwork
                if metadata:
                    embed_id3_tags(downloaded_file, metadata)
                
                with print_lock:
                    print(f"  ✅ Downloaded: {downloaded_title}\n")
                return 'success'
            else:
                with print_lock:
                    print(f"  ❌ No result found for: {song}\n")
                return 'failed'
                
    except Exception as e:
        err_str = str(e)
        with print_lock:
            if 'ffmpeg' in err_str.lower() or 'ffprobe' in err_str.lower():
                print(f"  ❌ FFmpeg Missing: Please install FFmpeg (e.g. winget install Gyan.FFmpeg)\n")
                log_message(f"FFmpeg missing error when downloading {song}: {err_str}", "ERROR")
            else:
                print(f"  ⚠️  Error: {err_str[:100]}\n")
                log_message(f"Download error for {song}: {err_str}", "WARNING")
        return 'failed'

def download_songs_threaded(songs_list, output_path, metadata_map=None, max_workers=3):
    """Download MP3s concurrently using thread pool."""
    header = "\n" + "="*60 + "\n🎵 STEP 2: Downloading Songs from YouTube\n" + "="*60 + "\n"
    print(header)
    log_message("="*60 + " STEP 2: Downloading Songs from YouTube " + "="*60, "INFO")
    
    if not songs_list:
        error_msg = "❌ No songs to download!"
        print(error_msg)
        log_message(error_msg, "ERROR")
        return
    
    if not os.path.exists(output_path):
        os.makedirs(output_path, exist_ok=True)
    
    # Deduplicate while preserving order
    seen = set()
    unique_songs = []
    for song in songs_list:
        norm = song.lower().strip()
        if norm not in seen:
            unique_songs.append(song)
            seen.add(norm)
    
    metadata_map = metadata_map or {}
    start_msg = f"📁 Destination: {os.path.abspath(output_path)} | 🚀 Threads: {max_workers} | Total: {len(unique_songs)}"
    print(f"{start_msg}\n")
    log_message(start_msg, "INFO")
    
    tasks = [
        (i+1, len(unique_songs), song, output_path, metadata_map.get(song))
        for i, song in enumerate(unique_songs)
    ]
    
    success_count = 0
    failed_count = 0
    skipped_count = 0
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(download_single_song, task): task for task in tasks}
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
                    error_msg = f"❌ Thread exception: {str(e)}"
                    print(f"{error_msg}\n")
                    log_message(error_msg, "ERROR")
                failed_count += 1
            
            completed += 1
            if completed % 5 == 0 or completed == len(unique_songs):
                progress = (completed / len(unique_songs)) * 100
                with print_lock:
                    print(f"📊 Progress: {completed}/{len(unique_songs)} ({progress:.0f}%) - ✅{success_count} ⏭️{skipped_count} ❌{failed_count}\n")
    
    print("\n" + "="*60)
    print("🎉 Download Complete!")
    print(f"✅ Successful: {success_count}")
    print(f"⏭️  Skipped (already exist): {skipped_count}")
    print(f"❌ Failed: {failed_count}")
    total_processed = success_count + skipped_count + failed_count
    if total_processed > 0:
        print(f"📊 Success Rate: {(success_count/total_processed*100):.1f}%")
    print("="*60)
    
    log_message("="*60 + " DOWNLOAD SUMMARY " + "="*60, "INFO")
    log_message(f"✅ Successful: {success_count} | ⏭️ Skipped: {skipped_count} | ❌ Failed: {failed_count}", "INFO")

# ============================================================================
# CLI & MAIN ENTRYPOINT
# ============================================================================

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Spotify Playlist Downloader: Convert Spotify track links to songs and download MP3s via YouTube."
    )
    parser.add_argument(
        '-u', '--urls',
        default='track_urls.txt',
        help="Path to file containing Spotify track URLs (default: track_urls.txt)"
    )
    parser.add_argument(
        '-o', '--output',
        default=DEFAULT_DOWNLOAD_FOLDER,
        help=f"Download folder path (default from .env or '{DEFAULT_DOWNLOAD_FOLDER}')"
    )
    parser.add_argument(
        '-t', '--threads',
        type=int,
        default=3,
        help="Number of concurrent YouTube download threads (default: 3 to avoid rate limits)"
    )
    parser.add_argument(
        '-y', '--yes',
        action='store_true',
        help="Automatically confirm and start download without prompting"
    )
    parser.add_argument(
        '--clean-only',
        action='store_true',
        help="Only clean up incomplete downloads (.part files) and exit"
    )
    return parser.parse_args()

def main():
    args = parse_arguments()
    
    # Initialize log file
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        f.write("")
    
    header = "\n" + "🎧"*30 + "\n     SPOTIFY PLAYLIST DOWNLOADER\n" + "🎧"*30
    print(header)
    log_message("="*80 + " SESSION START " + "="*80, "INFO")
    log_message(f"Log file: {os.path.abspath(LOG_FILE)}", "INFO")
    
    # Check FFmpeg
    ffmpeg_dir = get_ffmpeg_dir()
    if ffmpeg_dir:
        log_message(f"FFmpeg located: {ffmpeg_dir}", "INFO")
    else:
        log_message("⚠️  FFmpeg not found in PATH. Audio post-processing to MP3 may fail if FFmpeg is missing.", "WARNING")
    
    if args.clean_only:
        print("\n🧹 Cleaning up incomplete downloads...")
        cleanup_incomplete_downloads(args.output)
        return
    
    # Step 1: Extract Spotify track URLs to song names & metadata
    songs, metadata_map = convert_urls_to_songs(input_file=args.urls, max_workers=8)
    
    if not songs:
        error_msg = "❌ Failed to extract songs from URLs. Stopping."
        print(f"\n{error_msg}")
        log_message(error_msg, "ERROR")
        return
    
    # Cleanup incomplete downloads before preview
    cleanup_incomplete_downloads(args.output)
    
    # Step 1.5: Preview & Confirm
    proceed = preview_and_confirm(songs, args.output, auto_confirm=args.yes)
    
    if proceed:
        # Step 2: Download songs
        download_songs_threaded(
            songs_list=songs,
            output_path=args.output,
            metadata_map=metadata_map,
            max_workers=args.threads
        )
        print("\n" + "="*60)
        print("✨ All steps complete! Your music is ready.")
        print(f"📄 Detailed log: {os.path.abspath(LOG_FILE)}")
        print("="*60 + "\n")
        log_message("Session completed successfully", "SUCCESS")
    else:
        cancel_msg = "❌ Download cancelled by user"
        print(f"\n{cancel_msg}\n")
        log_message(cancel_msg, "INFO")
    
    log_message("="*80 + " SESSION END " + "="*80, "INFO")

if __name__ == "__main__":
    main()
