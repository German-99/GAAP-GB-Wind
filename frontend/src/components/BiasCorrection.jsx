import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { axis, COLORS, grid, legend, tooltip } from "../chartTheme";
import { fmt, fmtSigned } from "../format";
import { useApi } from "../hooks";
import Section from "./Section";
import Status from "./Status";

const ROWS = [
  { key: "mae", label: "MAE", short: "MAE", signed: false },
  { key: "rmse", label: "RMSE", short: "RMSE", signed: false },
  { key: "abs_error_p90", label: "90th pct. absolute error", short: "P90 abs.", signed: false },
  { key: "abs_error_p95", label: "95th pct. absolute error", short: "P95 abs.", signed: false },
  { key: "bias", label: "Bias", signed: true },
  { key: "error_p05", label: "5th pct. error (under-forecast tail)", signed: true, tone: "under" },
  { key: "error_p95", label: "95th pct. error (over-forecast tail)", signed: true, tone: "over" },
];

export default function BiasCorrection({ cutoffHour, windowDays }) {
  const result = useApi("/api/accuracy/bias-correction", {
    cutoff_hour: cutoffHour,
    window_days: windowDays,
  });
  const data = result.data;
  const hasData = data && data.days_evaluated > 0;

  const chartRows = useMemo(
    () =>
      hasData
        ? ROWS.filter((r) => !r.signed).map((r) => ({
            metric: r.short,
            Raw: data.raw[r.key],
            Corrected: data.corrected[r.key],
          }))
        : [],
    [data, hasData]
  );

  return (
    <Section
      id="correction"
      className="tall"
      title="Bias correction"
      subtitle={`Forecast minus the mean error of the previous ${windowDays} days known at the cutoff (D-${data?.lag_days ?? 2} and earlier).`}
    >
      <Status {...result} />
      {data && !hasData && (
        <p className="status">
          Not enough history for a {windowDays}-day window. Try a shorter window.
        </p>
      )}
      {hasData && (
        <>
          <p className="hint">
            {data.days_evaluated} delivery days. Raw covers only the days with a full history
            window, so it differs from Forecast accuracy.
          </p>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart
              layout="vertical"
              data={chartRows}
              margin={{ top: 4, right: 12, bottom: 0, left: 0 }}
            >
              <CartesianGrid {...grid} horizontal={false} />
              <XAxis type="number" tickFormatter={fmt} tickCount={4} {...axis} />
              <YAxis type="category" dataKey="metric" width={64} {...axis} />
              <Tooltip
                {...tooltip}
                cursor={{ fill: "rgba(255,255,255,0.05)" }}
                formatter={(v) => `${fmt(v)} MW`}
              />
              <Legend {...legend} />
              <Bar dataKey="Raw" fill={COLORS.raw} radius={[0, 4, 4, 0]} />
              <Bar dataKey="Corrected" fill={COLORS.corrected} radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>

          <p className="hint">Values below read Raw → Corrected.</p>
          <ul className="delta-list">
            {ROWS.map((r) => {
              const raw = data.raw[r.key];
              const fixed = data.corrected[r.key];
              const f = r.signed ? fmtSigned : fmt;
              const change = r.signed ? null : ((fixed - raw) / raw) * 100;
              return (
                <li key={r.key}>
                  <span>{r.label}</span>
                  {change != null && <strong className="good">{fmtSigned(change)}%</strong>}
                  <small className={r.tone ?? ""}>
                    {f(raw)} → {f(fixed)} MW
                  </small>
                </li>
              );
            })}
          </ul>
          <p className="hint">
            Check both tails: removing the bias can enlarge the tail on the other side.
          </p>
        </>
      )}
    </Section>
  );
}