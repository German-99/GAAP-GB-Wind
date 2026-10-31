import { useEffect, useState } from "react";
import Accuracy from "./components/Accuracy";
import BiasCorrection from "./components/BiasCorrection";
import CutoffSensitivity from "./components/CutoffSensitivity";
import DeliveryDay from "./components/DeliveryDay";
import WindowDaysInput, { DEFAULT_WINDOW_DAYS } from "./components/WindowDaysInput";
import { hourLabel } from "./format";

// Same order as the sections on the page.
const NAV = [
  { href: "#accuracy", label: "Forecast accuracy" },
  { href: "#forecast", label: "Forecast at decision time" },
  { href: "#correction", label: "Bias correction" },
  { href: "#sensitivity", label: "Cutoff sensitivity" },
];

const PUBLICATIONS_NOTE =
  "Previous day. Observed publications: about 02:30, 04:30, 07:30, 09:30, 11:30, 12:30, 15:30, 18:30 and 22:30 UTC.";
const SOURCE_NOTE =
  "Data: Elexon BMRS datasets FUELHH (actuals) and WINDFOR (forecasts). Times in UTC (UK time equals UTC in January).";

function Turbine() {
  return (
    <svg viewBox="0 0 32 32" aria-hidden="true">
      <path d="M16 14 V29" stroke="#a9b4d0" strokeWidth="2" strokeLinecap="round" />
      <g stroke="#6fa8f7" strokeWidth="2.5" strokeLinecap="round">
        <path d="M16 14 L16 3" />
        <path d="M16 14 L25.5 19.5" />
        <path d="M16 14 L6.5 19.5" />
      </g>
      <circle cx="16" cy="14" r="2.2" fill="#f4f6fb" />
    </svg>
  );
}

function MenuIcon({ open }) {
  return (
    <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" className="menu-icon">
      {open ? <path d="M6 6 L18 18 M18 6 L6 18" /> : <path d="M4 7 H20 M4 12 H20 M4 17 H20" />}
    </svg>
  );
}

export default function App() {
  const [cutoffHour, setCutoffHour] = useState(9);
  const [windowDays, setWindowDays] = useState(DEFAULT_WINDOW_DAYS);
  // On small screens the section links live in a menu that opens from a button.
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    if (!menuOpen) return undefined;
    const onKey = (e) => e.key === "Escape" && setMenuOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [menuOpen]);

  return (
    <div className="shell">
      <aside className={`sidebar${menuOpen ? " menu-open" : ""}`}>
        <div className="brand">
          <Turbine />
          <div className="brand-text">
            <strong>Wind forecast</strong>
            <span>GB day-ahead buying</span>
          </div>
          <button
            type="button"
            className="menu-button"
            aria-label={menuOpen ? "Close menu" : "Open menu"}
            aria-expanded={menuOpen}
            aria-controls="site-nav"
            onClick={() => setMenuOpen((open) => !open)}
          >
            <MenuIcon open={menuOpen} />
          </button>
        </div>

        <nav id="site-nav" className="nav" aria-label="Sections">
          {NAV.map((item) => (
            <a key={item.href} href={item.href} onClick={() => setMenuOpen(false)}>
              {item.label}
            </a>
          ))}
          <p className="hint menu-note">{PUBLICATIONS_NOTE}</p>
        </nav>

        {/* On phones the controls stay visible at the top, outside the menu. */}
        <div className="controls">
          <label>
            <span className="label-row">
              Decision cutoff <strong>{hourLabel(cutoffHour)} UTC</strong>
            </span>
            <input
              type="range"
              min="0"
              max="24"
              step="0.5"
              value={cutoffHour}
              onChange={(e) => setCutoffHour(Number(e.target.value))}
            />
            <span className="hint">{PUBLICATIONS_NOTE}</span>
          </label>
          <label>
            <span className="label-row">Bias window (days)</span>
            <WindowDaysInput value={windowDays} onCommit={setWindowDays} />
            <span className="hint">1 to 28 days. Press Enter to apply.</span>
          </label>
        </div>

        <p className="hint source">{SOURCE_NOTE}</p>
      </aside>

      {menuOpen && <div className="backdrop" onClick={() => setMenuOpen(false)} />}

      <div className="content">
        <header className="page-head">
          <h1>Wind forecast accuracy for day-ahead buying</h1>
          <p>
            National wind generation in Great Britain: forecasts available at decision time vs
            actuals, January 2026.
          </p>
        </header>

        <main className="dashboard">
          <Accuracy cutoffHour={cutoffHour} />
          <DeliveryDay cutoffHour={cutoffHour} windowDays={windowDays} />
          <BiasCorrection cutoffHour={cutoffHour} windowDays={windowDays} />
          <CutoffSensitivity />
        </main>

        <footer className="hint page-foot">{SOURCE_NOTE}</footer>
      </div>
    </div>
  );
}