# Wiring and hardware notes

## Overview

```
Raspberry Pi 5  ──USB──►  Arduino Mega 2560
   │                          ├── IR LED (send)      → Qlima SC-3525
   │                          ├── IR receiver         ← physical remote
   │                          ├── 5× soil sensors
   │                          ├── tank level sensor
   │                          ├── flow sensor
   │                          └── relay → solenoid valve → drip lines
   └── Pi Camera Module 3
```

## Arduino Mega pin map

| Function | Pin | Notes |
|---|---|---|
| IR LED (send) | D9 | Through an NPN/MOSFET driver + current-limiting resistor |
| IR receiver | D19 | TSOP38238, VCC 5 V, GND, OUT→D19 |
| Soil moisture ×5 | A0–A4 | Capacitive probes, powered from 5 V (or 3.3 V for stability) |
| Tank level | A5 | Analog float / pressure / ultrasonic analog output |
| Flow sensor | D21 | YF-S201, interrupt input, needs pull-up |
| Solenoid valve relay | D22 | Opto-isolated relay module input |
| Status LED | D13 | On-board LED, blinks with telemetry |

Baud: **115200**.

## IR

- Transmit: `arduino-heatpumpir` Qlima/Carrier protocol, ~38 kHz.
- Receive: the firmware captures raw edge timings and decodes the Carrier MCA
  frame so the dashboard mirrors the physical remote.
- Keep the IR LED reasonably close to the A/C (1–5 m) and clear of sunlight.

Confirm the protocol first with `firmware/ir_probe`. A frame that prints
`QCDF ok ...` means dynamic control is confirmed. If it prints
`not Qlima/Carrier MCA`, the raw fallback will be needed — tell the developer
and the learned-code path will be enabled.

## Soil sensors

Capacitive sensors read **lower** analog voltage when the soil is wet. Calibrate
`SOIL_ADC_DRY` (in air) and `SOIL_ADC_WET` (in water) in
`firmware/homerun_mega/config.h` for your specific probes.

## Watering (gravity tank)

- The tank must be **above** the valve. ~1 m of head gives ~0.1 bar.
- Use a **low-pressure / low-crack-pressure** solenoid valve; many standard
  valves will not open reliably on gravity alone. If flow is poor, either raise
  the tank or add a small pump (the firmware/backend already model an optional
  pump, even though it is not enabled here).
- Watch out for **water hammer** and **leaks**: put a drip tray under the tank
  and keep electronics above the water line.
- The firmware closes the valve if it stops hearing from the Pi (dead-man
  switch) and hard-caps continuous watering at `MAX_WATER_MS` (60 s).

### 3D-printed tank checklist

- Food-safe / UV-stable filament if it sees light.
- Bulkhead fitting at the **lowest** point for the outlet.
- Wide fill lid; add a breather hole.
- A molded recess for the level sensor, and a flat base on a stand for head.
- Print with enough walls/infill and seal seams (PETG + food-safe epoxy).

## Power

- Arduino logic: USB from the Pi (5 V).
- Solenoid valve: **separate** 12/24 V supply, common ground with the relay
  module. Add a **flyback diode** across the valve coil.
- Relay module: opto-isolated; power its coil side from the valve supply if
  required.

## Safety summary

1. Never switch mains with the Arduino.
2. Separate the water path from mains/electronics.
3. Fuse the valve supply.
4. Test the dead-man switch by unplugging USB while the valve is open — it must
   close within `LINK_TIMEOUT_MS` (15 s).
