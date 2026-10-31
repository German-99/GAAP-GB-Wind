import { useMemo } from "react";
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
import { fmt, hourLabel } from "../format";
import { useApi } from "../hooks";
import Section from "./Section";
import Status from "./Status";

export default function CutoffSensitivity() {
  const sensitivity = useApi("/api/accuracy/cutoff-sensitivity", {});

  const rows = useMemo(
    () =>
      (sensitivity.data?.results ?? []).map((r) => ({
        cutoff: hourLabel(r.cutoff_hour),
        mae: r.metrics.mae,
        rmse: r.metrics.rmse,
        p95: r.metrics.abs_error_p95,
      })),
    [sensitivity.data]
  );

  return (
    <Section
      id="sensitivity"
      className="wide"
      title="Cutoff sensitivity"
      subtitle="Error of the forecast selected at different cutoff hours (UTC, previous day). A later cutoff uses a more recent publication, and only helps if it falls before the day-ahead decision deadline."
    >
      <Status {...sensitivity} />
      {rows.length > 0 && (
        <ResponsiveContainer width="100%" height={320}>
          <LineChart data={rows} margin={{ top: 20, right: 20, bottom: 0, left: 10 }}>
            <CartesianGrid {...grid} />
            <XAxis dataKey="cutoff" {...axis} />
            <YAxis tickFormatter={fmt} unit=" MW" width={100} {...axis} />
            <Tooltip {...tooltip} formatter={(v) => `${fmt(v)} MW`} />
            <Legend {...legend} />
            <Line type="monotone" dataKey="mae" name="MAE" stroke={COLORS.forecast} strokeWidth={2.5} />
            <Line type="monotone" dataKey="rmse" name="RMSE" stroke={COLORS.rmse} strokeWidth={2.5} />
            <Line type="monotone" dataKey="p95" name="95th pct. abs. error" stroke={COLORS.over} strokeWidth={2.5} />
          </LineChart>
        </ResponsiveContainer>
      )}
    </Section>
  );
}