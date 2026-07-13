#include "Parameters.h"

/**
 * DEFINITION: This line allocates the actual physical memory space for 'synthParams' 
 * on the chip. Because it is defined outside of any function, it resides in the 
 * global BSS/Data memory segment and stays alive for the entire lifecycle of the program.
 */
SynthParameters synthParams;

/**
 * Sets up safe initial values for the synthesizer engine before the audio engine loops kick off.
 */
void initParameters()
{
    // Note: Since the architecture was recently updated to calculate the actual DSP frequency 
    // inside FMSynth.cpp based on a raw 0.0 to 1.0 control input, you may want to eventually 
    // update these defaults to normalized values (e.g., 0.0f instead of 130.0f).
    
    // .store() explicitly performs an atomic write, preventing CPU caching issues
    synthParams.frequency.store(1.0f, std::memory_order_relaxed);  // Sets default initial frequency parameter
    synthParams.modulation.store(1.0f, std::memory_order_relaxed);   // Sets default initial modulation intensity parameter
}