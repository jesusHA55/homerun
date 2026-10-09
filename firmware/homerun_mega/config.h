// Homerun Arduino Mega 2560 firmware configuration.
// Adjust pin assignments and thresholds here.
#pragma once

#include <Arduino.h>

// ---------------------------------------------------------------- IR -------
#define PIN_IR_SEND 9    // IR LED (via transistor driver)
#define PIN_IR_RECV 19   // TSOP38238 demodulator output (active LOW)

// Which Qlima/Carrier model to emit: 1 = Qlima #1, 2 = Qlima #2.
// The two differ only in the "maintenance"/frost-guard frame; normal
// operation is identical, so try 1 first.
#define QLIMA_MODEL 1

// Minimum gap between two IR transmissions to avoid command storms.
#define IR_SEND_MIN_GAP_MS 1000UL

// ------------------------------------------------------ Soil moisture ------
#define SOIL_COUNT 5
static const uint8_t SOIL_PINS[SOIL_COUNT] = {A0, A1, A2, A3, A4};
// Raw ADC calibration. Capacitive sensors read *lower* voltage when wet.
#define SOIL_ADC_DRY 830   // probe in air
#define SOIL_ADC_WET 340   // probe in water

// ------------------------------------------------------- Tank / flow ------
#define PIN_TANK_LEVEL A5
#define TANK_ADC_EMPTY 120
#define TANK_ADC_FULL 880
#define PIN_FLOW 21
#define FLOW_PULSES_PER_LITER 450.0f  // YF-S201

// ------------------------------------------------------------ Watering -----
#define PIN_VALVE 22
#define VALVE_ACTIVE_HIGH true
#define MAX_WATER_MS 60000UL   // hard safety cap
#define MIN_WATER_MS 1000UL

// ------------------------------------------------------------ Protocol -----
#define SERIAL_BAUD 115200
#define TELEMETRY_INTERVAL_MS 2000UL
// If no command/heartbeat arrives from the Pi within this window, close valve.
#define LINK_TIMEOUT_MS 15000UL

// ------------------------------------------------------------- Serial ------
// Comment out to compile with a single hardware UART (USB only).
#define USE_SERIAL_USB
