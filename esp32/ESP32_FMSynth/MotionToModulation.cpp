#include "MotionToModulation.h"
#include "Parameters.h"
#include <Arduino.h>
#include <cmath> // Required for the exp() function

// Pin allocation according to your wiring configuration
const int PIR_PIN = 14;

// Timers to track the last instant motion was detected
unsigned long lastMotionTime = 0;

void initMotionSensor() {
    // Configure GPIO 14 as an input pin
    pinMode(PIR_PIN, INPUT);
    
    // Seed the timer with the current uptime during boot sequence
    lastMotionTime = millis();
}

void motionUpdate() {
    // Check if the HC-SR501 output is active (HIGH means motion detected)
    if (digitalRead(PIR_PIN) == HIGH) {
        lastMotionTime = millis();
    }

    // Measure time elapsed since motion was last sensed
    unsigned long elapsed = millis() - lastMotionTime;

    // --- State Logic Handling ---
    
    // Condition 1: Motion occurred within the last 30 seconds.
    if (elapsed <= 30000) {
        synthParams.modulation.store(0.0f, std::memory_order_relaxed);
    } 
    // Condition 2: No motion detected for 40+ seconds (30s threshold + 10s ramp completion).
    else if (elapsed >= 40000) {
        synthParams.modulation.store(1.0f, std::memory_order_relaxed);
    } 
    // Condition 3: In between 30s and 40s. Generate the exponential ramp.
    else {
        // Step A: Normalize the active ramp timeline to a 0.0 to 1.0 window
        // 30,000ms represents 0.0, and 40,000ms represents 1.0
        float t = (float)(elapsed - 30000) / 10000.0f;

        // Step B: Apply an exponential growth function
        // Formula: f(t) = (e^(k*t) - 1) / (e^k - 1)
        // A factor of k = 3.0f gives a classic, organic exponential swoop. 
        // (You can increase k for a more sudden curve or lower it toward 1.0 for a more linear shape).
        float k = 3.0f;
        rampValue = (exp(k * t) - 1.0f) / (exp(k) - 1.0f);

        synthParams.modulation.store(rampValue, std::memory_order_relaxed);
    }
}