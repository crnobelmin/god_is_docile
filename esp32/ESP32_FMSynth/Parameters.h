#pragma once

#include <atomic>


struct SynthParameters
{
    std::atomic<float> frequency;
    std::atomic<float> modulation;
    std::atomic<float> lfoDepth;
};


extern SynthParameters synthParams;


void initParameters();