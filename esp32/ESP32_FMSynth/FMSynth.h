#pragma once

#include <stdint.h>


class FMSynth
{
public:

    FMSynth();

    void generateBlock(
        int16_t* buffer,
        int frames
    );


private:

    float carrierPhase;
    float modPhase;
    float lfoPhase;

    float smoothedFrequency;

};