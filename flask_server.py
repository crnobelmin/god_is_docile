import os
import base64
import subprocess
from datetime import datetime
from flask import Flask, request, redirect, send_from_directory, jsonify

# --- Settings and Directories ---
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}
BASE_DIR = os.path.expanduser('~/projects/god_is_docile')
IMAGE_FOLDER = os.path.join(BASE_DIR, 'image_files')
AUDIO_FOLDER = os.path.join(BASE_DIR, 'audio_files')
SIG_FOLDER = os.path.join(BASE_DIR, 'signatures')

for folder in [IMAGE_FOLDER, AUDIO_FOLDER, SIG_FOLDER]:
    os.makedirs(folder, exist_ok=True)

app = Flask(
    __name__
)

# --- GLOBAL INSTALLATION STATE ---
# This keeps track of the active group of 4 currently inside the installation space.
CURRENT_GROUP_ID = "group_001_initial_session"


# --- HTML TEMPLATES ---

# 1. The Mobile Canvas Page (Updated to collect Visitor Name)
HTML_SIGNATURE_PAD = """
<!doctype html>
<html lang="en">
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Visitor Signature Pad</title>
    <style>
        body { font-family: sans-serif; background: #121212; color: #e0e0e0; text-align: center; margin: 0; padding: 10px; overflow: hidden; }
        h1 { margin: 10px 0 5px 0; font-size: 1.1rem; color: #007bff; }
        .meta-text { font-size: 13px; color: #888; margin-bottom: 10px; }
        input[type=text] { 
            width: 80%; padding: 10px; margin-bottom: 10px; 
            background: #1a1a1a; border: 1px solid #444; color: white; 
            border-radius: 4px; font-size: 14px; text-align: center;
        }
        #sig-canvas { background: #fff; border-radius: 8px; cursor: crosshair; touch-action: none; margin: 0 auto; display: block; }
        .controls { margin-top: 15px; }
        button { padding: 12px 20px; font-size: 15px; border: none; border-radius: 4px; cursor: pointer; margin: 5px; font-weight: bold; }
        #clear-btn { background: #333; color: white; }
        #submit-btn { background: #28a745; color: white; }
    </style>
</head>
<body>
    <h1>✍️ Leave Your Sonic Signature</h1>
    <div class="meta-text">Connected to Session: <b style="color:#fff;">{{ group_id }}</b></div>
    
    <input type="text" id="visitor-name" placeholder="Enter your name or initials" required>
    <canvas id="sig-canvas"></canvas>
    
    <div class="controls">
        <button id="clear-btn">Clear Canvas</button>
        <button id="submit-btn">Lock In Signature</button>
    </div>

    <script>
        const canvas = document.getElementById('sig-canvas');
        const ctx = canvas.getContext('2d');
        let drawing = false;

        // Dynamic viewport allocation
        canvas.width = window.innerWidth - 30;
        canvas.height = window.innerHeight * 0.55;

        ctx.strokeStyle = "#000";
        ctx.lineWidth = 4;
        ctx.lineCap = "round";

        function start(e) { drawing = true; draw(e); }
        function end() { drawing = false; ctx.beginPath(); }
        function draw(e) {
            if (!drawing) return;
            const rect = canvas.getBoundingClientRect();
            const x = (e.clientX || e.touches[0].clientX) - rect.left;
            const y = (e.clientY || e.touches[0].clientY) - rect.top;
            ctx.lineTo(x, y);
            ctx.stroke();
            ctx.beginPath();
            ctx.moveTo(x, y);
        }

        canvas.addEventListener('mousedown', start);
        canvas.addEventListener('mousemove', draw);
        canvas.addEventListener('mouseup', end);
        canvas.addEventListener('touchstart', start);
        canvas.addEventListener('touchmove', draw);
        canvas.addEventListener('touchend', end);

        document.getElementById('clear-btn').onclick = () => ctx.clearRect(0, 0, canvas.width, canvas.height);

        document.getElementById('submit-btn').onclick = () => {
            const nameInput = document.getElementById('visitor-name').value.trim();
            if (!nameInput) {
                alert("Please enter your name before submitting your signature!");
                return;
            }
            
            const dataURL = canvas.toDataURL('image/png');
            fetch('/upload_signature', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    image: dataURL,
                    visitor_name: nameInput
                })
            }).then(res => res.json()).then(data => {
                alert("Signature locked into the core sound engine!");
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                document.getElementById('visitor-name').value = "";
            });
        };
    </script>
</body>
</html>
"""

