import zipfile
import os

def pack_and_split_project(source_folder=".", output_name="project_upload", max_size_mb=95):
    """
    Zips a folder while excluding junk (venv, .git) and splits it if it exceeds the size limit.
    """
    # --- CONFIG: Files/Folders to IGNORE ---
    exclusions = {
        '.git', '.venv', 'venv', 'env', 'Result', # Heavy dev folders
        '__pycache__', '.idea', '.vscode',        # Cache and IDE settings
        'prepare_project.py',                     # Don't zip this script itself
        'updated_database.py'                     # Don't zip the previous helper script
    }
    
    temp_zip = "temp_huge_archive.zip"
    limit_bytes = max_size_mb * 1024 * 1024 # Convert MB to Bytes
    
    print(f"📦 Packing '{source_folder}'...")
    print(f"🚫 Ignoring: {', '.join(exclusions)}")

    # 1. Create the Master Zip (Filtered)
    file_count = 0
    with zipfile.ZipFile(temp_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_folder):
            # Remove excluded folders from the search list
            dirs[:] = [d for d in dirs if d not in exclusions]
            
            for file in files:
                # Skip excluded files and other zips
                if file not in exclusions and not file.endswith('.zip') and not file.endswith('.rar'):
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, source_folder)
                    try:
                        zipf.write(file_path, arcname)
                        file_count += 1
                    except PermissionError:
                        print(f"⚠️  Skipping locked file: {file_path}")

    size_mb = os.path.getsize(temp_zip) / (1024 * 1024)
    print(f"✅ Packed {file_count} files. Total size: {size_mb:.2f} MB")

    # 2. Check Size and Split if necessary
    if size_mb <= max_size_mb:
        final_name = f"{output_name}.zip"
        if os.path.exists(final_name): os.remove(final_name)
        os.rename(temp_zip, final_name)
        print(f"🎉 Success! The file is small enough.")
        print(f"👉 Please upload: {final_name}")
    else:
        print(f"⚠️ File is too large (> {max_size_mb} MB). Splitting into parts...")
        part_num = 1
        with open(temp_zip, 'rb') as f:
            while True:
                chunk = f.read(limit_bytes)
                if not chunk:
                    break
                part_filename = f"{output_name}.zip.{part_num:03d}"
                with open(part_filename, 'wb') as chunk_file:
                    chunk_file.write(chunk)
                print(f"   Created part: {part_filename}")
                part_num += 1
        
        os.remove(temp_zip) # Remove the huge temp file
        print(f"🎉 Done! I split the project into {part_num-1} parts.")
        print(f"👉 Please upload ALL files ending in .001, .002, etc.")

# Run the function
if __name__ == "__main__":
    # Gets the folder where this script is located
    current_folder = os.getcwd()
    pack_and_split_project(current_folder)