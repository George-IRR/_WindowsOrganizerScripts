import os
import json
import shutil
import subprocess
import sys

# ==========================================
# DEFAULT CONFIGURATION
# ==========================================
DEFAULT_IGNORED_FOLDERS = {}
DEFAULT_IGNORED_FILES = {'.DS_Store', 'Thumbs.db', 'desktop.ini'}

IGNORED_FOLDERS = DEFAULT_IGNORED_FOLDERS
IGNORED_FILES = DEFAULT_IGNORED_FILES

# ==========================================
# HELPER FUNCTIONS
# ==========================================

def load_config_from_env():
    """
    Loads ignored folders/files from a .env file.
    """
    global IGNORED_FOLDERS, IGNORED_FILES
    env_path = '.env'
    
    if not os.path.exists(env_path):
        print("[INFO] No .env file found. Using default ignore settings.")
        return

    print(f"[INFO] Loading configuration from {os.path.abspath(env_path)}...")
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'): continue
                
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    items = {item.strip() for item in value.split(',') if item.strip()}
                    
                    if key == 'IGNORED_FOLDERS':
                        IGNORED_FOLDERS = items
                    elif key == 'IGNORED_FILES':
                        IGNORED_FILES = items
    except Exception as e:
        print(f"[WARNING] Error reading .env file: {e}")

def copy_to_clipboard(text):
    """
    Copies text to clipboard using Windows 'clip' or generic fallback.
    """
    try:
        process = subprocess.Popen('clip', stdin=subprocess.PIPE, shell=True)
        process.communicate(input=text.encode('utf-16'))
        print("\n[SUCCESS] AI Prompt copied to clipboard!")
    except Exception as e:
        print(f"\n[NOTICE] Could not auto-copy ({e}). Please copy manually.")

def generate_prompt_string(root_path, only_folders=False):
    """
    Scans directory and selects one of two prompts based on only_folders mode.
    """
    output = []
    
    # ==========================================
    # PROMPT SELECTION LOGIC
    # ==========================================
    if only_folders:
        # --- PROMPT A: FOLDERS ONLY (APP/PROJECT MOVING) ---
        output.append("Instructions for the AI:")
        output.append("1. Analyze the FOLDER structure below (Files are hidden).")
        output.append("2. This is an 'App/Project Organizer'. Focus on grouping folder hierarchies.")
        output.append("3. Group related folders (e.g., move 'Adobe Photoshop' and 'Figma' into a 'Design Tools' folder).")
        output.append("4. OUTPUT ONLY A RAW JSON OBJECT (no markdown).")
        output.append("5. Use this JSON schema:")
        output.append("{")
        output.append('    "moves": [')
        output.append('        {')
        output.append('            "source": "Folder_Name",')
        output.append('            "destination": "Category_Folder/Folder_Name",')
        output.append('            "reason": "Grouping design apps together"')
        output.append('        }')
        output.append('    ]')
        output.append("}")
    else:
        # --- PROMPT B: EVERYTHING (FILE SORTING) ---
        output.append("Instructions for the AI:")
        output.append("1. Analyze the file structure below.")
        output.append("2. Suggest a file organization strategy (group by extension, date, or context).")
        output.append("3. OUTPUT ONLY A RAW JSON OBJECT (no markdown).")
        output.append("4. Use this JSON schema:")
        output.append("{")
        output.append('    "moves": [')
        output.append('        {')
        output.append('            "source": "path/to/file.png",')
        output.append('            "destination": "Images/file.png",')
        output.append('            "reason": "Moving images to image folder"')
        output.append('        }')
        output.append('    ]')
        output.append("}")

    output.append("-" * 50)
    output.append("CURRENT STRUCTURE:")
    output.append(f"Root: {os.path.abspath(root_path)}")
    output.append("=" * 50)

    # ==========================================
    # FILE TREE GENERATION
    # ==========================================
    for root, dirs, files in os.walk(root_path):
        # Skip ignored folders
        dirs[:] = [d for d in dirs if d not in IGNORED_FOLDERS]

        level = root.replace(root_path, '').count(os.sep)
        indent = '    ' * level
        
        subdir = os.path.basename(root)
        if level == 0: subdir = "[Root]"
        
        output.append(f"{indent}[{subdir}/]")
        
        # If in 'Only Folders' mode, we stop here and don't list files
        if only_folders:
            continue

        # Otherwise list files
        subindent = '    ' * (level + 1)
        for file in files:
            if file == os.path.basename(__file__) or file in IGNORED_FILES:
                continue
            
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, root_path)
            output.append(f"{subindent}{file}  <-- Full Path: {rel_path}")

    return "\n".join(output)

def execute_moves(json_data, root_path):
    """
    Parses JSON and moves files/folders.
    """
    try:
        data = json.loads(json_data)
        moves = data.get("moves", [])
    except json.JSONDecodeError as e:
        print(f"\n[ERROR] Invalid JSON: {e}")
        return

    if not moves:
        print("\n[INFO] No moves found.")
        return

    print(f"\nAI suggested {len(moves)} moves. Let's review:")
    print("-" * 50)

    for i, move in enumerate(moves, 1):
        rel_src = move['source']
        rel_dst = move['destination']
        reason = move.get('reason', 'Organization')
        
        abs_src = os.path.join(root_path, rel_src)
        abs_dst = os.path.join(root_path, rel_dst)

        if not os.path.exists(abs_src):
            print(f"[{i}] SKIPPING (Not found): {rel_src}")
            continue

        print(f"\nMove {i}/{len(moves)}")
        print(f"  From:   {rel_src}")
        print(f"  To:     {rel_dst}")
        print(f"  Reason: {reason}")
        
        choice = input("  >>> Execute? (y/n): ").strip().lower()
        
        if choice == 'y':
            try:
                os.makedirs(os.path.dirname(abs_dst), exist_ok=True)
                shutil.move(abs_src, abs_dst)
                print("  [SUCCESS] Moved.")
            except Exception as e:
                print(f"  [ERROR] Failed: {e}")
        else:
            print("  [SKIPPED]")

# ==========================================
# MAIN EXECUTION
# ==========================================
if __name__ == "__main__":
    print("--- AI ORGANIZER (DUAL MODE) ---")
    
    load_config_from_env()

    while True:
        target_dir = input("\nEnter full path of folder to organize: ").strip()
        if os.path.isdir(target_dir): break
        print("Invalid directory.")

    print("\nSelect Scan Mode:")
    print("1. FILES & FOLDERS (General Cleanup) - Sorts files into folders.")
    print("2. FOLDERS ONLY (App/Project Organizer) - Groups app folders together.")
    mode = input("Enter 1 or 2: ").strip()
    
    only_folders_mode = (mode == '2')

    print(f"\nScanning {target_dir}...")
    prompt = generate_prompt_string(target_dir, only_folders=only_folders_mode)
    
    copy_to_clipboard(prompt)
    
    print("\nSTEP 1: Paste the text from your clipboard into the AI.")
    print("STEP 2: Copy the JSON response from the AI.")
    print("STEP 3: Paste the JSON below (Type 'DONE' on a new line when finished).")
    print("-" * 60)
    
    json_lines = []
    while True:
        try:
            line = input()
            if line.strip().upper() == 'DONE': break
            json_lines.append(line)
        except EOFError: break
            
    full_json = "\n".join(json_lines)

    if full_json.strip():
        execute_moves(full_json, target_dir)
    else:
        print("No input received.")
        
    input("\nPress Enter to exit...")