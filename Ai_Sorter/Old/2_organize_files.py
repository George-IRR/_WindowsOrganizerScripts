import os
import json
import shutil

def interactive_organizer(json_file):
    if not os.path.exists(json_file):
        print(f"Error: Could not find '{json_file}'. Please create it with the AI's response.")
        return

    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError:
        print("Error: The JSON file is invalid. Make sure it contains only valid JSON.")
        return

    moves = data.get("moves", [])
    
    if not moves:
        print("No moves found in the JSON file.")
        return

    print(f"\nFound {len(moves)} proposed file moves.\n")
    print("-" * 50)

    for i, move in enumerate(moves, 1):
        src = move['source']
        dst = move['destination']
        reason = move.get('reason', 'Organization')

        # Check if source exists
        if not os.path.exists(src):
            print(f"[{i}/{len(moves)}] SKIPPING: Source file not found: {src}")
            continue

        print(f"\nMove {i}/{len(moves)}")
        print(f"  From:   {src}")
        print(f"  To:     {dst}")
        print(f"  Reason: {reason}")
        
        user_input = input("  >>> Execute this move? (y/n): ").lower().strip()

        if user_input == 'y':
            try:
                # Create destination directory if it doesn't exist
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                
                # Move the file
                shutil.move(src, dst)
                print("  [SUCCESS] File moved.")
            except Exception as e:
                print(f"  [ERROR] Could not move file: {e}")
        else:
            print("  [SKIPPED] Action cancelled by user.")

    print("-" * 50)
    print("\nProcess complete.")

if __name__ == "__main__":
    json_filename = "moves.json"
    print("Ensure you have saved the AI response as 'moves.json' in this folder.")
    interactive_organizer(json_filename)