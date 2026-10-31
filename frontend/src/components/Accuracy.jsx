import { fmt, fmtPct, fmtSigned } from "../format";
import { useApi } from "../hooks";
import Status from "./Status";

// Tone: "over" = forecast above the actual (amber), "under" = below (cyan).
const KPIS = [
  { key: "mae", title: "Mean absolute error", note: "Average miss, in either direction", format: fmt },
  { key: "rmse", title: "RMSE", note: "Weights large misses more", format: fmt },
  {
    key: "bias",
    title: "Bias",
    note: "Forecast minus actual, on average",
    format: fmtSigned,
    tone: (v) => (v > 0 ? "over" : "under"),
  },
  { key: "abs_error_p95", title: "95th pct. absolute error", note: "1 hour in 20 misses by more than this", format: fmt },
];

const STATS = [
  { key: "mape_pct", label: "MAPE", format: fmtPct, unit: "" },
  { key: "abs_error_p90", label: "90th pct. absolute error", format: fmt, unit: "MW" },
  { key: "error_p05", label: "5th pct. error (under-forecast tail)", format: fmtSigned, unit: "MW", tone: () => "under" },
  { key: "error_p95", label: "95th pct. error (over-forecast tail)", format: fmtSigned, unit: "MW", tone: () => "over" },
];

export default function Accuracy({ cutoffHour }) {
  const summary = useApi("/api/accuracy/summary", { cutoff_hour: cutoffHour });
  const metrics = summary.data?.metrics;

  return (
    <>
      <div className="group-head" id="accuracy">
        <h2>Forecast accuracy</h2>
        <p className="subtitle">
          Latest forecast at the cutoff vs actual generation, 2 Jan – 1 Feb 2026
          {metrics ? ` (${fmt(metrics.n)} hourly values)` : ""}. Amber means the forecast was above
          the actual, cyan below.
        </p>
      </div>
      <Status {...summary} className="span-all" />
      {metrics && (
        <>
          {KPIS.map((k) => (
            <article className="card kpi" key={k.key}>
              <h3>{k.title}</h3>
              <p className="subtitle">{k.note}</p>
              <div className={`value ${k.tone ? k.tone(metrics[k.key]) : ""}`}>
                {k.format(metrics[k.key])} <small>MW</small>
              </div>
            </article>
          ))}
          <section className="card stat-strip">
            {STATS.map((s) => (
              <div className="stat" key={s.key}>
                <div className="stat-label">{s.label}</div>
                <div className={`stat-value ${s.tone ? s.tone() : ""}`}>
                  {s.format(metrics[s.key])} {s.unit && <small>{s.unit}</small>}
                </div>
              </div>
            ))}
          </section>
        </>
      )}
    </>
  );
}