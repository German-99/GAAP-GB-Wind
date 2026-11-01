import { useMemo, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { axis, COLORS, grid, legend, tooltip } from "../chartTheme";
import { everyNth, fmt, fmtSigned, hhmm, utcLabel } from "../format";
import { useApi, useMediaQuery } from "../hooks";
import Section from "./Section";
import Status from "./Status";

const FIRST_DAY = "2026-01-02";
const LAST_DAY = "2026-02-01";

export default function DeliveryDay({ cutoffHour, windowDays }) {
  const [day, setDay] = useState("2026-01-15");
  const latest = useApi("/api/forecast/latest", {
    delivery_date: day,
    cutoff_hour: cutoffHour,
  });
  const corrected = useApi("/api/forecast/corrected", {
    delivery_date: day,
    cutoff_hour: cutoffHour,
    window_days: windowDays,
  });

  const rows = useMemo(() => {
    if (!latest.data) return [];
    const correctedByTime = new Map(
      (corrected.data?.points ?? []).map((p) => [p.startTime, p.forecast_corrected])
    );
    return latest.data.points.map((p) => ({
      time: hhmm(p.startTime),
      forecast: p.forecast,
      corrected: correctedByTime.get(p.startTime) ?? null,
      actual: p.actual,
    }));
  }, [latest.data, corrected.data]);

  const publications = useMemo(
    () => [...new Set((latest.data?.points ?? []).map((p) => p.publishTime))].map(utcLabel),
    [latest.data]
  );

  // On phones the axis shows fewer hour labels and a narrower value axis, so nothing overlaps.
  const narrow = useMediaQuery("(max-width: 600px)");
  const ticks = useMemo(() => everyNth(rows.map((r) => r.time), narrow ? 6 : 3), [rows, narrow]);

  const cutoffLabel = latest.data?.cutoff_time
    ? `${latest.data.cutoff_time.slice(0, 16).replace("T", " ")} UTC`
    : null;

  return (
    <Section
      id="forecast"
      className="wide"
      title="Forecast at decision time"
      subtitle="Hourly forecast for a delivery day, using only publications available at the previous day's cutoff."
      actions={
        <label className="field">
          Delivery day
          <input
            type="date"
            value={day}
            min={FIRST_DAY}
            max={LAST_DAY}
            onChange={(e) => e.target.value && setDay(e.target.value)}
          />
        </label>
      }
    >
      <div className="pills">
        {cutoffLabel && <span className="pill">Decision cutoff: {cutoffLabel}</span>}
        {publications.length > 0 && (
          <span className="pill">Forecast published: {publications.join(", ")}</span>
        )}
        {corrected.data && (
          <span className="pill">
            Estimated bias: {fmtSigned(corrected.data.bias_estimate)} MW
          </span>
        )}
      </div>

      <Status {...latest} />
      {corrected.error?.status === 422 && (
        <p className="status">
          Bias correction is not available for this day: not enough error history yet.
        </p>
      )}
      {corrected.error && corrected.error.status !== 422 && corrected.error.status !== 404 && (
        <p className="status error">{corrected.error.message}</p>
      )}

      {rows.length > 0 && (
        <ResponsiveContainer width="100%" height={380}>
          <LineChart
            data={rows}
            margin={{ top: 20, right: narrow ? 8 : 20, bottom: 0, left: narrow ? 0 : 10 }}
          >
            <CartesianGrid {...grid} />
            <XAxis dataKey="time" ticks={ticks} interval={0} {...axis} />
            <YAxis tickFormatter={fmt} unit={narrow ? "" : " MW"} width={narrow ? 56 : 100} {...axis} />
            <Tooltip {...tooltip} formatter={(v) => (v == null ? "–" : `${fmt(v)} MW`)} />
            <Legend {...legend} />
            <Line type="monotone" dataKey="actual" name="Actual" stroke={COLORS.actual} dot={false} strokeWidth={2.5} />
            <Line type="monotone" dataKey="forecast" name="Forecast" stroke={COLORS.forecast} dot={false} strokeWidth={2.5} />
            <Line type="monotone" dataKey="corrected" name="Bias-corrected forecast" stroke={COLORS.corrected} dot={false} strokeWidth={2.5} strokeDasharray="5 3" />
          </LineChart>
        </ResponsiveContainer>
      )}
      <p className="hint">Hourly values in MW, times in UTC.</p>
    </Section>
  );
}