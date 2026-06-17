# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Files in this repo

| File | Role |
|---|---|
| `rapport_performance.html` | Static performance report Jan–Jun 2026 — open directly in browser |
| `extract_calendar.py` | Reads cached Strava data, outputs `calActs` JS array (134 activities) |
| `extract_extra.py` | Outputs cadence, heatmap, zone and CTL/ATL data for the report |
| `update_map.py` | Reads raw GPS stream files, samples to 250–500 pts, writes `mapRoutes` into the HTML |

---

## rapport_performance.html

The main file being actively developed. Zero-build, single-file static report.

### Running

Open directly in browser — no server needed (no OAuth, no fetch calls at runtime).

### Architecture

One `<script>` block with all data embedded as JS constants, rendered on `DOMContentLoaded`.

**5 tabs** (toggled by `showTab(name)`):

| Tab id | Content |
|---|---|
| `global` | KPI cards, weekly volume, CTL/ATL/TSB, ACWR, cadence, zones, heatmap, best efforts, W/kg, recommandations, résumé |
| `courses` | Competition table and FC/power chart per race |
| `entrainement` | Monthly calendar (6 grids), monthly stats table |
| `carte` | Leaflet map with 15 GPS traces |
| `lexique` | Definitions of CTL, ATL, TSB, ACWR, zones, cadence, etc. |

**CDN dependencies:**
- Tailwind CSS (utility styling)
- Chart.js 4.4.0 (bar, doughnut, line charts)
- Leaflet 1.9.4 (map — lazy-inited on first tab visit via `_mapInited` flag)

### Key data constants

| Constant | Description |
|---|---|
| `calActs[]` | 134 activities `{d, t, km, dur, re, elev, n, race}` — output of `extract_calendar.py` |
| `mapRoutes[]` | 15 GPS traces `{name, date, t, km, race, pts}` — written by `update_map.py` (5 decimal places, 250–500 pts each) |
| `reData[]` | Weekly Relative Effort for CTL/ATL/TSB calculation |
| `weeks[]` | 24 ISO week labels (29/12 → 08/06) |

### Key conventions

- **No `destroyChart()`** — charts are created once on page load, never re-rendered.
- **JS strings with French text**: use `\'` to escape apostrophes in single-quoted strings (e.g. `d\'efficacité`), or the syntax error will silently break all charts.
- **Legend tooltips**: a global Chart.js plugin (`legendTip`) intercepts `onHover`/`onLeave` on all chart legends and shows `<div id="legend-tip">`. Add new labels to `LEGEND_TIPS` at the top of the script.
- **Map**: `initMap()` runs once when tab `carte` is first visited. `mapRoutes` colors: `#f59e0b` race · `#16a34a` trail · `#FC4C02` run.
- **`showTab(name)`** iterates `['global','courses','entrainement','carte','lexique']`.

### GPS data pipeline

Raw streams are fetched via MCP `get_activity_streams` (no `resolution` param = full precision) and auto-saved to:
`C:\Users\lmiklic\.claude\projects\...\tool-results\mcp-claude_ai_Strava-get_activity_streams-<timestamp>.txt`

`update_map.py` reads those files, samples with `step = max(1, len(pts) // maxpts)`, rounds to 5 decimal places, and patches `const mapRoutes = [...]` in the HTML via regex.

