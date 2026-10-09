#pragma once
#include <Arduino.h>

struct ClimateState {
  bool power;       // true = on
  char mode[6];     // auto | cool | heat | dry | fan
  uint8_t temp;     // 17..30
  char fan[5];      // auto | 1 | 2 | 3
  bool valid;       // true once we have a known state
};

void climate_begin();
void climate_update(unsigned long now);

// Send a climate command. Returns false + message on invalid/rate-limited.
bool climate_set(bool power, const char* mode, uint8_t temp, const char* fan,
                 char* err, size_t errlen);

ClimateState climate_get();

// True (once) when a physical remote press was decoded and the state changed.
bool climate_take_remote_change(ClimateState* out);

// Decode a raw Qlima/Carrier frame (used by the firmware and the IR probe).
bool climate_decode(const uint16_t* durations, uint16_t len, ClimateState* out);
