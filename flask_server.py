import numpy as np
import sys, os, io, glob, base64, time, re
from flask import Flask, request, redirect, flash, send_from_directory, url_for, render_template
from PIL import Image, ImageEnhance, ImageFilter

# Create a flask app
app = Flask(__name__)
app.secret_key = 'kustos_session_key_2026'

# Set the directory where this script is running as the base dir
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
GROUPS_DIR = os.path.join(BASE_DIR, 'visitor_groups')

# Set a password to only give the kustos admin rights
KUSTOS_PASS = 'kustosisdocile'

# -------------------- HOME PAGE -------------------- #
@app.route('/')
def index():
    return redirect(url_for('manifesto'))
    
@app.route('/manifesto')
def manifesto():
    return render_template('manifesto.html')
    
# -------------------- GALLERY -------------------- #
@app.route('/gallery')
def gallery():
    # Pass the list of group names directly to Jinja2
    groups = [d for d in os.listdir(GROUPS_DIR) if os.path.isdir(os.path.join(GROUPS_DIR, d))]
    return render_template('gallery.html', groups=groups)
    
@app.route('/gallery/add_visitor')
def add_visitor():
    return render_template('add_visitor.html')
    
@app.route('/gallery/create_group', methods=['POST'])
def create_group():
    if request.form.get('password') != KUSTOS_PASS:
        flash("Unauthorized: Incorrect password.")
        return redirect(url_for('gallery'))
        
    raw_name = request.form.get('group_name', 'Unnamed_Group')
    safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', raw_name)
    
    group_path = os.path.join(GROUPS_DIR, safe_name)
    if not os.path.exists(group_path):
        os.makedirs(os.path.join(group_path, 'portraits'))
        os.makedirs(os.path.join(group_path, 'signatures'))
        os.makedirs(os.path.join(group_path, 'outputs'))
        os.makedirs(os.path.join(group_path, 'fused'))
        flash(f"Visitor group '{safe_name}' created.")
    else:
        flash("Group already exists.")
        
    return redirect(url_for('group', group_name=safe_name))
    
