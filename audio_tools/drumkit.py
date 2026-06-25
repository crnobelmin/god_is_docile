import numpy as np
import wave
import os
import sys

def generate_kick(sample_rate: int = 44100) -> np.ndarray:
    """Pitch-swept sine wave with fast exponential volume decay."""
    duration = 0.15
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    
    # Pitch sweep: drops rapidly from 150Hz down to 40Hz
    f_sweep = 40.0 + (150.0 - 40.0) * np.exp(-60.0 * t)
    phase = 2 * np.pi * np.cumsum(f_sweep / sample_rate)
    
    # Amplitude envelope: fast decay
    amp_env = np.exp(-18.0 * t)
    
    return (np.sin(phase) * amp_env).astype(np.float32)

def generate_snare(sample_rate: int = 44100) -> np.ndarray:
    """A body tone (180Hz) mixed with a sharp burst of white noise."""
    duration = 0.2
    total_samples = int(sample_rate * duration)
    t = np.linspace(0, duration, total_samples, endpoint=False)
    
    # 1. Fundamental drum shell tone (180Hz decaying to 80Hz)
    f_sweep = 80.0 + (180.0 - 80.0) * np.exp(-40.0 * t)
    phase = 2 * np.pi * np.cumsum(f_sweep / sample_rate)
    tone = np.sin(phase) * np.exp(-30.0 * t)
    
    # 2. Snare rattle (White Noise)
    noise = np.random.normal(0, 0.3, total_samples)
    noise_env = np.exp(-12.0 * t)
    
    # Mix together (60% noise texture, 40% low-end punch)
    signal = (0.4 * tone) + (0.6 * noise * noise_env)
    return signal.astype(np.float32)

def generate_closed_hat(sample_rate: int = 44100) -> np.ndarray:
    """Hyper-short burst of filtered white noise."""
    duration = 0.04
    total_samples = int(sample_rate * duration)
    t = np.linspace(0, duration, total_samples, endpoint=False)
    
    # Raw noise with an aggressive volume decay
    noise = np.random.normal(0, 0.4, total_samples)
    amp_env = np.exp(-75.0 * t)
    
    return (noise * amp_env).astype(np.float32)

def generate_open_hat(sample_rate: int = 44100) -> np.ndarray:
    """Longer, breathing version of the hi-hat."""
    duration = 0.25
    total_samples = int(sample_rate * duration)
    t = np.linspace(0, duration, total_samples, endpoint=False)
    
    noise = np.random.normal(0, 0.3, total_samples)
    # Slower decay allows the cymbal sound to bleed outward
    amp_env = np.exp(-15.0 * t)
    
    return (noise * amp_env).astype(np.float32)

def generate_clap(sample_rate: int = 44100) -> np.ndarray:
    """Staggered noise spikes modeling multiple hands hitting slightly out of time."""
    duration = 0.25
    total_samples = int(sample_rate * duration)
    signal = np.zeros(total_samples, dtype=np.float32)
    
    # Create 3 small initial transient hand strikes spaced ~12ms apart
    strike_offsets = [0, int(sample_rate * 0.012), int(sample_rate * 0.024)]
    
    for offset in strike_offsets:
        remaining = total_samples - offset
        t_strike = np.linspace(0, remaining / sample_rate, remaining, endpoint=False)
        strike_noise = np.random.normal(0, 0.25, remaining) * np.exp(-120.0 * t_strike)
        signal[offset:] += strike_noise
        
    # Add the final, long collective decay tail
    t_full = np.linspace(0, duration, total_samples, endpoint=False)
    tail = np.random.normal(0, 0.2, total_samples) * np.exp(-15.0 * t_full)
    
    master_clap = signal + tail
    return (master_clap / np.max(np.abs(master_clap)) * 0.7).astype(np.float32)
    
def generate_tom(frequency: float, sample_rate: int = 44100) -> np.ndarray:
  """Resonant pitch-dropping sine wave for low/high toms."""
  duration = 0.25
  t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
  
  # Pitch sweep drops down roughly 40% from its initial hit frequency
  f_sweep = (frequency * 0.6) + (frequency * 0.4) * np.exp(-25.0 * t)
  phase = 2 * np.pi * np.cumsum(f_sweep / sample_rate)
  amp_env = np.exp(-10.0 * t)
  
  return (np.sin(phase) * amp_env).astype(np.float32)

# =====================================================================
# 2. THE RHYTHMIC COHERENCE ENGINE
# =====================================================================

