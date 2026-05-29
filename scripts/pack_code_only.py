import zipfile
import os

def pack_code_only(source_folder=".", output_name="project_code_only.zip"):
    """
    Zips ONLY relevant code and config files. Ignores data, virtual envs, and large assets.
    """
    # Extensions of files we WANT to see (Code & Config)
    allowed_extensions = {
        '.py', '.ipynb', '.md', '.txt', '.json', '.yml', '.yaml', 
        '.csv', '.xml', '.html', '.css', '.js', '.sh', '.bat', '.gitignore'
    }

    # Folders to completely IGNORE
    ignored_folders = {
        'venv', '.venv', 'env', '.git', '.idea', '.vscode', 
        '__pycache__', 'site-packages', 'node_modules', 'build', 'dist',
        'Result', 'data', 'Data', 'pdfs', 'PDFs' # Assuming data folders
    }

    print(f"🔍 Scanning '{source_folder}' for code files...")
    
    file_count = 0
    zip_size = 0

    with zipfile.ZipFile(output_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_folder):
            # Remove ignored folders to prevent walking into them
            dirs[:] = [d for d in dirs if d not in ignored_folders]

            for file in files:
                _, ext = os.path.splitext(file)
                
                # Logic: Only include allowed extensions AND skip large CSVs (>1MB)
                if ext.lower() in allowed_extensions:
                    file_path = os.path.join(root, file)
                    file_size = os.path.getsize(file_path)

                    # Skip CSVs larger than 1MB (likely data, not config)
                    if ext.lower() == '.csv' and file_size > 1024 * 1024:
                        continue
                    
                    # Skip this script itself
                    if file == "pack_code_only.py":
                        continue

                    # Add to Zip
                    arcname = os.path.relpath(file_path, source_folder)
                    zipf.write(file_path, arcname)
                    file_count += 1
                    zip_size += file_size

    print(f"✅ Success! Packed {file_count} code files.")
    print(f"📦 Output File: {output_name}")
    print(f"📊 Total Size: {zip_size / 1024:.2f} KB")

if __name__ == "__main__":
    pack_code_only()