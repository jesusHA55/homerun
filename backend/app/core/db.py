"""Minimal SQLite persistence layer (synchronous, guarded by a lock).

The workload here is tiny (a home device), so a single connection with a
threading lock is more than sufficient and keeps the dependency list small.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS telemetry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    soil_json TEXT NOT NULL,
    tank INTEGER NOT NULL,
    flow_lpm REAL NOT NULL,
    valve INTEGER NOT NULL,
    climate_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS climate_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    power TEXT NOT NULL,
    mode TEXT NOT NULL,
    temp INTEGER NOT NULL,
    fan TEXT NOT NULL,
    source TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS watering_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    zone INTEGER NOT NULL,
    seconds INTEGER NOT NULL,
    trigger TEXT NOT NULL,
    liters REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS motion_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    snapshot_path TEXT,
    clip_path TEXT,
    area REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    actions_json TEXT
);

CREATE TABLE IF NOT EXISTS schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    zone INTEGER NOT NULL UNIQUE,
    enabled INTEGER NOT NULL DEFAULT 1,
    every_hours REAL NOT NULL DEFAULT 24,
    duration_s INTEGER NOT NULL DEFAULT 20,
    min_soil INTEGER NOT NULL DEFAULT 35
);
"""


class Database:
    def __init__(self, path: str) -> None:
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row

    def init_schema(self) -> None:
        with self._lock:
            self._conn.executescript(SCHEMA)
            self._conn.commit()

    def execute(self, sql: str, params: tuple = ()) -> int:
        with self._lock:
            cur = self._conn.execute(sql, params)
            self._conn.commit()
            return cur.lastrowid

    def query(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]

    # --- convenience -------------------------------------------------------
    def add_telemetry(self, soil: list[int], tank: int, flow_lpm: float,
                      valve: bool, climate: dict) -> int:
        return self.execute(
            "INSERT INTO telemetry (ts, soil_json, tank, flow_lpm, valve, climate_json)"
            " VALUES (?,?,?,?,?,?)",
            (time.time(), json.dumps(soil), tank, flow_lpm,
             1 if valve else 0, json.dumps(climate)),
        )

    def add_climate_event(self, climate: dict, source: str) -> int:
        return self.execute(
            "INSERT INTO climate_events (ts, power, mode, temp, fan, source)"
            " VALUES (?,?,?,?,?,?)",
            (time.time(), climate["power"], climate["mode"], int(climate["temp"]),
             climate["fan"], source),
        )

    def add_watering_event(self, zone: int, seconds: int, trigger: str,
                           liters: float = 0.0) -> int:
        return self.execute(
            "INSERT INTO watering_events (ts, zone, seconds, trigger, liters)"
            " VALUES (?,?,?,?,?)",
            (time.time(), zone, seconds, trigger, liters),
        )

    def add_motion_event(self, snapshot_path: str | None, clip_path: str | None,
                         area: float) -> int:
        return self.execute(
            "INSERT INTO motion_events (ts, snapshot_path, clip_path, area)"
            " VALUES (?,?,?,?)",
            (time.time(), snapshot_path, clip_path, area),
        )

    def add_chat_message(self, role: str, content: str,
                         actions: list | None = None) -> int:
        return self.execute(
            "INSERT INTO chat_messages (ts, role, content, actions_json)"
            " VALUES (?,?,?,?)",
            (time.time(), role, content,
             json.dumps(actions) if actions else None),
        )

    def recent(self, table: str, limit: int = 50) -> list[dict[str, Any]]:
        # Table names are internal constants, never user input.
        return self.query(f"SELECT * FROM {table} ORDER BY id DESC LIMIT ?", (limit,))

    def last_watered_ts(self, zone: int) -> float | None:
        rows = self.query(
            "SELECT ts FROM watering_events WHERE zone=? ORDER BY id DESC LIMIT 1",
            (zone,),
        )
        return rows[0]["ts"] if rows else None

    def get_schedule(self, zone: int) -> dict[str, Any] | None:
        rows = self.query("SELECT * FROM schedules WHERE zone=?", (zone,))
        return rows[0] if rows else None

    def upsert_schedule(self, zone: int, enabled: bool, every_hours: float,
                        duration_s: int, min_soil: int) -> None:
        self.execute(
            "INSERT INTO schedules (zone, enabled, every_hours, duration_s, min_soil)"
            " VALUES (?,?,?,?,?)"
            " ON CONFLICT(zone) DO UPDATE SET enabled=excluded.enabled,"
            " every_hours=excluded.every_hours, duration_s=excluded.duration_s,"
            " min_soil=excluded.min_soil",
            (zone, 1 if enabled else 0, every_hours, duration_s, min_soil),
        )
