import os
import sys
import shutil
import hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
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

# Thread-safe locks
print_lock = Lock()
size_map_lock = Lock()

def get_file_hash(filepath, chunk_size=65536):
    """Calculate SHA256 hash of a file"""
    try:
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(chunk_size), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        with print_lock:
            print(f"  ❌ Error hashing {filepath}: {e}")
        return None

def scan_directory_for_sizes(directory):
    """Scan directory and create a map of file sizes to lists of file paths"""
    size_map = {}
    
    if not os.path.exists(directory):
        return size_map
    
    print(f"Scanning {directory} for existing files (by size)...")
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(('.mp3', '.m4a', '.wav', '.flac', '.opus', '.aac')):
                filepath = os.path.join(root, file)
                try:
                    size = os.path.getsize(filepath)
                    if size not in size_map:
                        size_map[size] = []
                    size_map[size].append(filepath)
                except Exception:
                    pass
                    
    count = sum(len(paths) for paths in size_map.values())
    print(f"Found {count} existing audio files\n")
    return size_map

def copy_single_file(args):
    """Copy a single file - used by thread pool"""
    index, total, source, destination, existing_sizes = args
    
    filename = os.path.basename(source)
    
    with print_lock:
        print(f"[{index}/{total}] 📋 Processing: {filename}")
    
    try:
        source_size = os.path.getsize(source)
        
        # Check if destination file exists and has same size
        if os.path.exists(destination):
            dest_size = os.path.getsize(destination)
            if dest_size == source_size:
                with print_lock:
                    print(f"  ⏭️  Skipped (already copied with same size)\n")
                return False
                
        # Check for duplicates using size, then hash (thread-safe snapshot of candidate paths)
        candidate_paths = []
        with size_map_lock:
            if source_size in existing_sizes:
                candidate_paths = list(existing_sizes[source_size])
        
        is_duplicate = False
        if candidate_paths:
            source_hash = get_file_hash(source)
            if source_hash:
                for existing_path in candidate_paths:
                    if os.path.exists(existing_path) and get_file_hash(existing_path) == source_hash:
                        is_duplicate = True
                        break
                        
        if is_duplicate:
            with print_lock:
                print(f"  ⏭️  Skipped (duplicate found by hash)\n")
            return False
        
        # Copy file
        with print_lock:
            print(f"  📤 Copying...")
        
        shutil.copy2(source, destination)
        
        with print_lock:
            file_size_mb = source_size / (1024 * 1024)
            print(f"  ✅ Copied ({file_size_mb:.1f} MB)\n")
        
        # Update existing sizes map in thread-safe manner
        with size_map_lock:
            if source_size not in existing_sizes:
                existing_sizes[source_size] = []
            existing_sizes[source_size].append(destination)
        
        return True
        
    except Exception as e:
        with print_lock:
            print(f"  ❌ Error: {str(e)[:100]}\n")
        return False

