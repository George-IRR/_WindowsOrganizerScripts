import os
import json
import shutil
import subprocess
import sys

# ==========================================
# DEFAULT CONFIGURATION
# ==========================================
# These are used if no .env file is found
DEFAULT_IGNORED_FOLDERS = {}
DEFAULT_IGNORED_FILES = {}

# Globals to be populated
IGNORED_FOLDERS = DEFAULT_IGNORED_FOLDERS
IGNORED_FILES = DEFAULT_IGNORED_FILES

# ==========================================
# HELPER FUNCTIONS
# ==========================================

def load_config_from_env():
    """
    Loads ignored folders/files from a .env file in the current directory.
    Expected format:
    IGNORED_FOLDERS=folder1,folder2
    IGNORED_FILES=file1,file2
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
                if not line or line.startswith('#'):
                    continue
                
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    # Split by comma and clean whitespace
                    items = {item.strip() for item in value.split(',') if item.strip()}
                    
                    if key == 'IGNORED_FOLDERS':
                        IGNORED_FOLDERS = items
                        print(f"  -> Custom IGNORED_FOLDERS loaded ({len(items)} items)")
                    elif key == 'IGNORED_FILES':
                        IGNORED_FILES = items
                        print(f"  -> Custom IGNORED_FILES loaded ({len(items)} items)")
    except Exception as e:
        print(f"[WARNING] Error reading .env file: {e}")

def copy_to_clipboard(text):
    """
    Copies text to the clipboard using the Windows 'clip' command.
    Fallback logic included for non-Windows or failures.
    """
    try:
        # This uses the Windows 'clip' command
        process = subprocess.Popen('clip', stdin=subprocess.PIPE, shell=True)
        process.communicate(input=text.encode('utf-16')) # utf-16 usually required for clip
        print("\n[SUCCESS] The AI Prompt has been copied to your clipboard automatically!")
    except Exception as e:
        print(f"\n[NOTICE] Could not auto-copy to clipboard ({e}).")
        print("Please scroll up and copy the prompt manually.")

def generate_prompt_string(root_path):
    """
    Scans the directory and builds the string to send to the AI.
    """
    output = []
    
    # 1. The Instructions for the AI
    output.append("Instructions for the AI:")
    output.append("1. Analyze the file structure below.")
    output.append("2. Suggest a better file organization/sorting strategy.")
    output.append("3. OUTPUT ONLY A RAW JSON OBJECT (no markdown formatting, no explanations outside the JSON).")
    output.append("4. The JSON must follow this exact schema so my Python script can read it:")
    output.append("")
    output.append("{")
    output.append('    "moves": [')
    output.append('        {')
    output.append('            "source": "path/to/current/file.ext",')
    output.append('            "destination": "path/to/new/folder/file.ext",')
    output.append('            "reason": "Short explanation why"')
    output.append('        }')
    output.append('    ]')
    output.append("}")
    output.append("")
    output.append("If a file should stay, do not include it. Ensure destination folders are logical.")
    output.append("-" * 50)
    output.append("FILE STRUCTURE TO ANALYZE:")
    output.append("")
    output.append(f"Root: {os.path.abspath(root_path)}")
    output.append("=" * 50)

    # 2. The File Tree
    for root, dirs, files in os.walk(root_path):
        # Modify dirs in-place to skip ignored folders
        dirs[:] = [d for d in dirs if d not in IGNORED_FOLDERS]

        level = root.replace(root_path, '').count(os.sep)
        indent = '    ' * level
        
        subdir = os.path.basename(root)
        if level == 0: subdir = "[Root]"
        
        output.append(f"{indent}[{subdir}/]")
        
        subindent = '    ' * (level + 1)
        for file in files:
            # Skip this script itself, the .env file, and ignored files
            if file == os.path.basename(__file__) or file in IGNORED_FILES:
                continue
            
            # Create a clean display path
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, root_path)
            
            output.append(f"{subindent}{file}  <-- Full Path: {rel_path}")

    return "\n".join(output)

def execute_moves(json_data, root_path):
    """
    Parses the JSON and asks user for confirmation on moves.
    """
    try:
        data = json.loads(json_data)
        moves = data.get("moves", [])
    except json.JSONDecodeError as e:
        print(f"\n[ERROR] Invalid JSON provided: {e}")
        return

    if not moves:
        print("\n[INFO] No moves found in the JSON response.")
        return

    print(f"\nAI suggested {len(moves)} moves. Let's review them:")
    print("-" * 50)

    for i, move in enumerate(moves, 1):
        # Construct absolute paths to be safe
        rel_src = move['source']
        rel_dst = move['destination']
        
        abs_src = os.path.join(root_path, rel_src)
        abs_dst = os.path.join(root_path, rel_dst)
        reason = move.get('reason', 'Organization')

        if not os.path.exists(abs_src):
            print(f"[{i}/{len(moves)}] SKIPPING (File not found): {rel_src}")
            continue

        print(f"\nMove {i}/{len(moves)}")
        print(f"  From:   {rel_src}")
        print(f"  To:     {rel_dst}")
        print(f"  Reason: {reason}")
        
        choice = input("  >>> Execute this move? (y/n): ").strip().lower()
        
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
    print("--- AI FILE ORGANIZER (ALL-IN-ONE) ---")
    
    # 0. Load Configuration
    load_config_from_env()

    # 1. Get Target Directory
    while True:
        target_dir = input("\nEnter the full path of the folder to organize: ").strip()
        if os.path.isdir(target_dir):
            break
        print("Invalid directory. Please try again.")

    # 2. Generate and Copy Prompt
    print(f"\nScanning {target_dir}...")
    prompt_text = generate_prompt_string(target_dir)
    
    print("\n" + "="*20 + " GENERATED PROMPT " + "="*20)
    print(prompt_text)
    print("="*60)
    
    copy_to_clipboard(prompt_text)
    
    print("\nINSTRUCTIONS:")
    print("1. Go to your AI chat.")
    print("2. PASTE (Ctrl+V) the text I just copied to your clipboard.")
    print("3. Copy the JSON code block the AI gives you back.")
    print("4. Paste that JSON below.")
    
    # 3. Get JSON Input
    print("\n--- PASTE JSON BELOW (Type 'DONE' on a new line when finished) ---")
    
    json_lines = []
    while True:
        try:
            line = input()
            if line.strip().upper() == 'DONE':
                break
            json_lines.append(line)
        except EOFError:
            break
            
    full_json_input = "\n".join(json_lines)

    # 4. Execute
    if full_json_input.strip():
        execute_moves(full_json_input, target_dir)
    else:
        print("No input received. Exiting.")
        
    input("\nPress Enter to exit...")