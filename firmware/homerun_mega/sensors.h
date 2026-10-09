#pragma once
#include <Arduino.h>

#include "config.h"

struct SensorReadings {
  uint8_t soil[SOIL_COUNT];  // percent
  uint8_t tank;              // percent
  float flow_lpm;            // litres / minute (instantaneous)
  float flow_total_l;        // litres since boot
};

void sensors_begin();
void sensors_update(unsigned long now);
SensorReadings sensors_get();
float sensors_flow_total();
bool sensors_tank_low();
