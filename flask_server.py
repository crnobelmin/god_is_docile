import numpy as np
import sys, os, io, glob, base64, time, re
from flask import Flask, request, redirect, flash, send_from_directory, url_for, render_template
from PIL import Image, ImageEnhance, ImageFilter

# Create flask app
app = Flask(__name__)
app.secret_key = 'kustos_session_key_2026'

# Set directories
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
GROUPS_DIR = os.path.join(BASE_DIR, 'visitor_groups')
os.makedirs(GROUPS_DIR)

# Set a password
KUSTOS_PASS = 'kustosisdocile'

# Set portrait resize target
MAX_PORTRAIT_SIZE = (1000, 1000)


# -------------------- HELPER FUNCTIONS -------------------- #
def check_portraits_exist(group):
    portraits_dir = os.path.join(GROUPS_DIR, group, 'portraits')
    if not os.path.exists(portraits_dir):
        return "Group does not exist", 404
        
    portrait_files = glob.glob(os.path.join(portrait_dir, '*'))
    if not portrait_files:
        return "No portraits found", 404
    
    return True
        
def find_smallest_portrait_resolution(group):
    min_pixels = float('inf')
    target_size = None
    for p in portrait_files:
        try:
            with Image.open(p) as img:
                pixels = img.width * img.height
                if pixels < min_pixels:
                    min_pixels = pixels
                    target_size = (img.width, img.height)
        except Exception: continue

    if not target_size:
        return "Error processing images", 500
        
    return target_size

def fuse_portraits(group):
    check = check_portraits_exist(group)
    if check != True:
        return check
        
    target_size = find_smallest_portrait_resolution(group)

    sum_array = np.zeros((target_size[1], target_size[0], 3), dtype=np.float32)
    valid_count = 0
    
    for p in portrait_files:
        try:
            with Image.open(p) as img:
                resized = img.resize(target_size, Image.Resampling.LANCZOS).convert('RGB')
                sum_array += np.array(resized, dtype=np.float32)
                valid_count += 1
        except Exception: continue

    if valid_count > 0:
        fused_array = sum_array / valid_count
        fused_img = Image.fromarray(np.uint8(fused_array))

    return fused_img
    
def check_signatures_exist(group):
    signatures_dir = os.path.join(GROUPS_DIR, group, 'signatures')
    if not os.path.exists(signatures_dir):
        return "Group does not exist", 404
        
    signature_files = glob.glob(os.path.join(signatures_dir, '*'))
    if not signature_files:
        return "No signatures found", 404
    
    return True
    
def create_signed_portrait_numpy_array(group):
    return None

# -------------------- HOME PAGE -------------------- #
@app.route('/')
def index():
    return redirect(url_for('gallery'))
    
# -------------------- GALLERY -------------------- #
@app.route('/gallery')
def gallery():
    groups = [d for d in os.listdir(GROUPS_DIR) if os.path.isdir(os.path.join(GROUPS_DIR, d))]
    return render_template('gallery.html', groups=groups)
    
@app.route('/gallery/add_group')
def add_visitor():
    return render_template('add_group.html')
    
@app.route('/gallery/create_group', methods=['POST'])
def create_group():
    raw_name = request.form.get('group_name', 'Unnamed_Group')
    safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', raw_name)
    group_path = os.path.join(GROUPS_DIR, safe_name)
    
    if not os.path.exists(group_path):
        os.makedirs(os.path.join(group_path, 'portraits'))
        os.makedirs(os.path.join(group_path, 'signatures'))
        os.makedirs(os.path.join(group_path, 'audio'))
        os.makedirs(os.path.join(group_path, 'fused'))
        flash(f"Visitor group '{safe_name}' created.")
    else:
        flash("Group already exists.")

    return redirect(url_for('group', group=safe_name))
    
