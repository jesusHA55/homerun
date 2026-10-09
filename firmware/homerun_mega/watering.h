#pragma once
#include <Arduino.h>

void watering_begin();
void watering_update(unsigned long now);

void watering_set_valve(bool open);

// Timed watering, clamped to [MIN_WATER_MS, MAX_WATER_MS].
void watering_start(unsigned long duration_ms);
void watering_stop();

bool watering_is_open();
unsigned long watering_remaining_ms();
