# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Files in this repo

| File | Role |
|---|---|
| `rapport_performance.html` | Static performance report Jan–Jul 2026 — open directly in browser |
| `rapport_annuel.html` | Static multi-year bilan (2023–2026) — open directly in browser |
| `activities_store.json` | Source of truth: merged Strava activities from 6 May 2026 onward (id, name, description, sport_type, start_local, summary incl. `total_calories`) |
| `activities_pre_may2026.json` | Frozen `list_activities` dump covering 1 Jan – 3 May 2026 (100 activities). Loaded by `update_report.py` (`P1_PATH`) and merged with `activities_store.json` at report-build time — kept as a committed file, not a session tool-result, so it survives session cleanup. Static; never needs updating. |
| `activities_inbox.json` | Scratch file (gitignored) — paste a fresh `list_activities` MCP JSON dump here before running `update_report.py` |
| `update_report.py` | **Weekly update pipeline.** Merges `activities_inbox.json` into `activities_store.json`, recomputes every derived stat, and patches both HTML reports directly via regex. See "Weekly update workflow" below. |
| `update_map.py` | Reads raw GPS stream files, samples to 250–500 pts, writes `mapRoutes` into the HTML |
| `plan_inject.py` | One-shot script that injected the Plan Échappée Belle tab into the HTML |
| `marathon_inject.py` | One-shot script that injected the Plan Marathon NC tab into the HTML |
| `extract_calendar.py` / `extract_extra.py` | **Legacy, superseded by `update_report.py`.** Kept for reference only — do not use for weekly updates (their embedded `P2_JSON` blobs are no longer maintained). |
| `muscu_store.json` | Source of truth for strength-training detail: one entry per session (sets/reps/weight per exercise), fetched from the **Garmin Connect API** — not from the raw `.fit` file. See note below. |
| `update_muscu.py` | Fetches new `strength_training` activities via `garminconnect.Garmin.get_activity_exercise_sets()`, upserts them into `muscu_store.json` (keyed by Garmin activity id, skips sessions already `source:'garmin_api'`), and patches `const muscuSessions` in `rapport_performance.html`. Requires a saved session — see `garmin_login.py`. |
| `garmin_login.py` | Run manually (never by Claude) to authenticate with Garmin Connect — prompts for email/password/MFA via masked terminal input and saves a session token to `~/.garminconnect`. Re-run when the token expires. |
| `garmin_fetch_sets.py` | Debug utility — lists recent `strength_training` activities, or dumps the raw `exerciseSets` JSON for a given activity id. Not part of the regular pipeline. |

**Why the API, not the raw `.fit`:** the `.fit` exported from the watch (`Export Original`) contains the *pre-correction* auto-detected data — Garmin's on-device exercise/rep recognition is unreliable (confirmed by comparing both sources on a real session: the `.fit` showed vague/wrong exercise guesses and erratic rep counts, while `get_activity_exercise_sets()` returned 4 correctly identified exercises at 100% confidence with clean rep counts). Garmin Connect's server-side reprocessing is authoritative; don't reintroduce `.fit`-based parsing for exercise/rep data.

---

## rapport_performance.html

The main file being actively developed. Zero-build, single-file static report.

### Running

Open directly in browser — no server needed (no OAuth, no fetch calls at runtime).

### Architecture

One `<script>` block with all data embedded as JS constants, rendered on `DOMContentLoaded`.

**9 tabs** (toggled by `showTab(name)`):

| Tab id | Content |
|---|---|
| `global` | KPI cards, weekly volume (km + D+ + temps + temp + zones FC), CTL/ATL/TSB, ACWR, cadence, zones, heatmap, best efforts, W/kg, recommandations, résumé |
| `courses` | Competition table and FC/power chart per race |
| `entrainement` | Monthly calendar (6 grids), monthly stats table |
| `muscu` | Strength-training sessions: per-session sets/reps/weight, parsed from Garmin `.fit` files by `update_muscu.py` |
| `velo` | Cycling sessions (Ride/VirtualRide): KPI cards + table (distance, D+, durée, vitesse moy., calories), computed client-side from `veloSessions[]`. Deliberately excluded from run+trail volume/ACWR/CTL-ATL — cycling load isn't comparable to running load |
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
| `calActs[]` | One entry per activity `{d, t, km, dur, re, elev, n, race}` since Jan 1 2026 — regenerated in full every run by `update_report.py` (renames preserved via `NAME_OVERRIDES`) |
| `mapRoutes[]` | 15 GPS traces `{name, date, t, km, race, pts}` — written by `update_map.py` (5 decimal places, 250–500 pts each) |
| `muscuSessions[]` | One entry per strength-training session `{id, date, start_local, name, duration_s, calories, avg_hr, max_hr, exercises:[{category_name, sets:[{reps, weight, duration_s}]}], source}` — written by `update_muscu.py` from `muscu_store.json` (source: Garmin Connect API) |
| `veloSessions[]` | One entry per cycling activity (`Ride`/`VirtualRide`) `{id, date, start_local, name, km, elev, duration_s, avg_speed_kmh, calories, indoor}` (`indoor` = true for `VirtualRide`, e.g. MyWhoosh) — regenerated in full every run by `update_report.py` from `activities_store.json`, rendered in the `velo` tab (table badge + `wkVeloOutKm`/`wkVeloInKm` stacked bars + `wkVeloElev` D+ line on secondary axis, weekly chart) |
| `reData[]` | Weekly Relative Effort sum (all activity types) — used for CTL/ATL/TSB |
| `acwr[]` | Weekly ACWR (EWMA ATL/CTL, τ=7j/42j) on Relative Effort — history before the last published week is frozen; only the tail is recomputed/calibrated (see `compute_acwr()`) |
| `acwrDplus[]` | Same EWMA ACWR model as `acwr[]`, but on weekly D+ (`runElev+trailElev`) instead of Relative Effort — approximates eccentric/neuromuscular fatigue that RE-based ACWR misses (slow high-D+ hikes/trail score low RE but high muscular load). Computed by the same `compute_acwr()`, called a second time in `main()`; rendered in its own chart (`chart-acwr-dplus`) right under the RE-based ACWR chart |
| `weeks[]` | ISO week labels (Monday `dd/mm`), one per week from 29/12/2025 to the latest activity |
| `runKmOnly[]` / `trailKmOnly[]` / `runKm[]` | Weekly Run-only / Trail-only / Run+Trail km |
| `wkTimeH[]` | Weekly moving time in hours (Run+Trail only, excl. walks) |
| `runElev[]` / `trailElev[]` | Weekly run / trail elevation gain (m) |
| `totalElev[]` | Computed: `runElev.map((v,i) => v+trailElev[i])` |
| `wkCal[]` | Weekly total calories (all activity types, from real `total_calories`) |
| `wkMaxTemp[]` | Weekly max temperature (°C), auto-extracted from Enduraw description `"Heat (XX°C)"`, falling back to `KNOWN_TEMPS` for weeks predating description capture |