# -------------------- GROUP -------------------- #
@app.route('/gallery/<group>')
def group(group):
    target_dir_portraits = os.path.join(GROUPS_DIR, group, 'portraits')
    portraits = [f for f in os.listdir(target_dir_portraits) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        
    target_dir_signatures = os.path.join(GROUPS_DIR, group, 'signatures')
    signatures = [f for f in os.listdir(target_dir_signatures) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    
    return render_template(
        'group.html', 
        group_name=group, 
        portraits=portraits, 
        signatures=signatures,
    )
    
@app.route('/gallery/<group>/upload_portraits', methods=['POST'])
def upload_portraits(group):
    portraits_dir = os.path.join(GROUPS_DIR, group, 'portraits')
    existing_files = [f for f in os.listdir(portraits_dir)]
    current_count = len(existing_files)
    
    files = request.files.getlist('portraits')
    
    for i, file in enumerate(files):
        filename = f"portrait_{current_count + i}.jpg"
        save_path = os.path.join(portraits_dir, filename)
        
        img = Image.open(file)
        img.thumbnail(MAX_PORTRAIT_SIZE, Image.Resampling.LANCZOS)
        img.convert('RGB').save(save_path, "JPEG", quality=90)
            
    return "Upload successful", 200
    
@app.route('/gallery/<group>/create_fused_portrait', methods=['POST'])
def run_fuse_portraits(group):
    fused_img = fuse_portraits(group)
    fused_img_path = os.path.join(GROUPS_DIR, group, 'fused', 'fused_portrait.jpg')
    fused_img.save(fused_img_path, quality=90)
    return "Fusion complete", 200

@app.route('/gallery/<group>/upload_signature', methods=['POST'])
def upload_signature(group):
    data = request.json.get('image')
    if not data:
        return "Canvas is not signed", 400

    header, encoded = data.split(",", 1)
    decoded = base64.b64decode(encoded)
    signature = Image.open(io.BytesIO(decoded)).convert('RGBA')
            
    fused_portrait_path = os.path.join(GROUPS_DIR, group, 'fused', 'fused_portrait.jpg')
    if not os.path.exists(fused_portrait_path):
        return "Fused portrait is missing", 400
        
    with Image.open(fused_path) as fused_img:
        target_size = fused_img.size
            
    signature = signature.resize(target_size, Image.Resampling.LANCZOS)

    signatures_path = os.path.join(GROUPS_DIR, group, 'signatures')
    num_sig = len(os.listdir(signatures_path))
    filename = f"signature_{num_sig + 1}.png"
    filepath = os.path.join(signatures_path, filename)
    image.save(filepath, "PNG")
        
    return "Signature uploaded", 200
    
@app.route('/gallery/<group>/crete_fused_signature', methods=['POST'])
def run_fuse_signatures(group):
    check = check_signatures_exist(group)
    if check != True
        return check
    
    target_size = find_smallest_portrait_resolution(group)
    signature_canvas = Image.new("RGBA", target_size, (0, 0, 0, 0))

    signatures_dir = os.path.join(GROUPS_DIR, group, 'signatures')
    signature__paths = [os.path.join(signatures_dir, f) for f in os.listdir(signatures_dir)]
    for sig_path in signature__paths:
        with Image.open(sig_path) as sig:
            mask.paste(sig, (0, 0), sig)

    signature_canvas.save(os.path.join(GROUPS_DIR, group, 'fused', 'fused_signatures.png'), "PNG")
    
    return "Signatures fused", 200
    
@app.route('/manifesto')
def manifesto():
    return render_template('manifesto.html')
    
@app.route('/gallery/<group>/<directory>/<path:filename>')
def serve_media(group, directory, filename):
    target_dir = os.path.join(GROUPS_DIR, group, directory)
    return send_from_directory(target_dir, filename)
    
# -------------------- MANAGEMENT DASHBOARD -------------------- #
@app.route('/kustos_dashboard')
def kustos_dashboard():
    groups = [d for d in os.listdir(GROUPS_DIR) if os.path.isdir(os.path.join(GROUPS_DIR, d))]
    return render_template('kustos_dashboard.html', groups=groups)
    
@app.route('/run_installation')
def run_installation(group):
  
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)