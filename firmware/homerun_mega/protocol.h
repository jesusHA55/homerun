#pragma once
#include <Arduino.h>

void protocol_begin();

// Read serial, dispatch commands, forward remote-IR events.
void protocol_poll();

// True if the Pi has sent anything recently (used as a dead-man switch).
bool protocol_link_alive();

void protocol_send_telemetry();
