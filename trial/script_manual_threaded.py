import os
import yt_dlp
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import queue

load_dotenv()

DOWNLOAD_FOLDER = os.getenv('DOWNLOAD_FOLDER', './Dad_Car_Songs')

# Thread-safe output
print_lock = Lock()

def load_songs_from_file(filename='songs.txt'):
    """Load songs from a text file if it exists"""
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            songs = [line.strip() for line in f if line.strip()]
            return songs
    return []

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
    
    if not songs_list:
        print("❌ No songs provided!")
        print("\nCreate a songs.txt file in this folder with one song per line:")
        print("  Song Name - Artist Name")
        print("  Song Name 2 - Artist Name 2")
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

    print("\n" + "="*50)
    print(f"🎉 Download Complete!")
    print(f"✅ Successful: {success_count}")
    print(f"❌ Failed: {failed_count}")
    print(f"📊 Success Rate: {(success_count/len(songs_list)*100):.1f}%")
    print("="*50)

# --- Main ---
if __name__ == "__main__":
    songs = load_songs_from_file('songs.txt')
    
    if not songs:
        print("❌ No songs found!")
        print("\nCreate a songs.txt file in this folder with one song per line:")
        print("  Song Name - Artist Name")
        print("  Song Name 2 - Artist Name 2")
    else:
        print(f"🎵 Found {len(songs)} songs\n")
        # Use 4 parallel downloads (yt-dlp can be resource-intensive)
        # Adjust based on your internet speed and CPU
        download_songs_threaded(songs, DOWNLOAD_FOLDER, max_workers=4)
