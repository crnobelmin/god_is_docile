#pragma once

// Initializes the HC-SR501 sensor hardware configuration
void initMotionSensor();

// Non-blocking update loop to handle time tracking and exponential calculation
void motionUpdate();