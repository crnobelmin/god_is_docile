#include "Parameters.h"


SynthParameters synthParams;


void initParameters()
{
    synthParams.frequency.store(130.0f);
    synthParams.modulation.store(1.0f);
    synthParams.lfoDepth.store(15.0f);
}