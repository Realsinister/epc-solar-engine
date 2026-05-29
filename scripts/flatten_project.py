import os

def flatten_project(output_file="full_project_code.txt"):
    # Files we want to read
    extensions = {'.py', '.md', '.yaml', '.yml', '.json', '.txt'}
    
    # Folders to IGNORE completely
    ignore_folders = {
        'venv', '.venv', 'env', '.git', '__pycache__', 
        '.idea', '.vscode', 'site-packages', 'build', 'dist',
        'data', 'Data', 'result', 'Result', 'pdfs', 'PDFs'
    }

    # Files to IGNORE
    ignore_files = {
        'flatten_project.py', 
        'package-lock.json',
        'yarn.lock'
    }

    print(f"🚀 Scanning project...")
    
    with open(output_file, 'w', encoding='utf-8') as outfile:
        # Write a header
        outfile.write("PROJECT CODE DUMP\n")
        outfile.write("=================\n\n")

        for root, dirs, files in os.walk("."):
            # Modify dirs in-place to skip ignored folders
            dirs[:] = [d for d in dirs if d not in ignore_folders]
            
            for file in files:
                if file in ignore_files:
                    continue
                
                _, ext = os.path.splitext(file)
                if ext.lower() in extensions:
                    file_path = os.path.join(root, file)
                    
                    # Write file delimiter
                    outfile.write(f"\n{'='*50}\n")
                    outfile.write(f"FILE: {file_path}\n")
                    outfile.write(f"{'='*50}\n")
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as infile:
                            outfile.write(infile.read())
                            outfile.write("\n") # Ensure newline at end
                        print(f"  + Added: {file_path}")
                    except Exception as e:
                        print(f"  ! Error reading {file_path}: {e}")

    print(f"\n✅ Done! All code is saved in: {output_file}")

if __name__ == "__main__":
    flatten_project()