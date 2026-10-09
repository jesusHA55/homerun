// Raw IR receiver: captures the edge durations of one frame.
#pragma once
#include <Arduino.h>

void irrecv_begin();

// Call frequently from loop(). Detects the end of a frame via an idle gap.
void irrecv_update();

bool irrecv_available();
uint16_t irrecv_length();
const uint16_t* irrecv_buffer();

// Release the captured frame so a new one can be received.
void irrecv_resume();

// Ignore incoming edges while we are transmitting our own IR.
void irrecv_suspend();
void irrecv_unsuspend();
