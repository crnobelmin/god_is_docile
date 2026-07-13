#pragma once // Ensure this header is included only once per file
#include <atomic> // Atomic wrappers for thread-safe multi-core variables

/**
 * A central global structure holding the control parameters for the synthesizer.
 * Every variable is wrapped in std::atomic to prevent cross-core memory corruption.
 */
struct SynthParameters
{
    // Holds the normalized target frequency value (0.0 to 1.0)
    std::atomic<float> frequency;
    
    // Holds the normalized modulation index multiplier value (0.0 to 1.0)
    std::atomic<float> modulation;
    
};

/**
 * The 'extern' keyword tells the compiler that the actual memory allocation for 
 * 'synthParams' happens inside a separate source (.cpp) file. This acts as a global 
 * reference declaration, making the parameters searchable and usable across the entire project.
 */
extern SynthParameters synthParams;

/**
 * Public function declaration to initialize parameters with default startup values.
 */
void initParameters();