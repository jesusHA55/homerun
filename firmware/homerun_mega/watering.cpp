#include "config.h"
#include "watering.h"

static bool s_open = false;
static bool s_timed = false;
static unsigned long s_stopAt = 0;

static void applyValve(bool open) {
  bool level = VALVE_ACTIVE_HIGH ? open : !open;
  digitalWrite(PIN_VALVE, level ? HIGH : LOW);
}

void watering_begin() {
  pinMode(PIN_VALVE, OUTPUT);
  applyValve(false);
}

void watering_set_valve(bool open) {
  applyValve(open);
  s_open = open;
  s_timed = false;
}

void watering_start(unsigned long duration_ms) {
  if (duration_ms < MIN_WATER_MS) duration_ms = MIN_WATER_MS;
  if (duration_ms > MAX_WATER_MS) duration_ms = MAX_WATER_MS;
  applyValve(true);
  s_open = true;
  s_timed = true;
  s_stopAt = millis() + duration_ms;
}

void watering_stop() {
  applyValve(false);
  s_open = false;
  s_timed = false;
}

void watering_update(unsigned long now) {
  if (s_open && s_timed && (long)(now - s_stopAt) >= 0) {
    watering_stop();
  }
}

bool watering_is_open() { return s_open; }

unsigned long watering_remaining_ms() {
  if (!s_open || !s_timed) return 0;
  unsigned long now = millis();
  if ((long)(s_stopAt - now) < 0) return 0;
  return s_stopAt - now;
}
