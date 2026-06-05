import os
import glob
import base64
import numpy as np
from PIL import Image
from scipy.io import wavfile
from flask import Flask, request, redirect, url_for, render_template_string, flash

app = Flask(__name__)
app.secret_key = 'kustos_session_key_2026' # Used for flashing messages

# Core Directories
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
GROUPS_DIR = os.path.join(BASE_DIR, 'static', 'visitor_groups')
os.makedirs(GROUPS_DIR, exist_ok=True)

# Security
KUSTOS_PASSWORD = "kustosgeslo" 

# =====================================================================
# HTML TEMPLATES
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
            <img src="{{ url_for('static', filename='visitor_groups/' + group.name + '/outputs/fused.jpg') }}" alt="Fused Photo">
        {% else %}
            <div style="height: 150px; background: #eee; display: flex; align-items: center; justify-content: center; margin-bottom: 10px; border-radius: 4px;">No synthesis yet</div>
        {% endif %}
        
        {% if group.audio %}
            <audio controls style="width: 100%;">
                <source src="{{ url_for('static', filename='visitor_groups/' + group.name + '/outputs/sound.wav') }}" type="audio/wav">
                Your browser does not support the audio element.
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
        <img src="{{ url_for('static', filename='visitor_groups/' + group_name + '/outputs/fused.jpg') }}" style="max-width: 100%; border-radius: 4px; box-shadow: 0 4px 15px rgba(0,0,0,0.3);">
        <br><br>
        <audio controls style="width: 80%;">
            <source src="{{ url_for('static', filename='visitor_groups/' + group_name + '/outputs/sound.wav') }}" type="audio/wav">
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
                <img src="{{ url_for('static', filename='visitor_groups/' + group_name + '/portraits/' + p) }}" style="width: 100%; border-radius: 4px;">
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
                <img src="{{ url_for('static', filename='visitor_groups/' + group_name + '/signatures/' + s) }}" style="width: 100%; border: 1px solid #ddd; background: white;">
            {% endfor %}
        </div>
    </div>
</div>

<hr style="margin: 40px 0;">

<div class="auth-box" style="text-align: center;">
    <h2>3. Finalize & Synthesize</h2>
    <p>This process will fuse the portraits, apply the signatures as a modulation mask, and generate the generative `.wav` and `.npy` files.</p>
    <form action="{{ url_for('synthesize', group_name=group_name) }}" method="POST">
        <input type="password" name="password" placeholder="Kustos Password required to Synthesize" style="max-width: 300px;" required>
        <br>
        <button type="submit" class="btn btn-danger" style="font-size: 1.2em; padding: 15px 30px;">SYNTHESIZE</button>
    </form>
</div>
""" + "{% endblock %}" + """
{% block scripts %}
<script>
    // Canvas Logic for Signatures
    const canvas = document.getElementById('sigCanvas');
    if(canvas) {
        const ctx = canvas.getContext('2d');
        let isDrawing = false;
        
        // Resize canvas to physical dimensions
        canvas.width = canvas.offsetWidth;
        canvas.height = canvas.offsetHeight;
        
        // Start with a clean transparent background
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
    
    return render_template_string(
        "{% extends 'base' %}{% block content %}...{% endblock %}", 
        groups=groups, 
        _template=GALLERY_HTML, base=BASE_HTML
    ).replace('{% extends \'base\' %}', '{% extends base_template %}').replace('base_template', '"{}"'.format('base')) # Quick engine trick
    
    # Proper rendering setup
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
        # Strip header from base64 string
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
    sig_dir = os.path.join(group_path, 'signatures')
    out_dir = os.path.join(group_path, 'outputs')
    
    portrait_files = glob.glob(os.path.join(portrait_dir, '*'))
    sig_files = glob.glob(os.path.join(sig_dir, '*'))
    
    if not portrait_files:
        flash("Cannot synthesize: No portraits found.")
        return redirect(url_for('view_group', group_name=group_name))

    # --- 1. PORTRAIT FUSION ---
    # Find smallest resolution (MP)
    min_pixels = float('inf')
    target_size = None
    
    for p in portrait_files:
        try:
            with Image.open(p) as img:
                pixels = img.width * img.height
                if pixels < min_pixels:
                    min_pixels = pixels
                    target_size = (img.width, img.height)
        except Exception:
            pass # Ignore non-image files

    # Average the arrays
    fused_array = np.zeros((target_size[1], target_size[0], 3), dtype=np.float32)
    valid_count = 0
    for p in portrait_files:
        try:
            with Image.open(p) as img:
                resized = img.resize(target_size, Image.Resampling.LANCZOS).convert('RGB')
                fused_array += np.array(resized, dtype=np.float32)
                valid_count += 1
        except Exception:
            pass
            
    if valid_count > 0:
        fused_array /= valid_count
        
    fused_img = Image.fromarray(np.uint8(fused_array))
    fused_img.save(os.path.join(out_dir, 'fused.jpg'), quality=90)

    # --- 2. SIGNATURE OVERLAY & MASKING ---
    mask = np.zeros((target_size[1], target_size[0]), dtype=np.float32)
    
    for s in sig_files:
        try:
            with Image.open(s) as img:
                # Canvas exports as PNG with transparent background. 
                # We resize, ensure RGBA, and use the Alpha channel as the mask.
                resized = img.resize(target_size, Image.Resampling.LANCZOS).convert('RGBA')
                alpha = np.array(resized)[:, :, 3].astype(np.float32) / 255.0
                mask = np.maximum(mask, alpha) # Additive overlay
        except Exception:
            pass

    # --- 3. SONIFICATION ---
    # Convert fused photo to grayscale to map intensity to audio amplitude
    gray_fused = fused_img.convert('L')
    gray_array = np.array(gray_fused, dtype=np.float32)

    # Apply the combined signature mask filter
    # If no signatures exist, the mask is all zeros. We'll default to 1.0 (pass all) if empty.
    if not sig_files:
        mask = np.ones_like(gray_array)
        
    filtered_array = gray_array * mask

    # Flatten the filtered 2D array into a 1D audio sequence
    audio_1d = filtered_array.flatten()

    # Center the waveform (remove DC offset) and normalize to -1.0 to 1.0
    if len(audio_1d) > 0:
        audio_1d = audio_1d - np.mean(audio_1d)
        max_val = np.max(np.abs(audio_1d))
        if max_val > 0:
            audio_norm = audio_1d / max_val
        else:
            audio_norm = audio_1d
    else:
        audio_norm = np.zeros(44100) # 1 sec silence fallback

    # Save live modulation Numpy array
    np.save(os.path.join(out_dir, 'sound.npy'), audio_norm)

    # Convert to 16-bit PCM for WAV playback
    audio_pcm = np.int16(audio_norm * 32767)
    sample_rate = 44100  # Standard CD-quality sample rate
    wavfile.write(os.path.join(out_dir, 'sound.wav'), sample_rate, audio_pcm)

    flash("Synthesis complete! Fused portrait and audio generated.")
    return redirect(url_for('view_group', group_name=group_name))

if __name__ == '__main__':
    # Run the local server
    app.run(debug=True, host='0.0.0.0', port=5000)