import os
import io
import re
import glob
import base64
import numpy as np
from flask import Flask, request, redirect, flash, send_from_directory, url_for, render_template, jsonify
from PIL import Image, ImageEnhance
import config

app = Flask(__name__)
app.secret_key = 'kustos_session_key_2026'

# -------------------- PORTRAIT PIPELINE HELPERS -------------------- #
def get_portrait_paths(group):
    portraits_dir = os.path.join(config.GROUPS_DIR, group, 'portraits')
    if not os.path.exists(portraits_dir):
        return "Group does not exist", 404
    portrait_paths = glob.glob(os.path.join(portraits_dir, '*'))
    if not portrait_paths:
        return "No portraits found", 404
    return portrait_paths
        
def find_smallest_portrait_resolution(group):
    portrait_paths = get_portrait_paths(group)
    if isinstance(portrait_paths, tuple):
        return portrait_paths
    min_pixels = float('inf')
    target_size = None
    for p in portrait_paths:
        try:
            with Image.open(p) as img:
                pixels = img.width * img.height
                if pixels < min_pixels:
                    min_pixels = pixels
                    target_size = (img.width, img.height)
        except Exception: 
            continue
    if not target_size:
        return "Error processing images", 500
    return target_size

def fuse_portraits(group):
    portrait_paths = get_portrait_paths(group)   
    target_size = find_smallest_portrait_resolution(group)
    sum_array = np.zeros((target_size[1], target_size[0], 3), dtype=np.float32)
    valid_count = 0
    
    for p in portrait_paths:
        try:
            with Image.open(p) as img:
                resized = img.resize(target_size, Image.Resampling.LANCZOS).convert('RGB')
                sum_array += np.array(resized, dtype=np.float32)
                valid_count += 1
        except Exception: 
            continue

    if valid_count > 0:
        fused_array = sum_array / valid_count
        fused_img = Image.fromarray(np.uint8(fused_array))

    contrast_enhancer = ImageEnhance.Contrast(fused_img)
    color_enhancer = ImageEnhance.Color(fused_img)
    fused_img = contrast_enhancer.enhance(2)
    fused_img = color_enhancer.enhance(1.5)
    return fused_img
    
def check_signatures_exist(group):
    signatures_dir = os.path.join(config.GROUPS_DIR, group, 'signatures')
    if not os.path.exists(signatures_dir):
        return "Group does not exist", 404
    signature_files = glob.glob(os.path.join(signatures_dir, '*'))
    if not signature_files:
        return "No signatures found", 404
    return True
    
def convert_img_to_rgb(image):
    pixels = np.array(image.convert("RGB"), dtype=np.float32) / 255.0
    return pixels.reshape(-1, 3)
    
def convert_rgb_to_luminance(rgb_pixels: np.ndarray, rec: str ='709'):
    if rec == '601': coeffs = (0.299, 0.587, 0.114)
    elif rec == '709': coeffs = (0.2126, 0.7152, 0.0722)
    elif rec == '2020': coeffs = (0.2627, 0.6780, 0.0593)
    else: raise ValueError("Unsupported Rec standard format.")
    return rgb_pixels[:, 0] * coeffs[0] + rgb_pixels[:, 1] * coeffs[1] + rgb_pixels[:, 2] * coeffs[2]
    
def create_signed_portrait_numpy_array(group):
    with Image.open(os.path.join(config.GROUPS_DIR, group, 'fused', 'fused_signature.png')) as fused_signature:
        signature_alpha_channel = np.array(fused_signature.convert('RGBA'))[:,:,3].reshape(-1)
        signature_mask = signature_alpha_channel > 0
        
    with Image.open(os.path.join(config.GROUPS_DIR, group, 'fused', 'fused_portrait.jpg')) as fused_portrait:
        rgb_array = convert_img_to_rgb(fused_portrait)
        masked_rgb_array = rgb_array[signature_mask]
        masked_luma_array = convert_rgb_to_luminance(masked_rgb_array)
        masked_portrait_array = np.column_stack((masked_rgb_array, masked_luma_array))
        np.save(os.path.join(config.GROUPS_DIR, group, 'outputs', 'masked_portrait_array.npy'), masked_portrait_array)
    return None

# -------------------- SERVER HTTP ENDPOINTS -------------------- #
@app.route('/')
def index():
    return redirect(url_for('gallery'))
    
@app.route('/gallery')
def gallery():
    groups = [d for d in os.listdir(config.GROUPS_DIR) if os.path.isdir(os.path.join(config.GROUPS_DIR, d))]
    return render_template('gallery.html', groups=groups)
    
@app.route('/gallery/add_group')
def add_group():
    return render_template('add_group.html')
    
@app.route('/gallery/create_group', methods=['POST'])
def create_group():
    raw_name = request.form.get('group_name', 'Unnamed_Group')
    safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', raw_name)
    group_path = os.path.join(config.GROUPS_DIR, safe_name)
    
    if not os.path.exists(group_path):
        os.makedirs(os.path.join(group_path, 'portraits'))
        os.makedirs(os.path.join(group_path, 'signatures'))
        os.makedirs(os.path.join(group_path, 'outputs'))
        os.makedirs(os.path.join(group_path, 'fused'))
        flash(f"Visitor group '{safe_name}' created.")
    else:
        flash("Group already exists.")
    return redirect(url_for('group', group=safe_name))
    
