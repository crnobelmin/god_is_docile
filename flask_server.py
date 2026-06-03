import os
from flask import Flask, request, redirect, send_from_directory

app = Flask(__name__)

# System paths matching your local Termux repository layout
UPLOAD_FOLDER = os.path.expanduser('~/godisdocile/god_is_docile/audio_files')
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_allowed_images():
    """Helper to fetch only valid image files from the storage folder"""
    try:
        return [f for f in os.listdir(UPLOAD_FOLDER) 
                if os.path.isfile(os.path.join(UPLOAD_FOLDER, f)) 
                and f.split('.')[-1].lower() in ALLOWED_EXTENSIONS]
    except Exception:
        return []

# --- HTML TEMPLATES ---

HTML_UPLOAD_INTERFACE = """
<!doctype html>
<html lang="en">
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Matrix Audio Upload</title>
    <style>
        body { font-family: sans-serif; background: #121212; color: #e0e0e0; text-align: center; padding: 20px; }
        .box { border: 2px dashed #333; padding: 40px; border-radius: 8px; background: #1a1a1a; max-width: 400px; margin: 40px auto; }
        input[type=file] { margin: 20px 0; color: #aaa; width: 100%; }
        input[type=text] { 
            width: 90%; padding: 10px; margin-bottom: 20px; 
            background: #2a2a2a; border: 1px solid #444; color: white; 
            border-radius: 4px; font-size: 14px;
        }
        input[type=submit] { background: #007bff; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; font-size: 16px; width: 100%; }
        input[type=submit]:hover { background: #0056b3; }
        .nav-link { display: inline-block; margin-top: 20px; color: #007bff; text-decoration: none; }
    </style>
</head>
<body>
    <h1>🌌 Interactive Audio Matrix</h1>
    <p>Upload a JPEG and name it to feed the sound modulation engine</p>
    <div class="box">
        <form method="post" enctype="multipart/form-data" action="/upload">
            <input type="text" name="custom_name" placeholder="Desired Filename (e.g., track_one)" required><br>
            <input type="file" name="file" accept="image/*" required><br>
            <input type="submit" value="Upload & Transform">
        </form>
        <a class="nav-link" href="/gallery">🖼️ View Uploaded Matrix Images</a>
    </div>
</body>
</html>
"""

# --- ROUTES ---

@app.route('/')
def index():
    return HTML_UPLOAD_INTERFACE

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return "No file part", 400
    file = request.files['file']
    custom_name = request.form.get('custom_name', '').strip()
    
    if file.filename == '' or not custom_name:
        return "Missing file or filename configuration", 400
        
    # Extract extension (e.g., .jpg)
    file_ext = file.filename.split('.')[-1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        return "Invalid file type. Please use JPG, JPEG, or PNG.", 400
        
    if file:
        # Sanitize name to prevent path injection attacks (strips spaces/weird characters)
        safe_base = "".join([c for c in custom_name if c.isalpha() or c.isdigit() or c in ('-', '_')]).rstrip()
        if not safe_base:
            safe_base = "uploaded_matrix_asset"
            
        filename = f"{safe_base}.{file_ext}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        return f"""
        <body style="background:#121212;color:#e0e0e0;text-align:center;font-family:sans-serif;padding-top:50px;">
            <h2>✅ Matrix Asset Saved as: {filename}</h2>
            <p>The matrix engine is tracking this asset identity.</p>
            <a href="/" style="color:#007bff; text-decoration:none; margin-right: 20px;">Upload another</a>
            <a href="/gallery" style="color:#28a745; text-decoration:none;">Go to Gallery ➡️</a>
        </body>
        """

@app.route('/gallery')
def gallery():
    images = get_allowed_images()
    
    # Build dynamic image card rows
    image_cards = ""
    for img in images:
        image_cards += f"""
        <div class="card">
            <img src="/media/{img}" alt="{img}">
            <div class="card-info">{img}</div>
        </div>
        """
        
    if not images:
        image_cards = "<p style='color:#888;'>No files processed inside the matrix directory yet.</p>"

    html_gallery = f"""
    <!doctype html>
    <html lang="en">
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Matrix Asset Gallery</title>
        <style>
            body {{ font-family: sans-serif; background: #121212; color: #e0e0e0; padding: 20px; text-align: center; }}
            .grid {{ display: flex; flex-wrap: wrap; justify-content: center; gap: 20px; margin-top: 30px; }}
            .card {{ background: #1a1a1a; border: 1px solid #333; border-radius: 8px; padding: 10px; width: 200px; text-align: center; }}
            .card img {{ max-width: 100%; height: 150px; object-fit: cover; border-radius: 4px; background: #222; }}
            .card-info {{ margin-top: 10px; font-size: 13px; color: #aaa; word-break: break-all; }}
            .back-btn {{ display: inline-block; margin-top: 30px; background: #333; color: white; padding: 10px 20px; border-radius: 4px; text-decoration: none; }}
            .back-btn:hover {{ background: #444; }}
        </style>
    </head>
    <body>
        <h1>🖼️ Processed Matrix Assets</h1>
        <p>Active image layers available for real-time mathematical sound generation</p>
        <div class="grid">
            {image_cards}
        </div>
        <br>
        <a class="back-btn" href="/">⬅️ Back to Upload Interface</a>
    </body>
    </html>
    """
    return html_gallery

# Route to safely stream files out of the hidden Termux system directory to user browsers
@app.route('/media/<filename>')
def serve_media(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)