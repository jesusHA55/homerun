import { useEffect, useState } from "react";
import { api } from "../api";
import { Button, Card, SoilRow } from "../components/ui";
import type { PlantState, SystemStatus } from "../types";

type Props = { system: SystemStatus | null; refresh: () => void };

export default function Plants({ system, refresh }: Props) {
  const [plants, setPlants] = useState<PlantState | null>(null);
  const [seconds, setSeconds] = useState(20);
  const [error, setError] = useState("");
  const [schedule, setSchedule] = useState({
    enabled: true,
    every_hours: 24,
    duration_s: 20,
    min_soil: 35,
  });

  const soilKey = system?.state?.soil?.join(",") ?? "";

  const load = () =>
    api
      .plants()
      .then((p) => {
        const data = p as PlantState;
        setPlants(data);
        setSchedule({
          enabled: !!data.schedule.enabled,
          every_hours: data.schedule.every_hours,
          duration_s: data.schedule.duration_s,
          min_soil: data.schedule.min_soil,
        });
      })
      .catch(() => {});

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [soilKey]);

  const water = async () => {
    try {
      await api.water(seconds);
      setError("");
    } catch (err) {
      setError((err as Error).message);
    }
    refresh();
  };

  const offline = !system?.device_connected;
  const soil = system?.state?.soil ?? [];

  return (
    <div className="grid">
      <Card title="Zone 1 · Plants" action={<span className="mono">tank {system?.state?.tank ?? 0}%</span>}>
        {soil.map((value, index) => (
          <SoilRow key={index} index={index} value={value} threshold={plants?.threshold ?? 35} />
        ))}
        <p className="muted">
          Average {plants?.soil_avg ?? "--"}% · threshold {plants?.threshold ?? 35}% · target{" "}
          {plants?.target ?? 55}%
        </p>
      </Card>

      <Card title="Water now">
        <div className="row">
          <input
            type="number"
            min={1}
            max={60}
            value={seconds}
            onChange={(e) => setSeconds(Number(e.target.value))}
            style={{ width: 90 }}
          />
          <span className="muted">seconds</span>
          <Button kind="primary" disabled={offline} onClick={water}>
            Water
          </Button>
          <Button kind="danger" disabled={offline} onClick={() => api.stopWater().then(refresh)}>
            Stop
          </Button>
        </div>
        <p className="muted" style={{ marginTop: 10 }}>
          Valve {system?.state?.valve_open ? "open" : "closed"}
          {system?.state?.valve_open && system?.state?.valve_remaining_ms
            ? ` · ${Math.round(system.state.valve_remaining_ms / 1000)}s left`
            : ""}
        </p>
        {error && <p className="error">{error}</p>}
      </Card>

      <Card title="Automatic schedule">
        <div className="row tight" style={{ marginBottom: 12 }}>
          <label className="row tight">
            <input
              type="checkbox"
              checked={schedule.enabled}
              onChange={(e) => setSchedule({ ...schedule, enabled: e.target.checked })}
            />
            enabled
          </label>
        </div>
        <div className="row">
          <label>
            every
            <input
              type="number"
              value={schedule.every_hours}
              min={1}
              onChange={(e) => setSchedule({ ...schedule, every_hours: Number(e.target.value) })}
              style={{ width: 80, marginLeft: 8 }}
            />
            h
          </label>
          <label>
            for
            <input
              type="number"
              value={schedule.duration_s}
              min={1}
              max={60}
              onChange={(e) => setSchedule({ ...schedule, duration_s: Number(e.target.value) })}
              style={{ width: 80, marginLeft: 8 }}
            />
            s
          </label>
          <label>
            below
            <input
              type="number"
              value={schedule.min_soil}
              min={0}
              max={100}
              onChange={(e) => setSchedule({ ...schedule, min_soil: Number(e.target.value) })}
              style={{ width: 80, marginLeft: 8 }}
            />
            %
          </label>
        </div>
        <div className="row" style={{ marginTop: 14 }}>
          <Button kind="primary" onClick={() => api.setSchedule(schedule).then(load)}>
            Save schedule
          </Button>
        </div>
      </Card>
    </div>
  );
}
