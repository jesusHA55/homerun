# Homerun

A self-hosted home assistant for climate control and plant care, running on a
Raspberry Pi 5 with **Ollama** for natural-language control.

- **Raspberry Pi 5 (8 GB)** — hub: FastAPI backend, React web UI, Ollama, camera.
- **Arduino Mega 2560** — real-time I/O over USB serial: IR climate control,
  soil sensors, water valve.
- **Climate** — Qlima SC-3525 A/C controlled via IR (`arduino-heatpumpir`,
  Qlima/Carrier protocol). Raw-code fallback supported.
- **Plants** — 1 zone / 5 plants, 5 capacitive soil sensors, gravity tank and a
  solenoid valve.
- **Camera** — Raspberry Pi Camera Module 3 with **manual** and **motion**
  detection modes.
- **Ollama agent** — tool-calling assistant: set climate, water plants, check
  sensors, control the camera.

## Architecture

```
                    LAN (browser)
                         │
        ┌────────────────▼─────────────────┐
        │        Raspberry Pi 5 (8GB)       │
        │  React SPA  ◄──HTTP/WS──►  FastAPI│
        │   • SerialManager   • CameraSvc   │
        │   • ClimateSvc      • MotionSvc   │
        │   • PlantsSvc       • OllamaAgent │
        │   • SQLite / event bus / WS       │
        │  Ollama  ·  Pi Camera Module 3    │
        └────────────────┬──────────────────┘
                         │ USB serial (JSON lines @115200)
        ┌────────────────▼──────────────────┐
        │         Arduino Mega 2560         │
        │  IR send/receive · 5× soil · tank │
        │  flow · solenoid valve · watchdog │
        └───────────────────────────────────┘
```

## Repository layout

```
Homerun/
├─ firmware/                Arduino Mega firmware + IR probe
├─ backend/                 FastAPI service
├─ frontend/                React (Vite + TS) SPA
├─ scripts/                 setup / systemd / dev helpers
├─ docs/                    wiring and protocol reference
├─ data/                    sqlite, snapshots, clips (gitignored)
└─ .env.example
```

## Quick start

### 1. Firmware (Arduino Mega)

With [PlatformIO](https://platformio.org/):

```bash
cd firmware
pio run -e megaatmega2560 -t upload
pio device monitor -b 115200
```

Or open `firmware/homerun_mega/homerun_mega.ino` in the Arduino IDE and install
the libraries listed in `firmware/platformio.ini`.

**First, verify the A/C protocol** with the probe sketch:

```bash
cd firmware/ir_probe
pio run -e megaatmega2560 -t upload
pio device monitor -b 115200
```

Point the Qlima remote at the IR receiver and press power / change temperature.
The probe prints the raw timings and a best-effort decode. If it prints
`QCDF ...` the Qlima/Carrier format is confirmed.

### 2. Backend (Raspberry Pi)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[rpi]"
cp ../.env.example ../.env         # edit port / serial device
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

On a non-Pi machine, install without the `rpi` extra and use
`HOMERUN_CAMERA_BACKEND=opencv` or `synthetic`.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev            # http://localhost:5173 (proxies /api to :8000)
npm run build          # static bundle for production
```

### 4. Ollama

```bash
ollama pull llama3.2:3b
ollama serve
```

## Documentation

- `docs/wiring.md` — pin map and power/water safety notes.
- `docs/protocol.md` — Pi ⇄ Mega serial protocol reference.

## Safety

Water and mains-powered switching are involved. Read `docs/wiring.md` before
connecting anything. The firmware closes the valve automatically if it loses
contact with the Pi, and hard-caps continuous watering.
