import os
import sys
import base64
import subprocess
import threading
from flask import Flask, request, redirect, url_for, render_template_string, flash, send_from_directory

app = Flask(__name__)
app.secret_key = 'kustos_session_key_2026'

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
GROUPS_DIR = os.path.join(BASE_DIR, 'static', 'visitor_groups')
os.makedirs(GROUPS_DIR, exist_ok=True)

KUSTOS_PASSWORD = "kustosgeslo" 

# =====================================================================
# BACKGROUND TASK RUNNER
# =====================================================================
def run_synthesis_pipeline(group_name):
    """Runs the fuser and sonifier sequentially in the background."""
    print(f"Starting background synthesis for {group_name}...")
    subprocess.run([sys.executable, 'fuse_images.py', group_name])
    #subprocess.run([sys.executable, 'generate_audio.py', group_name])
    print(f"Pipeline complete for {group_name}.")

# =====================================================================
# HTML TEMPLATES (Updated with /media/ endpoint usage)
# =====================================================================

BASE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Visitor Sonification Gallery</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background: #f4f4f9; color: #333; }
        .container { max-width: 900px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        h1, h2, h3 { color: #2c3e50; }
        .btn { padding: 10px 15px; background: #3498db; color: white; border: none; border-radius: 4px; cursor: pointer; text-decoration: none; display: inline-block; }
        .btn:hover { background: #2980b9; }
        .btn-danger { background: #e74c3c; }
        .btn-danger:hover { background: #c0392b; }
        .card-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 20px; margin-top: 20px; }
        .card { border: 1px solid #ddd; border-radius: 8px; padding: 15px; text-align: center; background: #fafafa; }
        .card img { max-width: 100%; border-radius: 4px; margin-bottom: 10px; }
        .flash { padding: 10px; margin-bottom: 20px; border-radius: 4px; background: #ffeaa7; color: #d63031; border: 1px solid #fdcb6e; }
        input[type="text"], input[type="password"] { padding: 10px; border: 1px solid #ccc; border-radius: 4px; width: calc(100% - 22px); margin-bottom: 10px;}
        .auth-box { background: #ecf0f1; padding: 15px; border-radius: 8px; margin-top: 30px; border-left: 5px solid #34495e; }
        canvas { border: 2px dashed #bdc3c7; background: #fff; cursor: crosshair; touch-action: none; width: 100%; height: 200px; }
    </style>
</head>
<body>
    <div class="container">
        {% with messages = get_flashed_messages() %}
          {% if messages %}
            {% for message in messages %}
              <div class="flash">{{ message }}</div>
            {% endfor %}
          {% endif %}
        {% endwith %}
        {% block content %}{% endblock %}
    </div>
    {% block scripts %}{% endblock %}
</body>
</html>
"""

GALLERY_HTML = "{% extends 'base' %}{% block content %}" + """
<h1>Visitor Groups Gallery</h1>
<p>Archive of fused portraits and generative soundscapes.</p>

<div class="card-grid">
    {% for group in groups %}
    <div class="card">
        <h3><a href="{{ url_for('view_group', group_name=group.name) }}">{{ group.name }}</a></h3>
        {% if group.fused_photo %}
            <img src="{{ url_for('serve_media', filename=group.name + '/outputs/fused.jpg') }}" alt="Fused Photo">
        {% else %}
            <div style="height: 150px; background: #eee; display: flex; align-items: center; justify-content: center; margin-bottom: 10px; border-radius: 4px;">Processing / No synthesis yet</div>
        {% endif %}
        
        {% if group.audio %}
            <audio controls style="width: 100%;">
                <source src="{{ url_for('serve_media', filename=group.name + '/outputs/sound.wav') }}" type="audio/wav">
            </audio>
        {% endif %}
    </div>
    {% endfor %}
</div>

<div class="auth-box">
    <h3>Kustos Controls: Create New Visitor Group</h3>
    <form action="{{ url_for('create_group') }}" method="POST">
        <input type="text" name="group_name" placeholder="Enter new group name (e.g., 'May_14_Exhibition')" required>
        <input type="password" name="password" placeholder="Kustos Password" required>
        <button type="submit" class="btn">Create Blank Group</button>
    </form>
</div>
""" + "{% endblock %}"

GROUP_HTML = "{% extends 'base' %}{% block content %}" + """
<a href="{{ url_for('gallery') }}" class="btn" style="margin-bottom: 20px;">&larr; Back to Gallery</a>
<h1>Group: {{ group_name }}</h1>

{% if has_outputs %}
    <div style="text-align: center; margin-bottom: 40px; padding: 20px; background: #2c3e50; border-radius: 8px;">
        <h2 style="color: white;">Synthesis Results</h2>
        <img src="{{ url_for('serve_media', filename=group_name + '/outputs/fused.jpg') }}" style="max-width: 100%; border-radius: 4px; box-shadow: 0 4px 15px rgba(0,0,0,0.3);">
        <br><br>
        <audio controls style="width: 80%;">
            <source src="{{ url_for('serve_media', filename=group_name + '/outputs/sound.wav') }}" type="audio/wav">
        </audio>
    </div>
{% endif %}

<div style="display: flex; gap: 20px; flex-wrap: wrap;">
    <div style="flex: 1; min-width: 300px;">
        <h2>1. Portraits</h2>
        <form action="{{ url_for('upload_portraits', group_name=group_name) }}" method="POST" enctype="multipart/form-data">
            <input type="file" name="portraits" multiple accept="image/*" required>
            <button type="submit" class="btn">Upload Portraits</button>
        </form>
        <div class="card-grid" style="grid-template-columns: repeat(3, 1fr);">
            {% for p in portraits %}
                <img src="{{ url_for('serve_media', filename=group_name + '/portraits/' + p) }}" style="width: 100%; border-radius: 4px;">
            {% endfor %}
        </div>
    </div>

    <div style="flex: 1; min-width: 300px;">
        <h2>2. Signatures</h2>
        <canvas id="sigCanvas"></canvas>
        <br><br>
        <button id="saveSigBtn" class="btn">Save Signature</button>
        <button id="clearSigBtn" class="btn" style="background: #95a5a6;">Clear Canvas</button>
        
        <div class="card-grid" style="grid-template-columns: repeat(3, 1fr); margin-top: 20px;">
            {% for s in signatures %}
                <img src="{{ url_for('serve_media', filename=group_name + '/signatures/' + s) }}" style="width: 100%; border: 1px solid #ddd; background: white;">
            {% endfor %}
        </div>
    </div>
</div>

<hr style="margin: 40px 0;">

<div class="auth-box" style="text-align: center;">
    <h2>3. Finalize & Synthesize</h2>
    <p>This will fuse the portraits and generate audio in the background.</p>
    <form action="{{ url_for('synthesize', group_name=group_name) }}" method="POST">
        <input type="password" name="password" placeholder="Kustos Password required to Synthesize" style="max-width: 300px;" required>
        <br>
        <button type="submit" class="btn btn-danger" style="font-size: 1.2em; padding: 15px 30px;">START SYNTHESIS</button>
    </form>
</div>
""" + "{% endblock %}" + """
{% block scripts %}
<script>
    const canvas = document.getElementById('sigCanvas');
    if(canvas) {
        const ctx = canvas.getContext('2d');
        let isDrawing = false;
        
        canvas.width = canvas.offsetWidth;
        canvas.height = canvas.offsetHeight;
        
        ctx.lineJoin = 'round';
        ctx.lineCap = 'round';
        ctx.lineWidth = 3;
        ctx.strokeStyle = 'black';

        const startDraw = (e) => { isDrawing = true; draw(e); };
        const endDraw = () => { isDrawing = false; ctx.beginPath(); };
        const draw = (e) => {
            if (!isDrawing) return;
            e.preventDefault();
            const rect = canvas.getBoundingClientRect();
            const x = (e.clientX || e.touches[0].clientX) - rect.left;
            const y = (e.clientY || e.touches[0].clientY) - rect.top;
            
            ctx.lineTo(x, y);
            ctx.stroke();
            ctx.beginPath();
            ctx.moveTo(x, y);
        };

        canvas.addEventListener('mousedown', startDraw);
        canvas.addEventListener('mousemove', draw);
        canvas.addEventListener('mouseup', endDraw);
        canvas.addEventListener('mouseout', endDraw);
        
        canvas.addEventListener('touchstart', startDraw, {passive: false});
        canvas.addEventListener('touchmove', draw, {passive: false});
        canvas.addEventListener('touchend', endDraw);

        document.getElementById('clearSigBtn').addEventListener('click', () => {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
        });

        document.getElementById('saveSigBtn').addEventListener('click', () => {
            const dataURL = canvas.toDataURL('image/png');
            fetch("{{ url_for('upload_signature', group_name=group_name) }}", {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ image: dataURL })
            }).then(response => {
                if(response.ok) window.location.reload();
            });
        });
    }
</script>
{% endblock %}
"""


# =====================================================================
# ROUTING & LOGIC
# =====================================================================

@app.route('/media/<path:filename>')
def serve_media(filename):
    """Endpoint for serving raw assets directly from the groups directory."""
    return send_from_directory(GROUPS_DIR, filename)

def get_group_data(group_name):
    base_path = os.path.join(GROUPS_DIR, group_name)
    return {
        "name": group_name,
        "fused_photo": os.path.exists(os.path.join(base_path, 'outputs', 'fused.jpg')),
        "audio": os.path.exists(os.path.join(base_path, 'outputs', 'sound.wav'))
    }

@app.route('/')
def index():
    return redirect(url_for('gallery'))

@app.route('/gallery', methods=['GET'])
def gallery():
    groups = []
    if os.path.exists(GROUPS_DIR):
        for d in os.listdir(GROUPS_DIR):
            if os.path.isdir(os.path.join(GROUPS_DIR, d)):
                groups.append(get_group_data(d))
    
    env = app.jinja_env
    env.globals['base'] = env.from_string(BASE_HTML)
    return render_template_string(GALLERY_HTML, groups=groups)

@app.route('/gallery', methods=['POST'])
def create_group():
    if request.form.get('password') != KUSTOS_PASSWORD:
        flash("Unauthorized: Incorrect password.")
        return redirect(url_for('gallery'))
        
    import re
    raw_name = request.form.get('group_name', 'Unnamed_Group')
    safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', raw_name)
    
    group_path = os.path.join(GROUPS_DIR, safe_name)
    if not os.path.exists(group_path):
        os.makedirs(os.path.join(group_path, 'portraits'))
        os.makedirs(os.path.join(group_path, 'signatures'))
        os.makedirs(os.path.join(group_path, 'outputs'))
        flash(f"Visitor group '{safe_name}' created.")
    else:
        flash("Group already exists.")
        
    return redirect(url_for('gallery'))

@app.route('/group/<group_name>')
def view_group(group_name):
    env = app.jinja_env
    env.globals['base'] = env.from_string(BASE_HTML)
    
    group_path = os.path.join(GROUPS_DIR, group_name)
    if not os.path.exists(group_path):
        return "Group not found", 404
        
    portraits = os.listdir(os.path.join(group_path, 'portraits'))
    signatures = os.listdir(os.path.join(group_path, 'signatures'))
    has_outputs = os.path.exists(os.path.join(group_path, 'outputs', 'fused.jpg'))
    
    return render_template_string(GROUP_HTML, 
                                  group_name=group_name, 
                                  portraits=portraits, 
                                  signatures=signatures,
                                  has_outputs=has_outputs)

@app.route('/group/<group_name>/upload_portraits', methods=['POST'])
def upload_portraits(group_name):
    files = request.files.getlist('portraits')
    target_dir = os.path.join(GROUPS_DIR, group_name, 'portraits')
    for f in files:
        if f.filename != '':
            f.save(os.path.join(target_dir, f.filename))
    return redirect(url_for('view_group', group_name=group_name))

@app.route('/group/<group_name>/upload_signature', methods=['POST'])
def upload_signature(group_name):
    data = request.json.get('image')
    if data:
        header, encoded = data.split(",", 1)
        decoded = base64.b64decode(encoded)
        sig_count = len(os.listdir(os.path.join(GROUPS_DIR, group_name, 'signatures')))
        filename = f"signature_{sig_count + 1}.png"
        filepath = os.path.join(GROUPS_DIR, group_name, 'signatures', filename)
        with open(filepath, "wb") as f:
            f.write(decoded)
        return "OK", 200
    return "Error", 400

@app.route('/group/<group_name>/synthesize', methods=['POST'])
def synthesize(group_name):
    if request.form.get('password') != KUSTOS_PASSWORD:
        flash("Unauthorized: Incorrect password to synthesize.")
        return redirect(url_for('view_group', group_name=group_name))

    group_path = os.path.join(GROUPS_DIR, group_name)
    portrait_dir = os.path.join(group_path, 'portraits')
    portrait_files = os.listdir(portrait_dir)
    
    if not portrait_files:
        flash("Cannot synthesize: No portraits found.")
        return redirect(url_for('view_group', group_name=group_name))

    # Spin up the background thread so the UI responds instantly
    threading.Thread(target=run_synthesis_pipeline, args=(group_name,), daemon=True).start()

    flash("Synthesis started in the background! Refresh the page in a few moments to see results.")
    return redirect(url_for('view_group', group_name=group_name))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)