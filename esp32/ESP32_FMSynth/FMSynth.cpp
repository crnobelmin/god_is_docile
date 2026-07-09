#include "FMSynth.h"
#include "Parameters.h"
#include <math.h>


#define SAMPLE_RATE 44100.0f

#define PI2 6.28318530718f


FMSynth::FMSynth()
{
    carrierPhase = 0;
    modPhase = 0;
    lfoPhase = 0;

    smoothedFrequency = 130.0f;
}



void FMSynth::generateBlock(
    int16_t* buffer,
    int frames
)
{

    const float dt = 1.0f / SAMPLE_RATE;


    for(int i=0;i<frames;i++)
    {

        float target =
            synthParams.frequency.load();


        float modulation =
            synthParams.modulation.load();


        float lfoDepth =
            synthParams.lfoDepth.load();



        // smooth frequency changes
        smoothedFrequency +=
            (target-smoothedFrequency)
            *0.0005f;



        // LFO
        lfoPhase +=
            PI2 * 3.5f * dt;


        if(lfoPhase > PI2)
            lfoPhase -= PI2;


        float lfo =
            sin(lfoPhase);



        float carrierFreq =
            smoothedFrequency +
            lfo*lfoDepth;


        float modFreq =
            carrierFreq*1.5f;



        carrierPhase +=
            PI2*carrierFreq*dt;


        modPhase +=
            PI2*modFreq*dt;



        if(carrierPhase>PI2)
            carrierPhase-=PI2;


        if(modPhase>PI2)
            modPhase-=PI2;



        float sample =
            sin(
                carrierPhase +
                modulation *
                sin(modPhase)
            );



        int16_t out =
            sample*32767;



        buffer[i*2]=out;
        buffer[i*2+1]=out;
    }
}