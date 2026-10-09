import type { ReactNode } from "react";

export function Card({
  title,
  action,
  children,
}: {
  title?: string;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="card">
      {(title || action) && (
        <header className="card-head">
          <h2>{title}</h2>
          {action}
        </header>
      )}
      <div className="card-body">{children}</div>
    </section>
  );
}

export function Button({
  children,
  onClick,
  kind = "default",
  disabled,
  active,
  small,
  title,
}: {
  children: ReactNode;
  onClick?: () => void;
  kind?: "default" | "primary" | "danger";
  disabled?: boolean;
  active?: boolean;
  small?: boolean;
  title?: string;
}) {
  const classes = ["btn", kind !== "default" ? kind : "", active ? "active" : "", small ? "small" : ""]
    .filter(Boolean)
    .join(" ");
  return (
    <button className={classes} onClick={onClick} disabled={disabled} title={title}>
      {children}
    </button>
  );
}

function toneFor(value: number, threshold = 35): string {
  if (value < threshold) return "crit";
  if (value < threshold + 20) return "dry";
  return "wet";
}

export function Bar({ value, threshold = 35 }: { value: number; threshold?: number }) {
  return (
    <div className={`bar ${toneFor(value, threshold)}`}>
      <span style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
    </div>
  );
}

export function SoilRow({ index, value, threshold }: { index: number; value: number; threshold: number }) {
  return (
    <div className="soil-row">
      <span className="muted">#{index + 1}</span>
      <Bar value={value} threshold={threshold} />
      <span className="mono">{value}%</span>
    </div>
  );
}
