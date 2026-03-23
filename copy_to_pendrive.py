import os
import shutil
import hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import time

# Thread-safe output
print_lock = Lock()

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

def scan_directory_for_hashes(directory):
    """Scan directory and create hash map of all files"""
    hash_map = {}
    
    if not os.path.exists(directory):
        return hash_map
    
    print(f"Scanning {directory} for existing files...")
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(('.mp3', '.m4a', '.wav', '.flac')):
                filepath = os.path.join(root, file)
                file_hash = get_file_hash(filepath)
                if file_hash:
                    hash_map[filepath] = file_hash
    
    print(f"Found {len(hash_map)} existing audio files\n")
    return hash_map

def copy_single_file(args):
    """Copy a single file - used by thread pool"""
    index, total, source, destination, existing_hashes = args
    
    filename = os.path.basename(source)
    
    with print_lock:
        print(f"[{index}/{total}] 📋 Processing: {filename}")
    
    try:
        # Calculate hash of source file
        source_hash = get_file_hash(source)
        if not source_hash:
            with print_lock:
                print(f"  ❌ Could not hash file\n")
            return False
        
        # Check if file already exists on pen drive (by hash)
        for existing_file, existing_hash in existing_hashes.items():
            if source_hash == existing_hash:
                with print_lock:
                    print(f"  ⏭️  Skipped (duplicate found)\n")
                return False
        
        # Check if destination file exists
        if os.path.exists(destination):
            dest_hash = get_file_hash(destination)
            if dest_hash == source_hash:
                with print_lock:
                    print(f"  ⏭️  Skipped (already copied)\n")
                return False
        
        # Copy file
        with print_lock:
            print(f"  📤 Copying...")
        
        shutil.copy2(source, destination)
        
        with print_lock:
            file_size_mb = os.path.getsize(destination) / (1024 * 1024)
            print(f"  ✅ Copied ({file_size_mb:.1f} MB)\n")
        
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
                    # Get drive info
                    import ctypes
                    free = ctypes.c_ulonglong()
                    ctypes.windll.kernel32.GetDiskFreeSpaceEx(
                        ctypes.c_wchar_p(drive_letter), 
                        None, None, ctypes.pointer(free)
                    )
                    free_gb = free.value / (1024**3)
                    print(f"  {drive_letter} ({free_gb:.1f} GB free)")
                except:
                    print(f"  {drive_letter}")
        
        pendrive_path = input("\nEnter pen drive path (e.g., E:\\Music): ").strip()
    
    if not os.path.exists(pendrive_path):
        print(f"❌ Path not found: {pendrive_path}")
        return False
    
    if not os.path.exists(source_folder):
        print(f"❌ Source folder not found: {source_folder}")
        return False
    
    # Use the pen drive path directly (no subfolder creation)
    dest_subfolder = pendrive_path
    if not os.path.exists(dest_subfolder):
        os.makedirs(dest_subfolder)
        print(f"✅ Created folder: {dest_subfolder}\n")
    else:
        print(f"✅ Destination: {dest_subfolder}\n")
    
    # Get list of songs to copy
    print(f"📂 Scanning source: {os.path.abspath(source_folder)}")
    songs_to_copy = []
    
    for file in os.listdir(source_folder):
        if file.endswith(('.mp3', '.m4a', '.wav', '.flac')):
            source_path = os.path.join(source_folder, file)
            if os.path.isfile(source_path):
                songs_to_copy.append(source_path)
    
    print(f"Found {len(songs_to_copy)} songs to process\n")
    
    if not songs_to_copy:
        print("❌ No songs found in source folder")
        return False
    
    # Scan pen drive for existing files if checking duplicates
    existing_hashes = {}
    if check_duplicates:
        print(f"📂 Scanning pen drive: {dest_subfolder}")
        existing_hashes = scan_directory_for_hashes(dest_subfolder)
    
    # Prepare copy tasks
    tasks = []
    for i, source_path in enumerate(songs_to_copy):
        filename = os.path.basename(source_path)
        dest_path = os.path.join(dest_subfolder, filename)
        tasks.append((i+1, len(songs_to_copy), source_path, dest_path, existing_hashes))
    
    print("Starting copy process...\n")
    
    copied_count = 0
    skipped_count = 0
    failed_count = 0
    total_size_copied = 0
    
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
            if completed % 5 == 0:
                progress = (completed / len(songs_to_copy)) * 100
                with print_lock:
                    print(f"📊 Progress: {completed}/{len(songs_to_copy)} ({progress:.0f}%)")
    
    elapsed_time = time.time() - start_time
    
    # Final summary
    print("\n" + "="*60)
    print("✨ Copy Complete!")
    print("="*60)
    print(f"📤 Copied:  {copied_count}")
    print(f"⏭️  Skipped: {skipped_count} (duplicates)")
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
    MAX_WORKERS = 10  # Number of parallel copy threads
    CHECK_DUPLICATES = True  # Enable duplicate detection
    
    # Run copy process
    copy_songs_to_pendrive(
        source_folder=SOURCE_FOLDER,
        pendrive_path=PENDRIVE_PATH,
        max_workers=MAX_WORKERS,
        check_duplicates=CHECK_DUPLICATES
    )
