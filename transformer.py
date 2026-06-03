import sys
import os
import numpy as np
from PIL import Image

def transform_image_to_audio(image_path, output_audio_path):
    print(f"🎨 [Transformer] Starting analysis on: {image_path}")
    
    # 1. Open the image and downsample it to keep memory tiny
    img = Image.open(image_path).convert('L') # Convert to grayscale (0-255)
    img = img.resize((128, 128)) # Matrix sizing
    
    pixels = np.array(img, dtype=np.float32) / 255.0 # Normalize 0.0 to 1.0
    flat_pixels = pixels.flatten() # 16,384 structural data points
    
    # 2. Synthesize a raw audio track from the pixel data
    # We will generate a 5-second raw audio buffer based on the image structure
    sample_rate = 44100
    duration = 5.0 
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    
    # Mathematical synthesis: Use pixel blocks to modulate basic carrier waves
    audio_signal = np.zeros_like(t)
    
    # Let's step through a fraction of the pixel matrix to generate a unique drone
    step = len(flat_pixels) // 10
    for i in range(0, len(flat_pixels), step):
        intensity = flat_pixels[i]
        frequency = 100 + (intensity * 400) # Map brightness to 100Hz - 500Hz
        audio_signal += np.sin(2 * np.pi * frequency * t) * intensity

    # Normalize to safe float boundaries
    if np.max(np.abs(audio_signal)) > 0:
        audio_signal = audio_signal / np.max(np.abs(audio_signal))
        
    # 3. Save as a lightning-fast native NumPy binary array
    np.save(output_audio_path, audio_signal.astype(np.float32))
    print(f"💾 [Transformer] Finished! Generated audio asset: {output_audio_path}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python transformer.py <input_img> <output_npy>")
        sys.exit(1)
        
    transform_image_to_audio(sys.argv[1], sys.argv[2])