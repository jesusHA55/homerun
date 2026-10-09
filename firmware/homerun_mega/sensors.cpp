#include "config.h"
#include "sensors.h"

static volatile unsigned long s_flowPulses = 0;

static SensorReadings s_readings;
static unsigned long s_lastSoilMs = 0;
static unsigned long s_lastFlowMs = 0;
static unsigned long s_lastPulseCount = 0;
static float s_totalLiters = 0.0f;

static void flowISR() { s_flowPulses++; }

// wetAdc -> 100 %, dryAdc -> 0 %.
static uint8_t pctFromAdc(uint16_t adc, uint16_t wetAdc, uint16_t dryAdc) {
  if (dryAdc <= wetAdc) return 0;
  long v = ((long)dryAdc - (long)adc) * 100L / ((long)dryAdc - (long)wetAdc);
  if (v < 0) v = 0;
  if (v > 100) v = 100;
  return (uint8_t)v;
}

static uint16_t readAveraged(uint8_t pin) {
  uint32_t sum = 0;
  for (uint8_t i = 0; i < 8; i++) {
    sum += analogRead(pin);
    delayMicroseconds(200);
  }
  return (uint16_t)(sum / 8);
}

void sensors_begin() {
  pinMode(PIN_FLOW, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(PIN_FLOW), flowISR, FALLING);
  for (uint8_t i = 0; i < SOIL_COUNT; i++) {
    s_readings.soil[i] = 0;
  }
  s_readings.tank = 0;
  s_readings.flow_lpm = 0;
  s_readings.flow_total_l = 0;
  s_lastFlowMs = millis();
}

void sensors_update(unsigned long now) {
  // Flow: compute litres/minute over the last second.
  if (now - s_lastFlowMs >= 1000UL) {
    noInterrupts();
    unsigned long pulses = s_flowPulses;
    interrupts();

    unsigned long delta = pulses - s_lastPulseCount;
    s_lastPulseCount = pulses;
    s_readings.flow_lpm = (delta / FLOW_PULSES_PER_LITER) * 60.0f;
    s_totalLiters += delta / FLOW_PULSES_PER_LITER;
    s_readings.flow_total_l = s_totalLiters;
    s_lastFlowMs = now;
  }

  // Soil + tank: every 2 s.
  if (now - s_lastSoilMs >= 2000UL || s_lastSoilMs == 0) {
    for (uint8_t i = 0; i < SOIL_COUNT; i++) {
      uint16_t adc = readAveraged(SOIL_PINS[i]);
      s_readings.soil[i] = pctFromAdc(adc, SOIL_ADC_WET, SOIL_ADC_DRY);
    }
    uint16_t tankAdc = readAveraged(PIN_TANK_LEVEL);
    s_readings.tank = pctFromAdc(tankAdc, TANK_ADC_FULL, TANK_ADC_EMPTY);
    s_lastSoilMs = now;
  }
}

SensorReadings sensors_get() { return s_readings; }
float sensors_flow_total() { return s_totalLiters; }
bool sensors_tank_low() { return s_readings.tank < 10; }
