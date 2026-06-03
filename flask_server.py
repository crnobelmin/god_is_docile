import os
from flask import Flask, request, redirect, render_code = """"""
# Using a string for the HTML template to keep it single-file

app = Flask(__name__)

# Point this directly to where your audio engine looks for images
UPLOAD_FOLDER = os.path.expanduser('~/multiframe_audio/audio_files')
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Simple HTML Interface served to anyone who visits the IP
HTML_INTERFACE = """
<!doctype html>
<html lang="en">
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Matrix Audio Upload</title>
    <style>
        body { font-family: sans-serif; background: #121212; color: #e0e0e0; text-align: center; padding: 20px; }
        .box { border: 2px dashed #333; padding: 40px; border-radius: 8px; background: #1a1a1a; max-width: 400px; margin: 40px auto; }
        input[type=file] { margin: 20px 0; color: #aaa; }
        input[type=submit] { background: #007bff; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; font-size: 16px; }
        input[type=submit]:hover { background: #0056b3; }
    </style>
</head>
<body>
    <h1>🌌 Interactive Audio Matrix</h1>
    <p>Upload a JPEG to feed the sound modulation engine</p>
    <div class="box">
        <form method="post" enctype="multipart/form-data" action="/upload">
            <input type="file" name="file" accept="image/*"><br>
            <input type="submit" value="Upload & Transform">
        </form>
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    return HTML_INTERFACE

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return "No file selected", 400
    file = request.files['file']
    if file.filename == '':
        return "No file selected", 400
        
    if file:
        # Standardize filename so the audio engine can find it predictably
        # e.g., saving it as input_image.jpg
        filename = "input_image.jpg" 
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        return """
        <body style="background:#121212;color:#e0e0e0;text-align:center;font-family:sans-serif;padding-top:50px;">
            <h2>✅ Image Received!</h2>
            <p>The audio matrix is modulating the new data stream.</p>
            <a href="/" style="color:#007bff;">Upload another</a>
        </body>
        """
    return "Invalid file type", 400

if __name__ == '__main__':
    # Host on 0.0.0.0 to broadcast to the entire local Wi-Fi network
    # Port 5000 is default for Flask, keeping 5001/6000 clear for audio data
    app.run(host='0.0.0.0', port=5000, debug=False)