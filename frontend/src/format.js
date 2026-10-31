const nf = new Intl.NumberFormat("en-GB", { maximumFractionDigits: 0 });
 
export const fmt = (n) => (n == null ? "–" : nf.format(n));
export const fmtSigned = (n) => (n == null ? "–" : `${n > 0 ? "+" : ""}${nf.format(n)}`);
export const fmtPct = (n) => (n == null ? "–" : `${n.toFixed(1)}%`);
 
/** "2026-01-15T07:30:00.000Z" -> "07:30" */
export const hhmm = (iso) => new Date(iso).toISOString().slice(11, 16);
 
/** "2026-01-15T07:30:00.000Z" -> "2026-01-15 07:30 UTC" */
export const utcLabel = (iso) =>
  `${new Date(iso).toISOString().slice(0, 16).replace("T", " ")} UTC`;
 
/** 9.5 -> "09:30" */
export const hourLabel = (h) => {
  const hh = Math.floor(h);
  const mm = Math.round((h - hh) * 60);
  return `${String(hh).padStart(2, "0")}:${String(mm).padStart(2, "0")}`;
};