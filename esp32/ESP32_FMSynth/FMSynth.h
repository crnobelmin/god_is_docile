#pragma once

#include <stdint.h>

/**
 * An independent Frequency Modulation (FM) synthesis voice engine.
 * Maintains its own isolated phase accumulators and smoothing states,
 * allowing for individual or multi-voice instantiation.
 */
class FMSynth
{
    public:
        // Constructor: Configures initial internal states safely
        FMSynth();

        /**
         * Fills a target data array with real-time synthesized audio frames.
         * @param buffer Pointer to the target 16-bit signed integer array.
         * @param frames The number of complete stereo pairs to generate.
         */
        void generateBlock(
            int16_t* buffer,
            int frames
        );

    private:
        // Phase Accumulators (Ramp from 0 to 2*Pi continuously)
        float carrierPhase;      // Phase tracker for the fundamental audible tone
        float modPhase;          // Phase tracker for the fast modulation oscillator
        float lfoPhase;          // Phase tracker for the slow vibrato oscillator (3.5 Hz)

        // DSP Filter State
        float smoothedFrequency; // Holds the rolling history of the smoothed pitch state
};