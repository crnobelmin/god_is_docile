from PIL import Image
import numpy as np
from scipy.interpolate import interp1d
+
import os


# -------------------- CONVERT IMAGE TO RGB AND BACK --------------------
def image_to_rgb(image):
    # Source: https://www.niwa.nu/2013/05/math-behind-colorspace-conversions-rgb-hsl/
    
    # Extract an array of pixels and normalize it (RGB values go from 0 to 255)
    pixels = np.array(image.convert("RGB")) / 255.0
   
   # Reshape pixels from height x width to 3 columns
    pixels = pixels.reshape(-1, 3)
        
    return pixels
    
    
       
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
    
def create_tonal_masks(luminance_array: np.ndarray, thresholds: tuple = (0.05, 0.2, 0.9, 0.95)):
    """
    Creates binary masks for different tonal ranges based on luminance values.

    Args:
        luminance_array: A 1D array of luminance values (normalized 0-1).
        thresholds: A tuple of four floats representing the boundaries for the
                    five tonal sections (blacks, shadows, midtones, highlights, whites).

    Returns:
        A dictionary where keys are tonal range names and values are boolean masks.
    """
    if len(thresholds) != 4:
        raise ValueError("Thresholds must be a tuple of four values.")

    mask_blacks = luminance_array <= thresholds[0]
    mask_shadows = (luminance_array > thresholds[0]) & (luminance_array <= thresholds[1])
    mask_midtones = (luminance_array > thresholds[1]) & (luminance_array <= thresholds[2])
    mask_highlights = (luminance_array > thresholds[2]) & (luminance_array <= thresholds[3])
    mask_whites = luminance_array > thresholds[3]

    tonal_masks = {
        'blacks': mask_blacks,
        'shadows': mask_shadows,
        'midtones': mask_midtones,
        'highlights': mask_highlights,
        'whites': mask_whites
    }

    return tonal_masks
       
def rgb_to_hsl(rgb_array_normalized: np.ndarray) -> np.ndarray:
    """
    Converts an array of normalized RGB pixel values (0-1) to HSL pixel values.

    This function expects the input normalized RGB array to be in the format obtained
    from `np.array(PIL.Image.open()).reshape(-1, 3) / 255.0`, meaning it's a 2D
    NumPy array where each row represents an [R, G, B] pixel triplet with values in [0, 1].

    Args:
        rgb_array_normalized (np.ndarray): A NumPy array of normalized RGB pixels
                                           with shape (N, 3), where N is the number
                                           of pixels, and each row contains float
                                           R, G, B values in the range [0, 1].

    Returns:
        np.ndarray: A NumPy array of HSL pixels with the same shape (N, 3),
                    where each row represents an [H, S, L] triplet.
                    - Hue (H) is in degrees [0, 360).
                    - Saturation (S) is a float in the range [0, 1].
                    - Lightness (L) is a float in the range [0, 1].

    Raises:
        ValueError: If the input is not a NumPy array or its shape is not (N, 3).
    """
    if not isinstance(rgb_array_normalized, np.ndarray) or rgb_array_normalized.ndim != 2 or rgb_array_normalized.shape[1] != 3:
        raise ValueError("Input 'rgb_array_normalized' must be a NumPy array of shape (N, 3).")

    # Assume input R, G, B values are already normalized to the range [0, 1]
    r = rgb_array_normalized[:, 0]
    g = rgb_array_normalized[:, 1]
    b = rgb_array_normalized[:, 2]

    # Calculate Cmax (maximum channel value) and Cmin (minimum channel value)
    cmax = np.maximum.reduce([r, g, b])
    cmin = np.minimum.reduce([r, g, b])
    delta = cmax - cmin  # Delta is the difference between max and min

    # Initialize H, S, L arrays with zeros
    h = np.zeros_like(r)
    s = np.zeros_like(r)
    l = (cmax + cmin) / 2.0  # Lightness is the average of max and min

    # Calculate Saturation (S)
    # If delta is 0, it's a shade of gray, saturation is 0.
    # Otherwise, calculate based on lightness using a conditional approach.
    non_zero_delta_mask = (delta != 0)

    # Calculate saturation only for non-grayscale pixels
    # Removed the redundant check for sum_cmax_cmin != 0
    s[non_zero_delta_mask] = np.where(
        l[non_zero_delta_mask] <= 0.5,
        delta[non_zero_delta_mask] / (cmax[non_zero_delta_mask] + cmin[non_zero_delta_mask]),
        delta[non_zero_delta_mask] / (2.0 - (cmax[non_zero_delta_mask] + cmin[non_zero_delta_mask]))
    )

    # Calculate Hue (H)
    # Only calculate hue if delta is not zero (i.e., not a grayscale pixel)
    # The non_zero_delta_mask is already defined above

    # Case 1: Cmax == R
    mask_r = (cmax == r) & non_zero_delta_mask
    h[mask_r] = 60 * (((g[mask_r] - b[mask_r]) / delta[mask_r]) % 6)

    # Case 2: Cmax == G
    mask_g = (cmax == g) & non_zero_delta_mask
    h[mask_g] = 60 * (((b[mask_g] - r[mask_g]) / delta[mask_g]) + 2)

    # Case 3: Cmax == B
    mask_b = (cmax == b) & non_zero_delta_mask
    h[mask_b] = 60 * (((r[mask_b] - g[mask_b]) / delta[mask_b]) + 4)


    # Ensure hue values are non-negative, as the modulo operator in Python
    # can return negative results for negative inputs.
    h[h < 0] += 360

    # Stack the H, S, L components into a single array
    hsl_array = np.stack([h, s, l], axis=-1)

    return hsl_array         
        