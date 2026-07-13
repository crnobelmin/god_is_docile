#include "FMSynth.h"
#include "Parameters.h" // Gives access to the shared multi-core atomic parameters
#include <math.h>

#define SAMPLE_RATE 44100.0f  // System clock standard audio sampling rate
#define PI2 6.28318530718f    // Fixed mathematical constant (2 * Pi) for complete radial cycles

/**
 * Constructor: Resets all core oscillator positions to zero and sets up initial pitch profiles.
 */
FMSynth::FMSynth()
{
    carrierPhase = 0.0f;
    modPhase = 0.0f;
    lfoPhase = 0.0f;

    smoothedFrequency = 130.0f; // Initialize at the bottom bound of the instrument's pitch range
}

/**
 * Audio Block Generator: Fills the assigned I2S DMA memory segments with processed FM signals.
 * FIX: Added 'FMSynth::' scope modifier to grant this function access to private member states.
 */
void FMSynth::generateBlock(int16_t* buffer, int frames)
{
    // dt (Delta Time): The duration in fractions of a second for a single discrete audio slice (~22.68 microseconds)
    const float dt = 1.0f / SAMPLE_RATE;

    // REAL-TIME OPTIMIZATION: Extract thread-safe configuration boundaries exactly ONCE per block.
    // This snapshotting pattern shields Core 1 from constant memory locking cycles against Core 0.
    float rawFreqVal = synthParams.frequency.load();     // Normalized pitch input (0.0 to 1.0)
    float rawModVal  = synthParams.modulation.load();    // Normalized brightness input (0.0 to 1.0)
    float lfoDepth   = 15.0f;      // Scaled raw LFO intensity modifier

    // DSP Scaling Calculations: Map linear control sliders to operational audio standards
    float targetFrequency = 130.0f + (rawFreqVal * 370.0f); // Map parameter range safely across 130Hz to 500Hz
    float modulationIndex = rawModVal * 5.0f;               // Scale modulator depth across a factor of 0.0 to 5.0

    // Loop through each frame demanded by the underlying FreeRTOS hardware buffer pipeline
    for (int i = 0; i < frames; i++)
    {
        // Exponential Parameter Smoothing (One-pole Low-Pass Filter Topology)
        // Gently moves our operational frequency towards target updates, filtering out digital step noise.
        smoothedFrequency += (targetFrequency - smoothedFrequency) * 0.0005f;

        // 1. Low Frequency Oscillator Generation
        // Increment phase position based on a target 3.5 Hz speed requirement
        lfoPhase += PI2 * 3.5f * dt;
        if (lfoPhase > PI2) 
        {
            lfoPhase -= PI2; // Bound phase within 0 to 2*Pi to safeguard floating-point accuracy
        }
        float lfo = sin(lfoPhase); // Calculate a standard bipolar trigonometric wave (-1.0 to 1.0)

        // 2. Modulate Intermediate Target Frequencies
        // Add the bipolar LFO output multiplied by our depth limit to inject standard pitch vibrato
        float carrierFreq = smoothedFrequency + (lfo * lfoDepth);
        
        // Define our modulator wave target speed using an explicit 1.5x harmonic ratio
        float modFreq = carrierFreq * 1.5f;

        // 3. Accumulate Component Oscillator Phases
        // Drive both sound generation engines forward based on their explicit instantaneous frequencies
        carrierPhase += PI2 * carrierFreq * dt;
        modPhase     += PI2 * modFreq * dt;

        // Wrap radial tracks to defend against numeric precision decay over extended run sessions
        if (carrierPhase > PI2) carrierPhase -= PI2;
        if (modPhase > PI2)     modPhase -= PI2;

        // 4. Core FM Synthesis Formula
        // Classic 2-Operator FM: The output of the Modulator sin() modifies the phase argument of the Carrier sin().
        float sample = sin(carrierPhase + (modulationIndex * sin(modPhase)));

        // 5. Fixed-Point Audio Quantization
        // Scale the normalized floating-point wave (-1.0 to 1.0) to match native 16-bit signed integer limits.
        int16_t out = sample * 32767;

        // 6. Stereo Buffer Interleaving
        // Mirror the identical mono signal sequentially across both standard channels inside the output array.
        buffer[i * 2]     = out; // Left audio output channel
        buffer[i * 2 + 1] = out; // Right audio output channel
    }
}