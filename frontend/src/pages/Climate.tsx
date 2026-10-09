import { useEffect, useState } from "react";
import { api } from "../api";
import { Button, Card } from "../components/ui";
import type { Climate, SystemStatus } from "../types";

type Props = { system: SystemStatus | null; refresh: () => void };

const MODES: Climate["mode"][] = ["auto", "cool", "heat", "dry", "fan"];
const FANS: Climate["fan"][] = ["auto", "1", "2", "3"];

export default function ClimatePage({ system, refresh }: Props) {
  const [power, setPower] = useState<Climate["power"]>("off");
  const [mode, setMode] = useState<Climate["mode"]>("cool");
  const [temp, setTemp] = useState(24);
  const [fan, setFan] = useState<Climate["fan"]>("auto");
  const [error, setError] = useState("");

  const current = system?.state?.climate;

  useEffect(() => {
    if (!current) return;
    setPower(current.power);
    setMode(current.mode);
    setTemp(current.temp);
    setFan(current.fan);
  }, [current?.power, current?.mode, current?.temp, current?.fan]);

  const send = async (next: Partial<Climate>) => {
    const payload = { power, mode, temp, fan, ...next };
    if (next.power) setPower(next.power);
    if (next.mode) setMode(next.mode);
    if (next.temp !== undefined) setTemp(next.temp);
    if (next.fan) setFan(next.fan);
    try {
      await api.setClimate(payload);
      setError("");
    } catch (err) {
      setError((err as Error).message);
    }
    refresh();
  };

  const offline = !system?.device_connected;

  return (
    <div className="grid">
      <Card title="Power">
        <div className="row">
          <Button active={power === "on"} disabled={offline} onClick={() => send({ power: "on" })}>
            On
          </Button>
          <Button active={power === "off"} disabled={offline} onClick={() => send({ power: "off" })}>
            Off
          </Button>
        </div>
      </Card>

      <Card title="Temperature">
        <div className="row between">
          <Button disabled={offline || temp <= 17} onClick={() => send({ temp: temp - 1 })}>
            −
          </Button>
          <span className="big">{temp}°C</span>
          <Button disabled={offline || temp >= 30} onClick={() => send({ temp: temp + 1 })}>
            +
          </Button>
        </div>
      </Card>

      <Card title="Mode">
        <div className="row tight">
          {MODES.map((option) => (
            <Button key={option} active={mode === option} disabled={offline} onClick={() => send({ mode: option })}>
              {option}
            </Button>
          ))}
        </div>
      </Card>

      <Card title="Fan">
        <div className="row tight">
          {FANS.map((option) => (
            <Button key={option} active={fan === option} disabled={offline} onClick={() => send({ fan: option })}>
              {option}
            </Button>
          ))}
        </div>
      </Card>

      {error && <p className="error">{error}</p>}
      <p className="muted">
        State is assumed from the last command; IR is one-way. Pressing the physical remote
        syncs the dashboard via the IR receiver.
      </p>
    </div>
  );
}
