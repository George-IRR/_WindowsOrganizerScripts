import os
import json
import shutil
import webbrowser
import sys

# ==========================================
# DEFAULT CONFIGURATION
# ==========================================
DEFAULT_IGNORED_FOLDERS = {'node_modules', '.git', '__pycache__', 'venv', '.idea', '.vscode'}
DEFAULT_IGNORED_FILES = {'.DS_Store', 'Thumbs.db', 'desktop.ini'}

IGNORED_FOLDERS = DEFAULT_IGNORED_FOLDERS
IGNORED_FILES = DEFAULT_IGNORED_FILES

# ==========================================
# 1. SCANNER & HTML GENERATOR
# ==========================================

def load_config_from_env():
    """Loads ignored folders/files from a .env file."""
    global IGNORED_FOLDERS, IGNORED_FILES
    env_path = '.env'
    if os.path.exists(env_path):
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        items = {item.strip() for item in value.split(',') if item.strip()}
                        if key.strip() == 'IGNORED_FOLDERS': IGNORED_FOLDERS = items
                        elif key.strip() == 'IGNORED_FILES': IGNORED_FILES = items
            print("[INFO] Config loaded from .env")
        except Exception:
            pass

def scan_directory_to_json(root_path):
    """
    Scans the directory and returns a hierarchical JSON-compatible list 
    representing the file tree.
    """
    def build_tree(current_path):
        name = os.path.basename(current_path)
        node = {
            "name": name,
            "path": os.path.relpath(current_path, root_path),
            "type": "folder",
            "children": []
        }
        
        try:
            # Sort: Folders first, then files
            items = sorted(os.listdir(current_path))
            # specific sort to put folders before files
            items.sort(key=lambda x: (not os.path.isdir(os.path.join(current_path, x)), x.lower()))
            
            for item in items:
                full_path = os.path.join(current_path, item)
                
                if os.path.isdir(full_path):
                    if item not in IGNORED_FOLDERS:
                        node["children"].append(build_tree(full_path))
                else:
                    if item not in IGNORED_FILES and item != os.path.basename(__file__) and item != 'privacy_ui.html':
                        node["children"].append({
                            "name": item,
                            "path": os.path.relpath(full_path, root_path),
                            "type": "file"
                        })
        except PermissionError:
            pass
            
        return node

    root_node = build_tree(root_path)
    # The root node itself usually has an empty path in relpath logic if strictly adhering to tree,
    # but let's ensure the root is labeled correctly for the UI.
    root_node['name'] = os.path.basename(root_path)
    return root_node