def copy_songs_to_pendrive(source_folder='Dad_Car_Songs', 
                           pendrive_path=None, 
                           max_workers=4,
                           check_duplicates=True):
    """Copy songs to pen drive with duplicate detection using multithreading"""
    
    print("="*60)
    print("📱 COPYING TO PEN DRIVE (Multi-threaded)")
    print("="*60 + "\n")
    
    # If no path specified, ask user
    if not pendrive_path:
        print("Available drives:")
        import string
        for drive in string.ascii_uppercase:
            drive_letter = f"{drive}:\\"
            if os.path.exists(drive_letter):
                try:
                    import ctypes
                    free = ctypes.c_ulonglong()
                    ctypes.windll.kernel32.GetDiskFreeSpaceEx(
                        ctypes.c_wchar_p(drive_letter), 
                        None, None, ctypes.pointer(free)
                    )
                    free_gb = free.value / (1024**3)
                    print(f"  {drive_letter} ({free_gb:.1f} GB free)")
                except Exception:
                    print(f"  {drive_letter}")
        
        pendrive_path = input("\nEnter pen drive path (e.g., E:\\Music): ").strip()
    
    if not os.path.exists(pendrive_path):
        try:
            os.makedirs(pendrive_path, exist_ok=True)
            print(f"✅ Created folder: {pendrive_path}\n")
        except Exception as e:
            print(f"❌ Could not access or create path: {pendrive_path} ({e})")
            return False
    
    if not os.path.exists(source_folder):
        print(f"❌ Source folder not found: {source_folder}")
        return False
    
    dest_subfolder = pendrive_path
    print(f"✅ Destination: {dest_subfolder}\n")
    
    # Get list of songs to copy
    print(f"📂 Scanning source: {os.path.abspath(source_folder)}")
    songs_to_copy = []
    
    for file in os.listdir(source_folder):
        if file.lower().endswith(('.mp3', '.m4a', '.wav', '.flac', '.opus', '.aac')):
            source_path = os.path.join(source_folder, file)
            if os.path.isfile(source_path):
                songs_to_copy.append(source_path)
    
    print(f"Found {len(songs_to_copy)} songs to process\n")
    
    if not songs_to_copy:
        print("❌ No songs found in source folder")
        return False
    
    # Scan pen drive for existing files if checking duplicates
    existing_sizes = {}
    if check_duplicates:
        print(f"📂 Scanning pen drive: {dest_subfolder}")
        existing_sizes = scan_directory_for_sizes(dest_subfolder)
    
    # Prepare copy tasks
    tasks = []
    for i, source_path in enumerate(songs_to_copy):
        filename = os.path.basename(source_path)
        dest_path = os.path.join(dest_subfolder, filename)
        tasks.append((i+1, len(songs_to_copy), source_path, dest_path, existing_sizes))
    
    print("Starting copy process...\n")
    
    copied_count = 0
    skipped_count = 0
    failed_count = 0
    
    start_time = time.time()
    
    # Use ThreadPoolExecutor for parallel copying
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(copy_single_file, task): task for task in tasks}
        
        completed = 0
        for future in as_completed(futures):
            try:
                result = future.result()
                if result:
                    copied_count += 1
                else:
                    skipped_count += 1
            except Exception as e:
                with print_lock:
                    print(f"❌ Thread error: {e}\n")
                failed_count += 1
            
            completed += 1
            if completed % 5 == 0 or completed == len(songs_to_copy):
                progress = (completed / len(songs_to_copy)) * 100
                with print_lock:
                    print(f"📊 Progress: {completed}/{len(songs_to_copy)} ({progress:.0f}%)")
    
    elapsed_time = time.time() - start_time
    
    # Final summary
    print("\n" + "="*60)
    print("✨ Copy Complete!")
    print("="*60)
    print(f"📤 Copied:  {copied_count}")
    print(f"⏭️  Skipped: {skipped_count} (duplicates / already present)")
    print(f"❌ Failed:  {failed_count}")
    print(f"📁 Destination: {dest_subfolder}")
    print(f"⏱️  Time: {elapsed_time:.1f} seconds")
    print("="*60 + "\n")
    
    return True

if __name__ == "__main__":
    print("\n" + "📱"*30)
    print("     PEN DRIVE COPY UTILITY")
    print("📱"*30 + "\n")
    
    # Configuration
    SOURCE_FOLDER = './Dad_Car_Songs'  # Folder with downloaded songs
    PENDRIVE_PATH = r'D:\Spotify songs'  # Pen drive path with existing songs
    MAX_WORKERS = 8  # Number of parallel copy threads
    CHECK_DUPLICATES = True  # Enable duplicate detection
    
    # Run copy process
    copy_songs_to_pendrive(
        source_folder=SOURCE_FOLDER,
        pendrive_path=PENDRIVE_PATH,
        max_workers=MAX_WORKERS,
        check_duplicates=CHECK_DUPLICATES
    )
