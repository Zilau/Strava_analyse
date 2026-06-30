# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Files in this repo

| File | Role |
|---|---|
| `rapport_performance.html` | Static performance report Jan–Jun 2026 — open directly in browser |
| `rapport_annuel.html` | Static multi-year bilan (2023–2026) — open directly in browser |
| `extract_calendar.py` | Reads cached Strava data, outputs `calActs` JS array (141 activities) |
| `extract_extra.py` | Outputs cadence, heatmap, zone, CTL/ATL, temperature and weekly volume data |
| `update_map.py` | Reads raw GPS stream files, samples to 250–500 pts, writes `mapRoutes` into the HTML |
| `plan_inject.py` | One-shot script that injected the Plan Échappée Belle tab into the HTML |
| `marathon_inject.py` | One-shot script that injected the Plan Marathon NC tab into the HTML |

---

## rapport_performance.html

The main file being actively developed. Zero-build, single-file static report.

### Running

Open directly in browser — no server needed (no OAuth, no fetch calls at runtime).

### Architecture

One `<script>` block with all data embedded as JS constants, rendered on `DOMContentLoaded`.

**7 tabs** (toggled by `showTab(name)`):

| Tab id | Content |
|---|---|
| `global` | KPI cards, weekly volume (km + D+ + temps + temp + zones FC), CTL/ATL/TSB, ACWR, cadence, zones, heatmap, best efforts, W/kg, recommandations, résumé |
| `courses` | Competition table and FC/power chart per race |
| `entrainement` | Monthly calendar (6 grids), monthly stats table |
| `carte` | Leaflet map with 15 GPS traces |
| `lexique` | Definitions of CTL, ATL, TSB, ACWR, zones, cadence, etc. |
| `plan` | Plan Maratrail de l'Échappée Belle — 42km D+2500m · 22 août 2026 |
| `marathon` | Plan Marathon Nice-Cannes — 42.195km · 25 octobre 2026 |

**CDN dependencies:**
- Tailwind CSS (utility styling)
- Chart.js 4.4.0 (bar, doughnut, line charts)
- Leaflet 1.9.4 (map — lazy-inited on first tab visit via `_mapInited` flag)

### Key data constants

| Constant | Description |
|---|---|
| `calActs[]` | 141 activities `{d, t, km, dur, re, elev, n, race}` — Jan 1 → Jun 28 2026 |
| `mapRoutes[]` | 15 GPS traces `{name, date, t, km, race, pts}` — written by `update_map.py` (5 decimal places, 250–500 pts each) |
| `reData[]` | 26 weekly Relative Effort values for CTL/ATL/TSB calculation |
| `acwr[]` | 26 weekly ACWR values (current week RE / chronic 28j average) |
| `weeks[]` | 26 ISO week labels (29/12 → 22/06) |
| `runKmOnly[]` | 26 weekly Run-only km |
| `trailKmOnly[]` | 26 weekly Trail-only km |
| `runKm[]` | 26 weekly Run+Trail km combined |
| `wkTimeH[]` | 26 weekly moving time in hours (Run+Trail only, excl. walks) |
| `runElev[]` | 26 weekly run elevation gain (m) |
| `trailElev[]` | 26 weekly trail elevation gain (m) |
| `totalElev[]` | Computed: `runElev.map((v,i) => v+trailElev[i])` |
| `wkCal[]` | 26 weekly total calories (all activity types) |
| `wkMaxTemp[]` | 26 weekly max temperature (°C, from Enduraw descriptions — null if unavailable) |

### Adding a new activity (weekly update workflow)

When new Strava activities come in, update **all** of the following in `rapport_performance.html`:

1. `calActs[]` — add entry `{d, t, km, dur, re, elev, n, race}` at end
2. `reData[last]` — add current week's RE to last slot (or append new week)
3. `acwr[last]` — recompute: current RE / mean(previous 4 weeks RE)
4. `wkCal[last]` — add calories (total_calories from MCP)
5. `runKm[last]` / `runKmOnly[last]` / `trailKmOnly[last]` — add distance per type
6. `wkTimeH[last]` — add moving_time / 3600
7. `trailElev[last]` or `runElev[last]` — add elevation_gain
8. Header subtitle (line ~47): update date, activité count, séance count
9. KPI cards: distance totale (km) and dénivelé cumulé (m)
10. Kcal total (line ~95)
11. Donut h2 count (line ~131), heatmap h2 count (line ~239)
12. ACWR badge (line ~109): date, ACWR value, J-countdown
13. Résumé paragraph (line ~397): séances, km, D+, J-countdown
14. Footer (line ~714): activité count, date
15. Sync `extract_calendar.py` and `extract_extra.py` P2_JSON + `weekly_re`

### Key conventions

