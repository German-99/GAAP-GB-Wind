import { useEffect, useState } from "react";

export const DEFAULT_WINDOW_DAYS = 7;
const MIN_WINDOW_DAYS = 1;
const MAX_WINDOW_DAYS = 28;

/**
 * Number field for the bias window. The text being typed is kept apart from the applied
 * value, so the field can be emptied and retyped freely. The value is applied on Enter
 * (or when the field loses focus): an empty or invalid entry goes back to the default,
 * and numbers are kept within the allowed range.
 */
export default function WindowDaysInput({ value, onCommit }) {
  const [draft, setDraft] = useState(String(value));

  // Keep the text in sync if the applied value changes from outside.
  useEffect(() => setDraft(String(value)), [value]);

  const commit = () => {
    const parsed = Number.parseInt(draft, 10);
    const next = Number.isNaN(parsed)
      ? DEFAULT_WINDOW_DAYS
      : Math.min(MAX_WINDOW_DAYS, Math.max(MIN_WINDOW_DAYS, parsed));
    setDraft(String(next));
    onCommit(next);
  };

  return (
    <input
      type="number"
      inputMode="numeric"
      min={MIN_WINDOW_DAYS}
      max={MAX_WINDOW_DAYS}
      value={draft}
      onChange={(e) => setDraft(e.target.value)}
      onBlur={commit}
      onKeyDown={(e) => {
        if (e.key === "Enter") commit();
      }}
    />
  );
}