# -------------------- GROUP -------------------- #
@app.route('/gallery/<group_name>')
def group(group_name):
    # Get all portrait files
    target_dir_portraits = os.path.join(GROUPS_DIR, group_name, 'portraits')
    portraits = [f for f in os.listdir(target_dir_portraits) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        
    # Get all signature files
    target_dir_signatures = os.path.join(GROUPS_DIR, group_name, 'signatures')
    signatures = [f for f in os.listdir(target_dir_signatures) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    
    num_sigs = len(signatures)
        
    # Pass lists directly to the template
    return render_template(
        'group.html', 
        group_name=group_name, 
        portraits=portraits, 
        signatures=signatures,
        num_sigs=num_sigs
    )
    
@app.route('/gallery/<group_name>/upload_portraits', methods=['POST'])
def upload_portraits(group_name):
    files = request.files.getlist('portraits')
    upload_dir = os.path.join(GROUPS_DIR, group_name, 'portraits')
    os.makedirs(upload_dir, exist_ok=True)
    
    MAX_SIZE = (1000, 1000)
    
    # Get the current count to start numbering correctly
    existing_files = [f for f in os.listdir(upload_dir) if f.startswith("portrait_")]
    current_count = len(existing_files)
    
    for i, file in enumerate(files):
        if file and file.filename != '':
            # 1. Create numbered filename
            filename = f"portrait_{current_count + i + 1}.jpg"
            save_path = os.path.join(upload_dir, filename)
            
            # 2. Open, resize, and save
            img = Image.open(file)
            img.thumbnail(MAX_SIZE, Image.Resampling.LANCZOS)
            img.convert('RGB').save(save_path, "JPEG", quality=85)
            
    return "Upload successful", 200
    
@app.route('/gallery/<group_name>/fuse_portraits', methods=['POST'])
def run_fuse_portraits(group_name):
    group_path = os.path.join(GROUPS_DIR, group_name)
    portrait_dir = os.path.join(group_path, 'portraits')
    fused_dir = os.path.join(group_path, 'fused')
    
    # Ensure the 'fused' directory exists
    os.makedirs(fused_dir, exist_ok=True)
    
    portrait_files = glob.glob(os.path.join(portrait_dir, '*'))
    if not portrait_files:
        return "No portraits found", 404

    # Find smallest resolution
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

    if not target_size: return "Error processing images", 500

    # Create fused image
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
        
        # Add saturation
        fused_img = ImageEnhance.Color(fused_img).enhance(1.3)
        fused_img = ImageEnhance.Contrast(fused_img).enhance(1.5)
        fused_img = ImageEnhance.Brightness(fused_img).enhance(1.2)
        
        
        # Save as fused.jpg inside the 'fused' folder
        fused_img.save(os.path.join(fused_dir, 'fused.jpg'), quality=90)
        return "Fusion complete", 200
    
    return "No valid images to fuse", 500
    


# @app.route('/gallery/<group_name>/upload_signature', methods=['POST'])
# def upload_signature(group_name):
    # data = request.json.get('image')
    # if data:
        # header, encoded = data.split(",", 1)
        # decoded = base64.b64decode(encoded)
        
        # num_sig = len(os.listdir(os.path.join(GROUPS_DIR, group_name, 'signatures')))
        # filename = f"signature_{num_sig + 1}.png"
        # filepath = os.path.join(GROUPS_DIR, group_name, 'signatures', filename)
        
        # print(f'Processing, cropping, resizing, and centering image for {filepath}')
        
        # # 1. Load the binary data
        # image = Image.open(io.BytesIO(decoded)).convert('RGBA')
            
        # # 2. Crop to the exact boundaries of the drawn lines
        # bbox = image.getbbox()
        # if bbox:
            # image = image.crop(bbox)
            
        # # 3. Find the fused photo to get target dimensions
        # fused_path = os.path.join(GROUPS_DIR, group_name, 'fused', 'fused.jpg')
        
        # if os.path.exists(fused_path):
            # with Image.open(fused_path) as fused_img:
                # target_w, target_h = fused_img.size
                
            # safe_w, = target_w * 0.80, 
            # safe_h = target_h * 0.80
            # # 4. Get the cropped signature dimensions and calculate the scale factor
            # sig_w, sig_h = image.size
            # scale = min(safe_w / sig_w, safe_h / sig_h)
            # new_w = int(sig_w * scale)
            # new_h = int(sig_h * scale)
            
            # # 5. Resize the cropped signature to its new massive size
            # resized_image = image.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
            # # Softens the harsh, jagged edges of the digital ink
            # resized_image = resized_image.filter(ImageFilter.SMOOTH_MORE)
            
            # # 6. Create a new, fully transparent canvas exactly the size of the fused photo
            # canvas = Image.new('RGBA', (target_w, target_h), (0, 0, 0, 0))
            
            # # 7. Calculate the (X, Y) coordinates to paste the *resized* signature in the center
            # paste_x = (target_w - new_w) // 2
            # paste_y = (target_h - new_h) // 2
            
            # # 8. Paste the resized signature onto the center of the transparent canvas
            # canvas.paste(resized_image, (paste_x, paste_y), resized_image)
            
        # # 10. Save to disk
        # canvas.save(filepath, "PNG")
        
        # return "OK", 200
        
    # return "Error", 400
    
    
@app.route('/gallery/<group_name>/upload_signature', methods=['POST'])
def upload_signature(group_name):
    data = request.json.get('image')
    if data:
        header, encoded = data.split(",", 1)
        decoded = base64.b64decode(encoded)
        
        num_sig = len(os.listdir(os.path.join(GROUPS_DIR, group_name, 'signatures')))
        filename = f"signature_{num_sig + 1}.png"
        filepath = os.path.join(GROUPS_DIR, group_name, 'signatures', filename)
        
        print(f'Processing and mapping signature for {filepath}')
        
        # 1. Load the binary data from the frontend canvas
        image = Image.open(io.BytesIO(decoded)).convert('RGBA')
            
        # 2. Find the fused photo to get the TRUE target dimensions
        fused_path = os.path.join(GROUPS_DIR, group_name, 'fused', 'fused.jpg')
        
        if os.path.exists(fused_path):
            with Image.open(fused_path) as fused_img:
                target_w, target_h = fused_img.size
            
            # 3. Resize the whole signature layer to match the fused photo's resolution
            # Because the aspect ratios match exactly, this perfectly maps the ink 
            # to where the user drew it, just at the correct high resolution.
            image = image.resize((target_w, target_h), Image.Resampling.LANCZOS)
            
            # 4. (Optional) Soften the harsh, jagged edges of the digital ink
            image = image.filter(ImageFilter.SMOOTH_MORE)
            
        # 5. Save directly to disk
        image.save(filepath, "PNG")
        
        return "OK", 200
        
    return "Error", 400
    
    
    
@app.route('/gallery/<group_name>/fuse_signatures', methods=['POST'])
def run_fuse_signatures(group_name):
    # Path to the signatures folder for this group
    sig_dir = os.path.join(GROUPS_DIR, group_name, 'signatures')
    
    if not os.path.exists(sig_dir):
        return "Signatures directory not found", 404

    # Load all unique signature filenames
    signatures = [f for f in os.listdir(sig_dir) if f.startswith("signature_") and f.endswith(".png")]
    
    if not signatures:
        return "No signatures to fuse", 200

    # Determine dimensions from the first signature
    first_sig_path = os.path.join(sig_dir, signatures[0])
    with Image.open(first_sig_path) as first_sig:
        width, height = first_sig.size

    # Create a new, fully transparent image
    mask = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    # Paste each signature onto the transparent mask
    for sig_name in signatures:
        sig_path = os.path.join(sig_dir, sig_name)
        with Image.open(sig_path) as sig:
            # Pasting with itself as the third argument uses its alpha channel
            mask.paste(sig, (0, 0), sig)

    # Save the combined mask (overwriting if it exists)
    save_path = os.path.join(sig_dir, 'fused_signatures.png')
    mask.save(save_path, "PNG")
    
    print(f"DEBUG: Successfully fused {len(signatures)} signatures for {group_name}")
    return "Fusing complete", 200
    
@app.route('/gallery/<group>/<directory>/<path:filename>')
def serve_media(group, directory, filename):
    target_dir = os.path.join(GROUPS_DIR, group, directory)
    return send_from_directory(target_dir, filename)
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)