@app.route('/gallery/<group>')
def group(group):
    target_dir_portraits = os.path.join(config.GROUPS_DIR, group, 'portraits')
    portraits = [f for f in os.listdir(target_dir_portraits) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    target_dir_signatures = os.path.join(config.GROUPS_DIR, group, 'signatures')
    signatures = [f for f in os.listdir(target_dir_signatures) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    return render_template('group.html', group_name=group, portraits=portraits, signatures=signatures)
    
@app.route('/gallery/<group>/upload_portraits', methods=['POST'])
def upload_portraits(group):
    portraits_dir = os.path.join(config.GROUPS_DIR, group, 'portraits')
    existing_files = os.listdir(portraits_dir)
    current_count = len(existing_files)
    files = request.files.getlist('portraits')
    
    for i, file in enumerate(files):
        filename = f"portrait_{current_count + i}.jpg"
        save_path = os.path.join(portraits_dir, filename)
        img = Image.open(file)
        img.thumbnail(config.MAX_PORTRAIT_SIZE, Image.Resampling.LANCZOS)
        img.convert('RGB').save(save_path, "JPEG", quality=90)
    return "Upload successful", 200
    
@app.route('/gallery/<group>/create_fused_portrait', methods=['POST'])
def create_fused_portrait(group):
    fused_img = fuse_portraits(group)
    fused_img_path = os.path.join(config.GROUPS_DIR, group, 'fused', 'fused_portrait.jpg')
    fused_img.save(fused_img_path, quality=90)
    return "Fusion complete", 200

@app.route('/gallery/<group>/upload_signature', methods=['POST'])
def upload_signature(group):
    data = request.json.get('image')
    if not data: return "Canvas is not signed", 400
    header, encoded = data.split(",", 1)
    decoded = base64.b64decode(encoded)
    signature = Image.open(io.BytesIO(decoded)).convert('RGBA')
            
    fused_portrait_path = os.path.join(config.GROUPS_DIR, group, 'fused', 'fused_portrait.jpg')
    if not os.path.exists(fused_portrait_path): return "Fused portrait is missing", 400
    with Image.open(fused_portrait_path) as fused_img:
        target_size = fused_img.size
            
    signature = signature.resize(target_size, Image.Resampling.LANCZOS)
    signatures_path = os.path.join(config.GROUPS_DIR, group, 'signatures')
    num_sig = len(os.listdir(signatures_path))
    filename = f"signature_{num_sig + 1}.png"
    signature.save(os.path.join(signatures_path, filename), "PNG")
    return "Signature uploaded", 200
    
@app.route('/gallery/<group>/create_fused_signature', methods=['POST'])
def run_fuse_signatures(group):
    check = check_signatures_exist(group)
    if check != True: return check
    
    target_size = find_smallest_portrait_resolution(group)
    signature_canvas = Image.new("RGBA", target_size, (0, 0, 0, 0))
    signatures_dir = os.path.join(config.GROUPS_DIR, group, 'signatures')
    signature__paths = [os.path.join(signatures_dir, f) for f in os.listdir(signatures_dir)]
    
    for sig_path in signature__paths:
        with Image.open(sig_path) as sig:
            signature_canvas.paste(sig, (0, 0), sig)

    signature_canvas.save(os.path.join(config.GROUPS_DIR, group, 'fused', 'fused_signature.png'), "PNG")
    create_signed_portrait_numpy_array(group)
    return "Signatures fused", 200
    
@app.route('/manifesto')
def manifesto():
    return render_template('manifesto.html')
    
@app.route('/gallery/<group>/<directory>/<path:filename>')
def serve_media(group, directory, filename):
    target_dir = os.path.join(config.GROUPS_DIR, group, directory)
    return send_from_directory(target_dir, filename)
    
@app.route('/kustos_dashboard')
def kustos_dashboard():
    groups = [d for d in os.listdir(config.GROUPS_DIR) if os.path.isdir(os.path.join(config.GROUPS_DIR, d))]
    return render_template('kustos_dashboard.html', groups=groups)

@app.route('/gallery/<group>/play')
def play_group(group):
    return render_template('play_group.html', group=group)
    
@app.route('/api/play/<group>', methods=['POST'])
def trigger_playback(group):
    if config.KUSTOS_PASS != request.form.get('kustos_pass'):
        return jsonify({"status": "error", "message": "Password is incorrect."}), 404
    
    file_path = os.path.join(config.GROUPS_DIR, group, 'outputs', 'masked_portrait_array.npy')
    if not os.path.exists(file_path):
        return jsonify({"status": "error", "message": f"Installation group '{group}' not found."}), 404

    # Safe write state communication across threads
    with config.state_lock:
        config.shared_state['current_group'] = group
        config.shared_state['play_requested'] = True

    print(f"Kiosk API: Commanded sequencer to play '{group}'")
    return redirect(url_for('group', group=group))