def export_kit_coherence_test(bpm=120, bars_to_loop=4, sample_rate=44100, filename="kit_coherence_test.wav"):
    """
    Simulates a 1-bar 8x8 grid step sequencer matrix, loops it, 
    and saves the mixed master audio to disk.
    """
    print("🥁 Initializing temporary drum instrument buffers...")
    kit = {
        0: generate_kick(sample_rate),
        1: generate_snare(sample_rate),
        2: generate_closed_hat(sample_rate),
        3: generate_open_hat(sample_rate),
        4: generate_clap(sample_rate),
        5: generate_tom(120.0, sample_rate)
    }

    # Calculate timing windows for an 8th-note grid step
    # 60 / BPM = length of a quarter note. Divide by 2 for an 8th note step.
    seconds_per_step = (60.0 / bpm) / 2.0
    samples_per_step = int(sample_rate * seconds_per_step)
    samples_per_bar = samples_per_step * 8
    
    # Create an empty single-bar mixing canvas
    bar_buffer = np.zeros(samples_per_bar, dtype=np.float32)

    # 🛠️ PROTOTYPE 8x8 PATTERN MATRIX
    # Rows (0-7) represent 8 consecutive time steps in the bar.
    # Columns (0-7) represent the 8 instruments in our kit map.
    # 1 = Trigger hit at max volume, 0.5 = Low velocity accent hit.
    pattern_matrix = np.array([
        # K  S   CH  OH  Clp LT  HT  Rim
        [1,  0,  0,  0,  1,  0],
        [0,  0,  1,  0,  0,  0],  # Step 1: Up-hat
        [0,  1,  0,  0,  0,  0],  # Step 2: Backbeat Snare + Layered Clap
        [0,  0,  1,  0,  0,  0],  # Step 3: Low Tom roll
        [1,  0, 0,  0,  0,  0],  # Step 4: Mid-bar Kick + Open Hat breathing
        [0,  0,  1,  0,  0,  0],  # Step 5: High Tom syncopation
        [0,  1,  0,  0,  0,  0],  # Step 6: Second Snare punch
        [0,  0,  1,  0,  0,  1]   # Step 7: Final Open Hat tail
    ])

    # Run through the 8 vertical steps of time
    for step in range(8):
        step_start_idx = step * samples_per_step
        
        # Check all 8 horizontal instruments at this specific moment in time
        for instrument_idx in range(6):
            velocity = pattern_matrix[step, instrument_idx]
            
            if velocity > 0:
                audio_hit = kit[instrument_idx] * velocity
                hit_len = len(audio_hit)
                
                # Determine how many audio samples we can safely write without bleeding
                # over the physical end edge of our 1-bar array buffer
                write_end_idx = min(step_start_idx + hit_len, samples_per_bar)
                available_space = write_end_idx - step_start_idx
                
                # Linear Mix Phase: Directly sum the array values together
                bar_buffer[step_start_idx:write_end_idx] += audio_hit[:available_space]


    master_timeline = np.tile(bar_buffer, bars_to_loop)

    # 🛑 CRITICAL MIX BUS SAFETY: Prevent digital distortion clipping
    # When multiple elements (Kick+Snare+Clap) hit on the exact same sample index,
    # their combined floating values might exceed 1.0. We normalize the master array.
    peak_volume = np.max(np.abs(master_timeline))
    if peak_volume > 1.0:
        print(f"⚠️ Mix bus warning: Peak hit reached {peak_volume:.2f}. Normalizing to 0.95 to protect speakers.")
        master_timeline = (master_timeline / peak_volume) * 0.95

    # Cast to standard 16-bit PCM bytes
    audio_ints = (master_timeline * 32767).astype(np.int16)

    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_ints.tobytes())

    print(f"💾 Render Complete -> {filename}")


if __name__ == "__main__":
    # 1. Set default values if no arguments are provided
    output_filename = "kit_coherence_test.wav"

    # 2. Parse the first command-line argument for the filename
    if len(sys.argv) > 1:
        output_filename = sys.argv[1]
        
        # Friendly safety check: append .wav if you forgot to type it
        if not output_filename.endswith(".wav"):
            output_filename += ".wav"
        
    # 3. Optional: Parse a second argument for the BPM tempo
    if len(sys.argv) > 2:
        try:
            target_bpm = int(sys.argv[2])
        except ValueError:
            print(f"⚠️ Invalid BPM input '{sys.argv[2]}'. Falling back to default: {target_bpm}")
            
    export_kit_coherence_test(filename=output_filename, bpm = target_bpm)