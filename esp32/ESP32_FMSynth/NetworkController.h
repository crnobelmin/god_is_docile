#pragma once // Preprocessor directive to ensure this header file is included only once during compilation

// Function declarations so other parts of your program know these functions exist
void initNetwork();    // Initializes the Wi-Fi connection and starts UDP listening
void networkUpdate();  // Checks for and processes incoming UDP network data (runs inside loop)