### Weekly update workflow

1. Fetch new activities: MCP `list_activities(range_start=<date after last update>)`.
2. Paste the raw JSON (`{"activities":[...]}`) into `activities_inbox.json`.
3. Run `python update_report.py` (add `--dry-run` to preview without writing).
   - Merges the inbox into `activities_store.json`, deduplicated by activity id.
   - Recomputes every derived stat (weekly arrays, ACWR, zones, heatmap, sports split, `calActs`, `veloSessions`, monthly 2026 breakdown) directly from real per-activity data — no manual arithmetic.
   - Patches both `rapport_performance.html` and `rapport_annuel.html` in place via regex, and prints a numeric summary (season totals, last 3 weeks, ACWR, J-countdowns to both races).
4. **The script does not touch narrative text.** Using the printed summary, manually update by hand:
   - ACWR badge text (`🟠`/`✅` spans near the ACWR chart), including the ACWR D+ badge below the second chart
   - Résumé exécutif (4-section card at the bottom of `global` tab)
   - Recommandations P1/P2/P3
5. If a new race happened, add its activity id to `RACES` in `update_report.py`.
6. If an activity needs a shorter/clearer display name in `calActs`, add it to `NAME_OVERRIDES` (keyed by activity id) rather than editing the HTML directly — the array is regenerated wholesale every run.

Historical weekly figures occasionally shift by small amounts (rounding, or a real correction like a previously under-counted week) when re-derived from source data — this is expected and more trustworthy than the old hand-accumulated numbers.

### Musculation update workflow

1. If the Garmin Connect session has expired (`update_muscu.py` raises an auth error), run `garmin_login.py` — **interactively, in the user's own terminal, never by Claude** (it prompts for the Garmin password).
2. Run `python update_muscu.py` (add `--dry-run` to preview). It fetches any new `strength_training` activity from Garmin Connect and patches `rapport_performance.html`. No manual file drop needed.

### Key conventions

- **No `destroyChart()`** — charts are created once on page load, never re-rendered.
- **JS strings with French text**: use `\'` to escape apostrophes in single-quoted strings (e.g. `d\'efficacité`), or the syntax error will silently break all charts.
- **Legend tooltips**: a global Chart.js plugin (`legendTip`) intercepts `onHover`/`onLeave` on all chart legends and shows `<div id="legend-tip">`. Add new labels to `LEGEND_TIPS` at the top of the script.
- **Map**: `initMap()` runs once when tab `carte` is first visited. `mapRoutes` colors: `#f59e0b` race · `#16a34a` trail · `#FC4C02` run.
- **`showTab(name)`** iterates `['global','courses','entrainement','carte','lexique','plan','marathon']`.
- **Temperature data** (`wkMaxTemp`): sourced from Enduraw description strings `"Heat (XX°C)"` via `extract_extra.py`, supplemented by `known_temps` dict for weeks without descriptions.
- **Strava `relative_effort` scale shift (2026-06-25)**: the raw `relative_effort` field returned by Strava for each activity dropped by a factor of ~7 starting 2026-06-25, coinciding with manual HR zone activation (FCmax=188bpm, see "Zones FC recalibrées" commit 2026-06-29). Weekly RE/h averaged ~175 before, ~23 after. The RE/hour-based HR-zone-distribution heuristics (`zoneSplit()` in the `chart-zones-week` IIFE, and `compute_zones()` in `update_report.py`) are **date-aware**: they use one threshold set before `RE_SCALE_SHIFT` (`2026-06-25`) and a rescaled set (÷7) after. If this ever needs re-tuning (e.g. after the next race establishes a real post-shift race-effort data point), adjust both `RE_SCALE_SHIFT`/`RE_SCALE_SHIFT_DATE` constants together — they must stay in sync between the HTML and the Python script.

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
