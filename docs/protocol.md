# Serial protocol (Raspberry Pi ⇄ Arduino Mega)

Newline-delimited JSON over USB serial at 115200 baud. Each command carries an
`id`; the device always answers with an `ack` or `error` for that `id`.
Telemetry and remote-IR events are pushed without an `id`.

## Commands: Pi → Mega

```json
{"id":1,"cmd":"ping"}
{"id":2,"cmd":"sensor.read"}
{"id":3,"cmd":"climate.set","params":{"power":"on","mode":"cool","temp":24,"fan":"auto"}}
{"id":4,"cmd":"valve.set","params":{"state":"open"}}
{"id":5,"cmd":"water.run","params":{"duration_ms":30000}}
{"id":6,"cmd":"water.stop"}
```

| cmd | params | notes |
|---|---|---|
| `ping` | — | heartbeat; keeps the dead-man switch armed |
| `sensor.read` | — | ack; use telemetry for values |
| `climate.set` | `power` `on/off`, `mode` `auto/cool/heat/dry/fan`, `temp` `17-30`, `fan` `auto/1/2/3` | rate-limited to one send per second |
| `valve.set` | `state` `open/closed` | direct valve control |
| `water.run` | `duration_ms` | clamped to `[1000, 60000]`; rejected when tank is low |
| `water.stop` | — | closes the valve |

## Replies: Mega → Pi

```json
{"type":"ack","id":3}
{"type":"error","id":3,"message":"temp out of range (17-30)"}
{"type":"telemetry","soil":[41,37,55,49,44],"tank_level":72,"flow_lpm":0.0,
 "flow_total_l":1.23,"valve":0,"valve_remaining_ms":0,
 "climate":{"power":"on","mode":"cool","temp":24,"fan":"auto"},"uptime_ms":123456}
{"type":"climate_remote","params":{"power":"on","mode":"heat","temp":22,"fan":"low"}}
```

| type | meaning |
|---|---|
| `ack` | command accepted |
| `error` | command rejected (with `message`) |
| `telemetry` | periodic state snapshot (every 2 s) |
| `climate_remote` | the physical remote was decoded; state changed |

## Safety

- Telemetry is sent every 2 s. The Pi sends a heartbeat (`ping`) every 5 s.
- If the firmware hears nothing for `LINK_TIMEOUT_MS` (15 s) it closes the
  valve. Keep heartbeats flowing during long watering runs.
