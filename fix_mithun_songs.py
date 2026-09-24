import os
import re
import sys
import shutil
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import yt_dlp

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

print_lock = Lock()
TARGET_DIR = os.path.abspath('./Mithun_songs')
LIBRARY_DIRS = [os.path.abspath('./Dad_Car_Songs'), os.path.abspath('./Spotify songs')]

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

def clean_song_name(filename):
    """Extract clean song name from filename by stripping extensions and metadata."""
    name = re.sub(r'(\.mp4)?\.part$', '', filename, flags=re.IGNORECASE)
    name = re.sub(r'\.mp3$', '', name, flags=re.IGNORECASE)
    return name.strip()

def find_matching_file_in_libraries(song_name, library_dirs):
    """Find matching MP3 in existing libraries (Dad_Car_Songs, Spotify songs)."""
    norm_song = re.sub(r'[<>:"/\\|?*]', '', song_name).strip().lower()
    
    title_part = norm_song
    artist_part = ""
    if ' - ' in norm_song:
        parts = norm_song.split(' - ', 1)
        title_part = parts[0].strip()
        artist_part = parts[1].strip()
        
    for lib_dir in library_dirs:
        if not os.path.exists(lib_dir):
            continue
        for f in os.listdir(lib_dir):
            if f.lower().endswith('.mp3'):
                f_base = os.path.splitext(f)[0].lower()
                
                # 1. Exact or cleaned match
                if norm_song == f_base or title_part == f_base:
                    return os.path.join(lib_dir, f)
                
                # 2. Title & artist containment
                if title_part and len(title_part) > 3 and title_part in f_base:
                    if not artist_part:
                        return os.path.join(lib_dir, f)
                    primary_artist = artist_part.split(',')[0].strip()
                    if primary_artist and len(primary_artist) > 2 and primary_artist in f_base:
                        return os.path.join(lib_dir, f)
    return None

def download_track(args):
    """Download single missing song from YouTube to MP3."""
    index, total, song_title, target_dir, ffmpeg_dir = args
    
    with print_lock:
        print(f"[{index}/{total}] 🎵 Downloading from YouTube: {song_title}")
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(target_dir, '%(title)s.%(ext)s'),
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
    
    if ffmpeg_dir:
        ydl_opts['ffmpeg_location'] = ffmpeg_dir
        
    for query_template in [f"{song_title} official audio", song_title]:
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch1:{query_template}", download=True)
                if info:
                    with print_lock:
                        print(f"  ✅ Downloaded MP3: {song_title}\n")
                    return 'downloaded'
        except Exception:
            time.sleep(1)
            
    with print_lock:
        print(f"  ❌ Failed to download: {song_title}\n")
    return 'failed'

def main():
    print("\n" + "="*70)
    print("🚀 MITHUN_SONGS .PART TO .MP3 RECOVERY & CONVERTER")
    print("="*70)
    
    if not os.path.exists(TARGET_DIR):
        print(f"❌ Folder not found: {TARGET_DIR}")
        return
    
    ffmpeg_dir = get_ffmpeg_dir()
    if ffmpeg_dir:
        print(f"✅ FFmpeg found: {ffmpeg_dir}")
    else:
        print("⚠️  FFmpeg not found! Audio conversion to MP3 may fail.")
    
    # 1. Collect all .part files
    all_files = os.listdir(TARGET_DIR)
    part_files = [f for f in all_files if f.endswith(('.part', '.ytdl'))]
    existing_mp3s = [f for f in all_files if f.lower().endswith('.mp3')]
    
    print(f"\n📂 Target directory: {TARGET_DIR}")
    print(f"📊 Current status: {len(existing_mp3s)} MP3 files | {len(part_files)} .part files to fix")
    
    if not part_files:
        print("\n🎉 No .part files found! All files are already in .mp3 format.")
        return
    
    # 2. Extract song names
    songs_to_process = []
    for f in part_files:
        song_name = clean_song_name(f)
        songs_to_process.append((f, song_name))
    
    print(f"\n⚡ STEP 1: Checking local libraries (Dad_Car_Songs & Spotify songs)...")
    copied_count = 0
    needs_download = []
    
    for orig_part_file, song_name in songs_to_process:
        dest_mp3 = os.path.join(TARGET_DIR, f"{song_name}.mp3")
        
        # Check if already present in destination
        if any(clean_song_name(m).lower() == song_name.lower() for m in os.listdir(TARGET_DIR) if m.lower().endswith('.mp3')):
            try:
                os.remove(os.path.join(TARGET_DIR, orig_part_file))
            except Exception:
                pass
            continue
            
        # Check in local libraries
        matching_lib_file = find_matching_file_in_libraries(song_name, LIBRARY_DIRS)
        if matching_lib_file and os.path.exists(matching_lib_file):
            try:
                shutil.copy2(matching_lib_file, dest_mp3)
                copied_count += 1
                try:
                    os.remove(os.path.join(TARGET_DIR, orig_part_file))
                except Exception:
                    pass
                print(f"  📂 Copied from library: {os.path.basename(matching_lib_file)}")
            except Exception:
                needs_download.append((orig_part_file, song_name))
        else:
            needs_download.append((orig_part_file, song_name))
    
    print(f"\n✅ Copied {copied_count} songs directly from local libraries!")
    print(f"🌐 Remaining songs to download from YouTube: {len(needs_download)}")
    
    # 3. Download remaining missing songs
    download_success = 0
    download_failed = 0
    
    if needs_download:
        print(f"\n⚡ STEP 2: Downloading {len(needs_download)} missing songs (8 parallel threads)...")
        tasks = [
            (i+1, len(needs_download), song_name, TARGET_DIR, ffmpeg_dir)
            for i, (part_f, song_name) in enumerate(needs_download)
        ]
        
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(download_track, task): task for task in tasks}
            for future in as_completed(futures):
                res = future.result()
                if res == 'downloaded':
                    download_success += 1
                else:
                    download_failed += 1
    
    # 4. Clean up any remaining .part files
    print("\n🧹 STEP 3: Cleaning up all .part files...")
    cleaned_count = 0
    for f in os.listdir(TARGET_DIR):
        if f.endswith(('.part', '.ytdl')):
            try:
                os.remove(os.path.join(TARGET_DIR, f))
                cleaned_count += 1
            except Exception:
                pass
    
    # 5. Final Report
    final_files = os.listdir(TARGET_DIR)
    final_mp3s = [f for f in final_files if f.lower().endswith('.mp3')]
    final_parts = [f for f in final_files if f.endswith(('.part', '.ytdl'))]
    
    print("\n" + "="*70)
    print("🎉 MITHUN_SONGS FIX COMPLETE!")
    print(f"✅ Songs Reused from Library: {copied_count}")
    print(f"✅ Songs Downloaded to MP3:   {download_success}")
    if download_failed > 0:
        print(f"⚠️  Downloads with issues:      {download_failed}")
    print(f"🗑️  .part files deleted:        {cleaned_count}")
    print(f"🎵 Total MP3 files now:        {len(final_mp3s)}")
    print(f"📁 Remaining .part files:      {len(final_parts)}")
    print("="*70 + "\n")

if __name__ == '__main__':
    main()
