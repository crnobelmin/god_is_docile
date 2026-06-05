import sys
import os
import numpy as np
from PIL import Image


# -------------------- CONVERT IMAGE TO RGB VALUES --------------------
def image_to_rgb(image):
    # Source: https://www.niwa.nu/2013/05/math-behind-colorspace-conversions-rgb-hsl/
    
    # Extract an array of pixels and normalize it (RGB values go from 0 to 255)
    pixels = np.array(image.convert("RGB"), dtype=np.float32) / 255.0
   
    # Reshape pixels from height x width to 3 columns
    pixels = pixels.reshape(-1, 3)
        
    return pixels
    
# -------------------- CONVERT RGB VALUES TO ESTIMATION OF LINEAR PHYSICAL LIGHT --------------------
def rgb_to_physical_light(rgb_pixels: np.ndarray) -> np.ndarray:
    """
    Converts normalized sRGB data (0.0 - 1.0) into linear physical light by completely undoing the standard sRGB gamma companding curve.
    
    Args:
        rgb_pixels: Nx3 NumPy array of normalized float32 color channels.
        
    Returns:
        Nx3 NumPy array of linear physical light values (0.0 - 1.0).
    """
    # Standard official sRGB inverse piecewise transformation
    # 1. Very dark values use a strict linear divider to prevent infinite slope noise
    # 2. Everything else uses the official sRGB power-curve calculation
    physical_pixels = np.where(
        rgb_pixels <= 0.04045,
        rgb_pixels / 12.92,
        ((rgb_pixels + 0.055) / 1.055) ** 2.4
    )
    
    return physical_pixels
    
# -------------------- PIXEL SPACE CONVERSIONS --------------------
def rgb_to_luminance(rgb_pixels: np.ndarray, rec: str ='709'):
    """
    Calculates luminance from RGB values using the specified Rec. standard.
    
    Args:
        rgb_pixels: Nx3 array of normalized RGB values.
        rec: '601', '709', or '2020' — selects the luminance coefficients.
    
    Returns:
        1D array of luminance values (normalized 0–1).
    """
    # Define coefficients based on Rec standard
    rec = str(rec)
    if rec == '601':
        coeffs = (0.299, 0.587, 0.114)
    elif rec == '709':
        coeffs = (0.2126, 0.7152, 0.0722)
    elif rec == '2020':
        coeffs = (0.2627, 0.6780, 0.0593)
    else:
        raise ValueError("Unsupported Rec format. Use '601', '709', or '2020'.")

    r_coef, g_coef, b_coef = coeffs

    # Calculate luminance
    luminance = (
        rgb_pixels[:, 0] * r_coef +
        rgb_pixels[:, 1] * g_coef +
        rgb_pixels[:, 2] * b_coef
    )

    return luminance
    
    
    
# -------------------- TRANSFORMER FUNCTION TO TRANSLATE LIGHT INTENSITY TO SYNTHETIC SOUNDWAVE --------------------
def translate_intensity_to_synth_channel(
    intensities: np.ndarray, 
    duration: float = 60.0, 
    sample_rate: int = 44100,
    f_min: float = 110.0,  # One octave lower baseline (A2)
    f_max: float = 880.0   # Upper frequency bound (A5)
) -> np.ndarray:
    """
    Translates an array of spatial intensities into a single time-continuous
    audio waveform with smooth frequency glides, replacing pyo's Linseg.
    """
    total_samples = int(sample_rate * duration)
    
    # 1. Map physical light intensities (0.0 - 1.0) directly to target frequencies
    # This replaces your old hue-to-hz calculations with light-energy-to-hz
    pixel_frequencies = f_min + (intensities * (f_max - f_min))
    
    # 2. Recreate Linseg behavior: Stretch our N pixel points across total_samples
    # This smoothly interpolates between every single frequency step
    xp = np.linspace(0, duration, len(pixel_frequencies))
    x_new = np.linspace(0, duration, total_samples)
    interpolated_frequencies = np.interp(x_new, xp, pixel_frequencies)
    
    # 3. THE PHASE ACCUMULATOR
    # Instead of multiplying, we sum up the steps to get continuous phase angles.
    # We divide by sample_rate to scale the step delta per audio frame.
    phase_delta = (2 * np.pi * interpolated_frequencies) / sample_rate
    phase = np.cumsum(phase_delta)
    
    # 4. Generate the pure, un-fractured sine wave oscillation
    audio_signal = np.sin(phase).astype(np.float32)
    
    return audio_signal
    
    
    
    
    
    
    
# -------------------- TRANSFORMER FUNCTION --------------------
def transform_image_to_audio(image_path, output_audio_path):
    print(f"TRANSFORMER - Starting analysis on: {image_path}")
    
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