# 2. Behind-the-Scenes Operator Dashboard to cycle groups
HTML_OPERATOR_PANEL = """
<!doctype html>
<html lang="en">
<head>
    <title>Engine Console - Operator Panel</title>
    <style>
        body { font-family: sans-serif; background: #0a0a0a; color: #cbd5e1; text-align: center; padding-top: 50px; }
        .panel { background: #1e293b; max-width: 500px; margin: 0 auto; padding: 30px; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.5); }
        input[type=text] { width: 80%; padding: 12px; margin: 15px 0; font-size: 16px; border-radius: 6px; border: 1px solid #475569; background: #0f172a; color: white; }
        input[type=submit] { background: #3b82f6; color: white; border: none; padding: 12px 24px; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 16px; }
        input[type=submit]:hover { background: #2563eb; }
        .status { margin-top: 20px; font-size: 14px; color: #94a3b8; }
    </style>
</head>
<body>
    <div class="panel">
        <h2>🎛️ Cohort Management Dashboard</h2>
        <p>Set the active group folder for the next incoming block of visitors.</p>
        <form method="post" action="/operator/set_group">
            <input type="text" name="group_name" placeholder="e.g., group_004_matrix_crew" required><br>
            <input type="submit" value="Cycle Activation Group">
        </form>
        <div class="status">Currently active storage path: <br><b style="color:#f43f5e;">/signatures/{{ current_group }}</b></div>
    </div>
</body>
</html>
"""


# --- ROUTES ---

@app.route('/signature')
def signature_page():
    # Dynamic template token replacement without dragging in bulky jinja2 environments
    return HTML_SIGNATURE_PAD.replace("{{ group_id }}", CURRENT_GROUP_ID)

@app.route('/upload_signature', methods=['POST'])
def upload_signature():
    global CURRENT_GROUP_ID
    data = request.json
    
    # 1. Extract base64 image payload and metadata
    image_data = data['image'].split(',')[1]
    raw_visitor_name = data.get('visitor_name', 'anonymous').strip()
    
    # Clean the visitor's name for safe filesystem handling
    safe_visitor_name = "".join([c for c in raw_visitor_name if c.isalnum() or c in ('-', '_')]).rstrip()
    if not safe_visitor_name:
        safe_visitor_name = "visitor"

    # 2. Establish dynamic cohort folder path
    group_dir = os.path.join(SIG_FOLDER, CURRENT_GROUP_ID)
    os.makedirs(group_dir, exist_ok=True)
    
    # Append a timestamp suffix to avoid overwriting files if two people share a name
    time_suffix = datetime.now().strftime("%H%M%S")
    target_filename = f"{safe_visitor_name}_{time_suffix}.png"
    target_filepath = os.path.join(group_dir, target_filename)
    
    # 3. Write out to hardware storage
    with open(target_filepath, "wb") as fh:
        fh.write(base64.b64decode(image_data))
        
    return jsonify({"status": "success", "saved_to": CURRENT_GROUP_ID, "file": target_filename})


# --- OPERATOR DASHBOARD SYSTEMS ---

@app.route('/operator')
def operator_panel():
    return HTML_OPERATOR_PANEL.replace("{{ current_group }}", CURRENT_GROUP_ID)

@app.route('/operator/set_group', methods=['POST'])
def set_active_group():
    global CURRENT_GROUP_ID
    chosen_name = request.form.get('group_name', '').strip()
    
    if chosen_name:
        # Format the name cleanly for directory creation
        safe_group_name = "".join([c for c in chosen_name if c.isalnum() or c in ('-', '_')]).rstrip()
        CURRENT_GROUP_ID = safe_group_name
        
    return redirect('/operator')


# (Keep your original /upload, /gallery, and /media routes down here unchanged)

if __name__ == '__main__':
    # Running debug=False inside local network spaces (like Termux setups) for speed and thread predictability
    app.run(host='0.0.0.0', port=5000, debug=False)