def generate_html_interface(root_path, tree_data):
    """
    Creates a standalone HTML file with the file tree data embedded.
    """
    json_data = json.dumps(tree_data)
    
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>AI Organizer - Privacy Filter</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #f4f4f9; color: #333; margin: 0; padding: 20px; }}
        .container {{ max-width: 900px; margin: 0 auto; background: white; padding: 25px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ margin-top: 0; font-size: 24px; color: #2c3e50; }}
        .controls {{ background: #eef2f5; padding: 15px; border-radius: 6px; margin-bottom: 20px; border: 1px solid #ddd; }}
        .controls label {{ font-weight: bold; margin-right: 10px; }}
        select {{ padding: 8px; border-radius: 4px; border: 1px solid #ccc; font-size: 14px; width: 300px; }}
        button {{ background: #27ae60; color: white; border: none; padding: 10px 20px; font-size: 16px; border-radius: 5px; cursor: pointer; transition: background 0.2s; }}
        button:hover {{ background: #219150; }}
        .tree-container {{ border: 1px solid #ddd; padding: 15px; height: 500px; overflow-y: auto; background: #fafafa; border-radius: 4px; }}
        ul {{ list-style-type: none; padding-left: 20px; margin: 5px 0; }}
        li {{ margin: 2px 0; }}
        .folder {{ font-weight: bold; color: #2980b9; }}
        .file {{ color: #555; }}
        input[type="checkbox"] {{ margin-right: 8px; }}
        .hidden {{ display: none; }}
        
        /* Toast notification */
        #toast {{ visibility: hidden; min-width: 250px; background-color: #333; color: #fff; text-align: center; border-radius: 2px; padding: 16px; position: fixed; z-index: 1; left: 50%; bottom: 30px; transform: translateX(-50%); }}
        #toast.show {{ visibility: visible; -webkit-animation: fadein 0.5s, fadeout 0.5s 2.5s; animation: fadein 0.5s, fadeout 0.5s 2.5s; }}
        @keyframes fadein {{ from {{bottom: 0; opacity: 0;}} to {{bottom: 30px; opacity: 1;}} }}
        @keyframes fadeout {{ from {{bottom: 30px; opacity: 1;}} to {{bottom: 0; opacity: 0;}} }}
    </style>
</head>
<body>

<div class="container">
    <h1>1. Review & Copy Prompt</h1>
    <p>Uncheck files/folders you want to <b>hide</b> from the AI. Then select a mode and copy.</p>
    
    <div class="controls">
        <label for="modeSelect">Optimization Goal:</label>
        <select id="modeSelect" onchange="renderTree()">
            <option value="files">Organize FILES (Sort docs, images, etc.)</option>
            <option value="folders">Organize APPS/PROJECTS (Group folders only)</option>
        </select>
        <br><br>
        <button onclick="generateAndCopy()">Generate Prompt & Copy to Clipboard</button>
    </div>

    <div class="tree-container" id="treeRoot">
        </div>
</div>

<div id="toast">Prompt copied to clipboard!</div>

<script>
    const treeData = {json_data};
    const rootPath = "{root_path.replace(os.sep, '/')}";

    // --- RENDER LOGIC ---
    function renderTree() {{
        const container = document.getElementById('treeRoot');
        container.innerHTML = ''; // clear
        const mode = document.getElementById('modeSelect').value;
        container.appendChild(createNode(treeData, mode));
    }}

    function createNode(node, mode) {{
        // If mode is folders-only and this is a file, strictly skip rendering it? 
        // Or keep it but unchecked? Let's just render checks for folders in folder mode.
        
        const li = document.createElement('li');
        
        // Checkbox
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.checked = true;
        checkbox.dataset.path = node.path;
        checkbox.dataset.type = node.type;
        checkbox.id = 'cb-' + node.path.replace(/\s/g, '_'); // simple ID

        // If Folder Mode and this is a file, we can hide it or disable it
        if (mode === 'folders' && node.type === 'file') {{
            // We just won't render the checkbox for files in folder mode to keep UI clean
            // actually let's just not render the node at all
            return null; 
        }}

        // Label
        const span = document.createElement('span');
        span.textContent = node.name;
        span.className = node.type;
        
        li.appendChild(checkbox);
        li.appendChild(span);

        // Children
        if (node.children && node.children.length > 0) {{
            const ul = document.createElement('ul');
            node.children.forEach(child => {{
                const childNode = createNode(child, mode);
                if (childNode) ul.appendChild(childNode);
            }});
            li.appendChild(ul);
            
            // Parent Checkbox Logic: if unchecked, uncheck children visual only? 
            // For simplicity, we just use the checkbox state during generation.
            checkbox.addEventListener('change', (e) => {{
                const checked = e.target.checked;
                const children = ul.querySelectorAll('input[type="checkbox"]');
                children.forEach(c => c.checked = checked);
            }});
        }}
        
        return li;
    }}

    // --- PROMPT GENERATION LOGIC ---
    function generateAndCopy() {{
        const mode = document.getElementById('modeSelect').value;
        const checkedBoxes = document.querySelectorAll('input[type="checkbox"]:checked');
        
        let fileListString = "";
        
        // Header
        fileListString += "FILE STRUCTURE TO ANALYZE:\\n";
        fileListString += "Root: " + rootPath + "\\n==================================================\\n";
        
        checkedBoxes.forEach(cb => {{
            // Visual indentation logic is hard to reconstruct perfectly from flat list
            // So we will just list the paths relative to root.
            if(cb.dataset.path !== ".") {{ // skip root dot
               fileListString += cb.dataset.path + "\\n"; 
            }}
        }});

        let prompt = "";
        
        if (mode === 'folders') {{
            prompt += "Instructions for the AI:\\n";
            prompt += "1. Analyze the FOLDER list below.\\n";
            prompt += "2. This is an 'App/Project Organizer'. Focus on grouping folder hierarchies.\\n";
            prompt += "3. Group related folders (e.g., move 'Photoshop' and 'Figma' folders into 'Design Tools').\\n";
            prompt += "4. OUTPUT ONLY RAW JSON (no markdown).\\n";
            prompt += "5. JSON Schema:\\n{{\\n  \\"moves\\": [\\n    {{ \\"source\\": \\"Current_Folder\\", \\"destination\\": \\"New_Category/Current_Folder\\", \\"reason\\": \\"...\\" }}\\n  ]\\n}}\\n";
        }} else {{
            prompt += "Instructions for the AI:\\n";
            prompt += "1. Analyze the FILE list below.\\n";
            prompt += "2. Suggest a file organization strategy (group by extension, date, or context).\\n";
            prompt += "3. OUTPUT ONLY RAW JSON (no markdown).\\n";
            prompt += "4. JSON Schema:\\n{{\\n  \\"moves\\": [\\n    {{ \\"source\\": \\"path/file.ext\\", \\"destination\\": \\"New_Folder/file.ext\\", \\"reason\\": \\"...\\" }}\\n  ]\\n}}\\n";
        }}
        
        prompt += "\\n" + fileListString;

        // Copy to clipboard
        navigator.clipboard.writeText(prompt).then(function() {{
            var x = document.getElementById("toast");
            x.className = "show";
            setTimeout(function(){{ x.className = x.className.replace("show", ""); }}, 3000);
        }}, function(err) {{
            console.error('Async: Could not copy text: ', err);
            alert("Failed to auto-copy. Please check console or permissions.");
        }});
    }}

    // Initial Render
    renderTree();
</script>

</body>
</html>
    """
    
    output_file = "privacy_ui.html"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    return os.path.abspath(output_file)

# ==========================================
# 2. EXECUTION ENGINE
# ==========================================

def execute_moves(json_data, root_path):
    """Parses JSON and moves files/folders."""
    try:
        data = json.loads(json_data)
        moves = data.get("moves", [])
    except json.JSONDecodeError as e:
        print(f"\n[ERROR] Invalid JSON: {e}")
        return

    if not moves:
        print("\n[INFO] No moves found.")
        return

    print(f"\nAI suggested {len(moves)} moves. Review:")
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
# MAIN
# ==========================================
if __name__ == "__main__":
    print("--- AI ORGANIZER WITH PRIVACY UI ---")
    load_config_from_env()

    # 1. Get Directory
    while True:
        target_dir = input("\nEnter full path of folder to organize: ").strip()
        if os.path.isdir(target_dir): break
        print("Invalid directory.")

    print(f"\nScanning {target_dir}...")
    
    # 2. Build Tree Data
    tree_data = scan_directory_to_json(target_dir)
    
    # 3. Generate HTML & Open
    html_path = generate_html_interface(target_dir, tree_data)
    print(f"\n[OPENING UI] Check your browser window: {html_path}")
    print("1. In browser: Uncheck files you want to hide.")
    print("2. In browser: Select Mode (Files or Folders).")
    print("3. In browser: Click 'Generate & Copy'.")
    
    webbrowser.open(f'file://{html_path}')
    
    # 4. Wait for Paste
    print("\n" + "="*60)
    print("WAITING FOR AI RESPONSE")
    print("Once you paste the prompt into the AI, copy the JSON it gives you.")
    print("Paste that JSON below. (Type 'DONE' on a new line to finish)")
    print("="*60)
    
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