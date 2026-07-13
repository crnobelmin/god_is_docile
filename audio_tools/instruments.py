import numpy as np

def generate_pixel_highs(blue_pixel_slice: np.ndarray, duration: float, sample_rate: int = 44100) -> np.ndarray:
    """
    Generates a shimmering, crystalline additive bell/chime texture.
    Blue pixels dictate high-frequency clusters with decaying metallic overtones.
    """
    total_samples = int(sample_rate * duration)
    t = np.linspace(0, duration, total_samples, endpoint=False)
    
    # 1. MAP: Scale blue pixels to high chime territory (600 Hz to 2200 Hz)
    pixel_frequencies = 600.0 + (blue_pixel_slice / 255.0) * 1600.0
    
    # 2. STRETCH: Interpolate
    xp = np.linspace(0, 1, len(blue_pixel_slice))
    x = np.linspace(0, 1, total_samples)
    fundamental_env = np.interp(x, xp, pixel_frequencies)
    
    # 3. ADDITIVE LAYER MATH: Define metallic, slightly detuned chime partials
    # Inharmonic ratios give it that eerie, structural, organic metal bell ring
    partials = [1.0, 2.0, 2.76, 3.41, 4.32]
    partial_weights = [0.5, 0.25, 0.15, 0.07, 0.03] # Higher partials are quieter
    
    audio_signal = np.zeros(total_samples, dtype=np.float32)
    
    # Render and sum each frequency layer individually
    for multiplier, weight in zip(partials, partial_weights):
        freq_layer = fundamental_env * multiplier
        phase = 2 * np.pi * np.cumsum(freq_layer / sample_rate)
        
        # Exponential decay envelope specific to this partial
        # Higher frequencies fade out faster, exactly like real glass or metal
        decay_speed = 3.0 * multiplier
        amp_decay = np.exp(-decay_speed * t)
        
        audio_signal += np.sin(phase) * amp_decay * weight
        
    # Final master safety fade
    fade_len = int(sample_rate * 0.01)
    if total_samples > fade_len:
        env = np.ones(total_samples, dtype=np.float32)
        env[-fade_len:] = np.linspace(1.0, 0.0, fade_len)
        audio_signal *= env
        
    return audio_signal.astype(np.float32)
    
    
    
    
    
    
    
    import numpy as np




def generate_pixel_mids(green_pixel_slice: np.ndarray, duration: float, sample_rate: int = 44100) -> np.ndarray:
    """
    Generates a rich FM (Frequency Modulation) mid-range texture.
    Green pixels map to carrier pitch and timber complexity (modulation index).
    """
    total_samples = int(sample_rate * duration)
    t = np.linspace(0, duration, total_samples, endpoint=False)
    
    # 1. MAP: Scale green pixels to a musical mid-range (130 Hz to 500 Hz)
    pixel_frequencies = 130.0 + (green_pixel_slice / 255.0) * 370.0
    
    # 2. STRETCH: Interpolate across audio samples
    xp = np.linspace(0, 1, len(green_pixel_slice))
    x = np.linspace(0, 1, total_samples)
    carrier_freq_env = np.interp(x, xp, pixel_frequencies)
    
    # 3. MODULATION MATH: Calculate dynamic timbre changes
    # Bright green pixels increase the modulation depth, making the sound brighter/harsher
    mod_index_env = np.interp(x, xp, (green_pixel_slice / 255.0) * 5.0)
    mod_freq_env = carrier_freq_env * 1.5  # Harmonic ratio (1.5 creates perfect fifth overtones)
    
    # Accumulate phases for both modulator and carrier to ensure continuity
    mod_phase = 2 * np.pi * np.cumsum(mod_freq_env / sample_rate)
    
    # The magic FM synthesis formula: Carrier phase is shifted by the Modulator signal
    carrier_phase = 2 * np.pi * np.cumsum(carrier_freq_env / sample_rate) + (mod_index_env * np.sin(mod_phase))
    audio_signal = np.sin(carrier_phase)
    
    # Apply anti-pop fade out
    fade_len = int(sample_rate * 0.02)
    if total_samples > fade_len:
        env = np.ones(total_samples, dtype=np.float32)
        env[-fade_len:] = np.linspace(1.0, 0.0, fade_len)
        audio_signal *= env
        
    return audio_signal.astype(np.float32)