#pragma once
#include <stdint.h>
#include <stddef.h>

void initI2S();


void writeAudio(
    int16_t* buffer,
    size_t samples
);