import { createElement } from "react";
 
// Colors for the dark theme. Keep in sync with the CSS variables in styles.css.
export const COLORS = {
  text: "#f4f6fb",
  muted: "#a9b4d0",
  grid: "#2b3558",
  surface: "#252f54",
  actual: "#f4f6fb",
  forecast: "#6fa8f7",
  corrected: "#5ccb7e",
  over: "#f2a93b", // forecast above the actual
  under: "#5cd6d0", // forecast below the actual
  raw: "#7d8aae",
  rmse: "#a78bfa",
};
 
export const axis = { stroke: COLORS.grid, tick: { fill: COLORS.muted, fontSize: 12 } };
export const grid = { stroke: COLORS.grid, strokeDasharray: "3 3" };
 
export const tooltip = {
  contentStyle: {
    background: COLORS.surface,
    border: `1px solid ${COLORS.grid}`,
    borderRadius: 10,
    color: COLORS.text,
  },
  labelStyle: { color: COLORS.muted },
  cursor: { stroke: COLORS.grid },
};
 
export const legend = {
  wrapperStyle: { paddingTop: 8 },
  formatter: (value) => createElement("span", { style: { color: COLORS.muted } }, value),
};