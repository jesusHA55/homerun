import { useEffect, useState } from "react";
import { api } from "../api";
import { Button, Card, SoilRow } from "../components/ui";
import type { PlantState, SystemStatus } from "../types";

type Props = { system: SystemStatus | null; refresh: () => void };

type Events = {
  motion: { id: number; ts: number; snapshot_path: string | null }[];
  watering: { id: number; ts: number; seconds: number; trigger: string }[];
  climate: { id: number; ts: number; power: string; mode: string; temp: number }[];
};

export default function Dashboard({ system, refresh }: Props) {
  const [plants, setPlants] = useState<PlantState | null>(null);
  const [events, setEvents] = useState<Events | null>(null);

  const soilKey = system?.state?.soil?.join(",") ?? "";

  useEffect(() => {
    api.plants().then((p) => setPlants(p as PlantState)).catch(() => {});
    api.events().then((e) => setEvents(e as Events)).catch(() => {});
  }, [soilKey]);

  const climate = system?.state?.climate;
  const device = system?.state;

  return (
    <div className="grid">
      <Card title="Climate" action={<span className="mono">{climate?.power === "on" ? "on" : "off"}</span>}>
        <div className="row between">
          <div>
            <div className="big">{climate ? `${climate.temp}°C` : "--"}</div>
            <div className="muted">
              {climate ? `${climate.mode} · fan ${climate.fan}` : "no data"}
            </div>
          </div>
          <Button
            kind="primary"
            disabled={!device?.connected}
            onClick={async () => {
              if (!climate) return;
              await api.setClimate({ ...climate, power: climate.power === "on" ? "off" : "on" });
              refresh();
            }}
          >
            {climate?.power === "on" ? "Turn off" : "Turn on"}
          </Button>
        </div>
      </Card>

      <Card title="Plants" action={<span className="mono">tank {device?.tank ?? 0}%</span>}>
        <div className="row between" style={{ marginBottom: 10 }}>
          <div>
            <div className="big">{plants?.soil_avg ?? "--"}%</div>
            <div className="muted">average soil moisture</div>
          </div>
          <Button
            disabled={!device?.connected}
            onClick={async () => {
              try {
                await api.water(20);
              } catch (err) {
                alert((err as Error).message);
              }
              refresh();
            }}
          >
            Water 20s
          </Button>
        </div>
        {(device?.soil ?? []).map((value, index) => (
          <SoilRow key={index} index={index} value={value} threshold={plants?.threshold ?? 35} />
        ))}
      </Card>

      <Card title="Camera" action={<span className="mono">{system?.camera.mode ?? "--"}</span>}>
        <img className="cam" src={api.streamUrl()} alt="camera" />
      </Card>

      <Card title="Recent events">
        <table>
          <thead>
            <tr>
              <th>When</th>
              <th>Event</th>
            </tr>
          </thead>
          <tbody>
            {[
              ...(events?.watering ?? []).map((e) => ({
                ts: e.ts,
                text: `Watered ${e.seconds}s (${e.trigger})`,
              })),
              ...(events?.motion ?? []).map((e) => ({ ts: e.ts, text: "Motion detected" })),
              ...(events?.climate ?? []).map((e) => ({
                ts: e.ts,
                text: `Climate ${e.power} ${e.mode} ${e.temp}°C`,
              })),
            ]
              .sort((a, b) => b.ts - a.ts)
              .slice(0, 8)
              .map((event, index) => (
                <tr key={index}>
                  <td className="muted">{new Date(event.ts * 1000).toLocaleTimeString()}</td>
                  <td>{event.text}</td>
                </tr>
              ))}
            {!events && (
              <tr>
                <td colSpan={2} className="muted">
                  loading…
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
