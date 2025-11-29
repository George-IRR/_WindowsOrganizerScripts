import os

def generate_tree_with_prompt(startpath, output_file):
    # ---------------------------------------------------------
    # CONFIGURATION: Ignored items
    # ---------------------------------------------------------
    IGNORED_FOLDERS = {
        '.git', 
        '__pycache__', 
        'node_modules', 
        'venv', 
        'env', 
        '.idea', 
        '.vscode', 
        'build', 
        'dist',
        'target'
    }

    IGNORED_FILES = {
        '.env', 
        '.DS_Store', 
        'Thumbs.db', 
        'secrets.json'
    }

    # ---------------------------------------------------------
    # THE PROMPT HEADER
    # This instructs the AI (me) on how to format the response
    # ---------------------------------------------------------
    ai_prompt = """
Instructions for the AI:
1. Analyze the file structure below.
2. Suggest a better file organization/sorting strategy.
3. OUTPUT ONLY A RAW JSON OBJECT (no markdown formatting, no explanations outside the JSON).
4. The JSON must follow this exact schema so my Python script can read it:

{
    "moves": [
        {
            "source": "path/to/current/file.ext",
            "destination": "path/to/new/folder/file.ext",
            "reason": "Short explanation why"
        }
    ]
}

If a file should stay, do not include it. Ensure destination folders are logical.
---------------------------------------------------------
FILE STRUCTURE TO ANALYZE:
"""

    with open(output_file, 'w', encoding='utf-8') as f:
        # Write the Prompt First
        f.write(ai_prompt)
        f.write("\n")
        
        # Write the Tree
        f.write(f"Root: {os.path.abspath(startpath)}\n")
        f.write("=" * 50 + "\n")
        
        for root, dirs, files in os.walk(startpath):
            dirs[:] = [d for d in dirs if d not in IGNORED_FOLDERS]

            level = root.replace(startpath, '').count(os.sep)
            indent = '    ' * level
            
            subdir = os.path.basename(root)
            if level == 0: subdir = startpath
            f.write(f"{indent}[{subdir}/]\n")
            
            subindent = '    ' * (level + 1)
            for file in files:
                if (file == output_file or 
                    file == os.path.basename(__file__) or 
                    file == "2_organize_files.py" or
                    file in IGNORED_FILES):
                    continue
                    
                # We write the full relative path so the AI knows exactly where the file is
                relative_path = os.path.join(root, file)
                display_path = os.path.relpath(relative_path, startpath)
                f.write(f"{subindent}{file}  <-- Full Path: {display_path}\n")

if __name__ == "__main__":
    output_filename = "file_structure_prompt.txt"
    current_directory = "."
    
    print(f"Scanning files in {os.path.abspath(current_directory)}...")
    try:
        generate_tree_with_prompt(current_directory, output_filename)
        print(f"Success! Open '{output_filename}'.")
        print("ACTION: Copy the ENTIRE content of that file and paste it into the AI chat.")
    except Exception as e:
        print(f"An error occurred: {e}")