- **No `destroyChart()`** — charts are created once on page load, never re-rendered.
- **JS strings with French text**: use `\'` to escape apostrophes in single-quoted strings (e.g. `d\'efficacité`), or the syntax error will silently break all charts.
- **Legend tooltips**: a global Chart.js plugin (`legendTip`) intercepts `onHover`/`onLeave` on all chart legends and shows `<div id="legend-tip">`. Add new labels to `LEGEND_TIPS` at the top of the script.
- **Map**: `initMap()` runs once when tab `carte` is first visited. `mapRoutes` colors: `#f59e0b` race · `#16a34a` trail · `#FC4C02` run.
- **`showTab(name)`** iterates `['global','courses','entrainement','carte','lexique','plan','marathon']`.
- **Temperature data** (`wkMaxTemp`): sourced from Enduraw description strings `"Heat (XX°C)"` via `extract_extra.py`, supplemented by `known_temps` dict for weeks without descriptions.

### GPS data pipeline

Raw streams are fetched via MCP `get_activity_streams` (no `resolution` param = full precision) and auto-saved to:
`C:\Users\lmiklic\.claude\projects\...\tool-results\mcp-claude_ai_Strava-get_activity_streams-<timestamp>.txt`

`update_map.py` reads those files, samples with `step = max(1, len(pts) // maxpts)`, rounds to 5 decimal places, and patches `const mapRoutes = [...]` in the HTML via regex.

---

## rapport_annuel.html

Multi-year bilan (2023–2026), same light-theme design system as `rapport_performance.html` (white cards, slate palette, `#FC4C02` Strava-orange accents). Zero-build, single-file, opened directly in browser. Not generated by any script — edited by hand.

### Architecture

One `<script>` block, data embedded as JS constants, rendered on `DOMContentLoaded`.

- **Year tabs**: `showYear(yr)` toggles between 2023 / 2024 / 2025 / 2026 sections (2026 marked "en cours" / partial year).
- **Sub-tabs per year** (`showSubTab(name)`): `recap` (Vue d'ensemble), `courses`, `mensuel` — plus a cross-year `synthese` tab.
- Charts are lazy-inited per year via `_chartsInited[yr]`, and the synthèse tab via `_syntheseInited`.

**CDN dependencies:**
- Tailwind CSS
- Chart.js 4.4.0 + `chartjs-plugin-annotation@3.0.1` (avg-km / avg-D+ reference lines)

### Key data constants

| Constant | Description |
|---|---|
| `MONTHS` | 12 French month abbreviations, shared across years |
| `DATA{2023..2026}` | Monthly `runKm`/`trailKm`/`runElev`/`trailElev`/`sessions`/`timeH` arrays + `sub` summary string + `lowSessions` + `partial` flag (2026 only) |
| `RACES{2023..2026}` | Race objects: `date`, `name`, `dist`, `elev`, `time`, `fmt`, `dnf` |
| `NOTES{2023..2026}` | Per-month annotation text |
| `POLAR_COLORS` | Seasonal palette (winter indigo → summer orange/red → autumn amber) for the monthly polar-area chart |

### Chart types per year (`initCharts(yr)`)

| Canvas id | Chart |
|---|---|
| `chartMixed_{yr}` | Stacked Run/Trail km bars (rounded, asymmetric `borderRadius`) + Séances line on `yAxisID:'y2'` + avg-km annotation line |
| `chartElev_{yr}` | Same rounded-bar pattern for monthly D+ + avg-D+ annotation line |
| `chartPolar_{yr}` | Monthly polar area, `POLAR_COLORS`, `startAngle:-Math.PI/2` |
| `chartSplitKm_{yr}` / `chartSplitElev_{yr}` | Run vs Trail doughnut, custom `doughnutCenter()` plugin draws total + label in the middle |
| `chartTime_{yr}` | Monthly hours, line with canvas-gradient fill |
| `chartRaces_{yr}` | Rounded horizontal bars, one per race, tooltip shows distance/D+/time/DNF |

### Synthèse tab (`initSynthese()`)

| Canvas id | Chart |
|---|---|
| `synthRadar` | Normalized (0–100) radar comparing years; 2026 uses `borderDash:[6,3]` (partial year) |
| `synthKm` / `synthDp` | Rounded stacked bars, Run+Trail per year |
| `synthKmLine` / `synthDpLine` / `synthSess` | Built by `mkLine()` factory — monthly lines per year, 2026 dashed, white-bordered points, light fill |

### Key conventions

- `doughnutCenter(line1Fn, line2)` is a plugin **factory** (not a global plugin) — pass a fresh instance per chart via `plugins:[...]` so multiple doughnuts can show different units.
- 2026 (partial year) is always visually distinguished with `borderDash:[6,3]` — apply this to any new dataset that includes 2026.
- `Chart.defaults.plugins.tooltip.*` and `Chart.defaults.animation.*` are set globally near the top of the script — new charts inherit them automatically, no per-chart tooltip styling needed unless overriding.
- No `destroyChart()` — same as `rapport_performance.html`, charts are created once and never re-rendered.
