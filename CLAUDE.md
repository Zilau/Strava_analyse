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
| `update_report.py` | **Weekly update pipeline.** Merges `activities_inbox.json` into `activities_store.json`, recomputes every derived stat, and patches both HTML reports directly via regex. See "Weekly update workflow" below. Also holds `MARATHON_PACE_KM`, a manual dict (same spirit as `NAME_OVERRIDES`/`RACES`) mapping activity id → km identified at marathon-goal pace or faster. |
| `update_map.py` | Reads raw GPS stream files, samples to 250–500 pts, writes `mapRoutes` into the HTML |
| `plan_inject.py` | One-shot script that injected the Plan Échappée Belle tab into the HTML |
| `marathon_inject.py` | One-shot script that injected the Plan Marathon NC tab into the HTML |
| `extract_calendar.py` / `extract_extra.py` | **Legacy, superseded by `update_report.py`.** Kept for reference only — do not use for weekly updates (their embedded `P2_JSON` blobs are no longer maintained). |
| `hr_store.json` | Per-activity performance data fetched via MCP `get_activity_performance` (HR, power and best efforts are **not** in `list_activities`): `{id: {avg_hr, max_hr, avg_watts, best: {'400m','1k','5k','10k'} (seconds)}}`. Covers easy flat runs (→ `effRuns[]`) and quality sessions/long runs/races (→ `perfRuns[]`). ETP 120 and Échappée Belle deliberately not fetched (mountain ultras, huge payloads, irrelevant for 400 m–10 km bests). |
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
| `global` | Organised in 4 blocks with section headers: **1 · Où j'en suis** (`status-strip` dashboard built from `STATUS`, résumé exécutif, recommandations, KPI cards) · **2 · Charge & risque** (CTL/ATL/TSB + monotonie, `chart-re` = weekly load coloured by ACWR — the former standalone ACWR chart was merged into it —, ACWR D+) · **3 · Progression** (efficacité aérobie, économie de course, best efforts 400 m/1 km and 5/10 km, W/kg in races, records table) · **4 · Comment je m'entraîne** (volume, zones FC + distribution d'intensité, cadence + répartition, heatmap folded in a `<details>`) |
| `courses` | KPI cards + `comp-table` (one row per race, built at runtime from `calActs` `race:true` joined with `perfRuns` by date, enriched by the hand-maintained `RACE_INFO` {name, official time, result} and `NEXT_RACE`; intensity = avg HR as % of FCmax 188) · `chart-comp-power` (W/kg vs race duration, log-log fit on races < 15 m D+/km, extrapolated to ~3h55 for a marathon power target) · 10 km pacing card (`chart-comp-splits` + `chart-comp-fcwatts`, hardcoded per-km data) |
| `entrainement` | All generated at runtime by `renderCalendar()` from `calActs` (months up to the latest activity, no hardcoded list). Each run/trail is classified by `classify()` (name regex + km + D+/km) into footing / qualité / sortie longue / D+ montagne / rando / course → `chart-session-mix` (weekly km stacked by type) + `mix-status` verdicts on the last 28 days · `cal-stats` monthly table (most recent first: km, km/sem, D+, heures, longest run, counts per type, vélo, muscu, days without running) · calendars with cell colour = main session type and a Σ weekly-km column; last 3 months shown, older ones in a `<details>` |
| `muscu` | Strength-training sessions: per-session sets/reps/weight, parsed from Garmin `.fit` files by `update_muscu.py` |
| `velo` | Cycling sessions (Ride/VirtualRide): KPI cards + table (distance, D+, durée, vitesse moy., calories), computed client-side from `veloSessions[]`. Deliberately excluded from run+trail volume/ACWR/CTL-ATL — cycling load isn't comparable to running load |
| `carte` | Leaflet map with 15 GPS traces |
| `lexique` | Definitions of CTL, ATL, TSB, ACWR, zones, cadence, etc. |
| `plan` | Plan Maratrail de l'Échappée Belle — 42km D+2500m · 22 août 2026 |
| `marathon` | Plan Marathon Nice-Cannes — 42.195km · 8 novembre 2026 |

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
| `acwr[]` | Weekly ACWR (EWMA acute τ=7 j / chronic τ=42 j) computed by `compute_acwr()` on `reAdj` = weekly Relative Effort with the ×7 correction after `RE_SCALE_SHIFT_DATE`, seeded on the mean of the first 4 weeks. Fully recomputed every run (the former frozen-history/calibrated variant on raw RE read 0.2–0.5 all summer and 4.0 in week 1). Drives the bar colours of `chart-re` and the dashboard |
| `acwrDplus[]` | Same EWMA ACWR model as `acwr[]` (seeded, no calibration), on weekly D+ (`runElev+trailElev`) — approximates eccentric/neuromuscular fatigue that RE-based ACWR misses (slow high-D+ hikes/trail score low RE but high muscular load). Rendered in `chart-acwr-dplus` |
| `weeks[]` | ISO week labels (Monday `dd/mm`), one per week from 29/12/2025 to the latest activity |
| `runKmOnly[]` / `trailKmOnly[]` / `runKm[]` | Weekly Run-only / Trail-only / Run+Trail km |
| `wkTimeH[]` | Weekly moving time in hours (Run+Trail only, excl. walks) |
| `runElev[]` / `trailElev[]` | Weekly run / trail elevation gain (m) |
| `totalElev[]` | Computed: `runElev.map((v,i) => v+trailElev[i])` |
| `wkCal[]` | Weekly total calories (all activity types, from real `total_calories`) |
| `wkMaxTemp[]` | Weekly max temperature (°C), auto-extracted from Enduraw description `"Heat (XX°C)"`, falling back to `KNOWN_TEMPS` for weeks predating description capture |
| `wkEfficiency[]` | Weekly km per unit of RE-adjusted Relative Effort, **flat running only** (`Run`/`TrailRun` with < 15 m D+/km, races in `RACES` excluded — trail/hike and max efforts inflate RE/km and would read as a regression; `flatKm / flatReAdj`, `null` if no qualifying run that week) — a fully-automatic "course economy" proxy (more km for the same physiological cost = improving). RE is rescaled ×7 for activities after `RE_SCALE_SHIFT_DATE` so the ratio stays comparable across the whole season (see scale-shift note below) — this rescaled sum is separate from `reData[]` and never touches the ACWR anchor logic. Rendered in the `global` tab (`chart-course-economy`, right under the RE trend chart) with a 4-week rolling mean and the season median as reference. Caveat: the ratio also drops in weeks heavy on intervals, so it partly reflects intensity mix |
| `effRuns[]` | One entry per easy flat run with HR `{d, n, ef, hr, pace}` — `ef` = Efficiency Factor (speed m/min ÷ avg HR). Selection: `Run`/`TrailRun` ≥ 6 km, < 15 m D+/km, not in `RACES`/`MARATHON_PACE_KM`, name/description not matching `EASY_EXCLUDE`, and `max_hr` < 165 (hidden accelerations). Regenerated every run from `hr_store.json`; rendered in `chart-efficiency` with a 5-run rolling mean vs season median |
| `perfRuns[]` | One entry per run with performance data in `hr_store.json` `{d, n, race, trail, km, elev, w, hr, b400, b1k, b5k, b10k}` — regenerated by `update_report.py`. Feeds `chart-be-speed` / `chart-be-endurance` (monthly best per distance, race points in orange), `chart-wkg` (avg power ÷ 86 kg on races) and the `be-table` records table (season record vs best of the last 60 days) |
| `STATUS` | JS object declared at the top of the script; each chart registers its verdict `{label, val, txt, color}` (forme, charge, dplus, eff, eco, cad, be, race) and the `Tableau de bord` IIFE (just before `chart-zones-week`) renders them in `#status-strip`. Add a key when a new indicator should appear in the dashboard |
| `wkMarathonPaceKm[]` | Weekly km identified in activity descriptions as run at marathon-goal pace or faster, from the manual `MARATHON_PACE_KM` dict in `update_report.py` — 0 for any week not manually tagged. Tracking starts at the current marathon block (post-Échappée Belle, 24 Aug 2026 onward); the rest of the season is deliberately left at 0, not retro-tagged. Rendered in the `marathon` tab (`chart-marathon-pace`, last 12 weeks only) |

### Weekly update workflow

1. Fetch new activities: MCP `list_activities(range_start=<date after last update>)`.
2. Paste the raw JSON (`{"activities":[...]}`) into `activities_inbox.json`.
3. Run `python update_report.py` (add `--dry-run` to preview without writing).
   - Merges the inbox into `activities_store.json`, deduplicated by activity id.
   - Recomputes every derived stat (weekly arrays, ACWR, zones, heatmap, sports split, `calActs`, `veloSessions`, monthly 2026 breakdown) directly from real per-activity data — no manual arithmetic.
   - Patches both `rapport_performance.html` and `rapport_annuel.html` in place via regex, and prints a numeric summary (season totals, last 3 weeks, ACWR, J-countdowns to both races).
4. **The script does not touch narrative text.** Using the printed summary, manually update by hand:
   - ACWR badge text (`🟠`/`✅` spans under `chart-re`, "Charge hebdomadaire & ACWR"), including the ACWR D+ badge below `chart-acwr-dplus`
   - Résumé exécutif (4-section card at the bottom of `global` tab)
   - Recommandations P1/P2/P3
5. If a new race happened, add its activity id to `RACES` in `update_report.py`, and an entry keyed by date in `RACE_INFO` (readable name, official time `h:mm:ss`, result text) in `rapport_performance.html` — without it the row still appears, with the raw Strava name and moving time. Fetch its `get_activity_performance` too (step 9) so HR/power show up in the table and the power-duration fit.
6. If an activity needs a shorter/clearer display name in `calActs`, add it to `NAME_OVERRIDES` (keyed by activity id) rather than editing the HTML directly — the array is regenerated wholesale every run.
7. For each new activity, check whether its description mentions a segment run at the current marathon-goal pace (5:41/km as of Sep 2026) or faster (an explicitly named semi/10km-pace segment counts too). If so, estimate the km and add an entry to `MARATHON_PACE_KM` before running the script. Ambiguous segments (short intervals without a stated pace) don't count. This feeds `wkMarathonPaceKm[]` — see "Key data constants" above.
8. If the summary prints `⚠ FC manquante pour N footing(s)`, call MCP `get_activity_performance` for each listed id, add `{avg_hr, max_hr, avg_watts, best}` to `hr_store.json`, and re-run the script. Easy flat runs without HR are simply left out of `effRuns[]` until then.
9. Same for `⚠ Best efforts manquants pour N séance(s)` (fractionnés, sorties longues, courses since `PERF_TRACK_FROM`): fetch `get_activity_performance`, store `{avg_hr, max_hr, avg_watts, best: {'400m','1k','5k','10k'}}` (seconds, from `best_efforts`), re-run. Feeds `perfRuns[]`.

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

Multi-year bilan (2023–2026), same light-theme design system as `rapport_performance.html` (white cards, slate palette, `#FC4C02` Strava-orange accents). Zero-build, single-file, opened directly in browser. Mostly edited by hand; `update_report.py` patches the 2026 KPIs, `DATA[2026]`, the 2026 monthly table footer and `AS_OF`.

### Architecture

One `<script>` block, data embedded as JS constants, rendered on `DOMContentLoaded`.

- **Year tabs**: `showYear(yr)` toggles between 2023 / 2024 / 2025 / 2026 sections (2026 marked "en cours" / partial year).
- **Sub-tabs per year** (`showSubTab(name)`): `recap` (Vue d'ensemble), `courses`, `mensuel` — plus a cross-year `synthese` tab.
- Charts are lazy-inited per year via `_chartsInited[yr]`, and the synthèse tab via `_syntheseInited`.
- Opens on the **Synthèse** tab (`showSubTab('synthese')` at the end of the script); clicking a sub-tab from the synthèse returns to `currentYear` (default 2026).

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
| `AS_OF` | Date of the latest 2026 activity (`'YYYY-MM-DD'`) — **patched by `update_report.py`** (`annuel-AS_OF`). Drives every "à date" comparison: past years are cut at the same day, with the current month prorated |
| `READ{2023..2026}` | One-sentence hand-written reading of each year, rendered at the top of its recap (`read_{yr}`) |

### Chart types per year (`initCharts(yr)`)

| Canvas id | Chart |
|---|---|
| `chartMixed_{yr}` | Stacked Run/Trail km bars (rounded, asymmetric `borderRadius`) + Séances line on `yAxisID:'y2'` + avg-km annotation line |
| `chartElev_{yr}` | Same rounded-bar pattern for monthly D+ + avg-D+ annotation line |
| `profile_{yr}` (HTML, not a chart) | Run/Trail split bars for km and D+, plus km/sem, h/sem, D+/km (replaced the former polar chart and the two doughnuts) |
| `chartTime_{yr}` | Monthly hours, line with canvas-gradient fill |
| `chartRaces_{yr}` | Rounded horizontal bars, one per race, tooltip shows distance/D+/time/DNF |

### Synthèse tab (`initSynthese()`)

| Element | Content |
|---|---|
| `ytd-cards` | km / D+ / heures / séances of each year at `AS_OF`, with the 2026 delta vs 2025 at the same date |
| `synthCumKm` / `synthCumDp` | Cumulative km / D+ from Jan 1 (x = day of year), plus a dashed 2026 projection = YTD + mean of what 2023–2025 did after the same date (`proj-km` / `proj-dp` badges) |
| `recur-table` | Races run in several years (matched by regex in `RECUR`), compared on pace only between finished editions of similar distance (±10 %), pacer runs (`pacer` in the name) excluded |
| `years-table` | 4-year table with arrows vs the previous year — for 2026, totals vs 2025 at the same date, ratios vs full 2025; D+/km and part trail shown in neutral grey |
| `synthKmLine` / `synthDpLine` | Built by `mkLine()` — monthly lines per year, 2026 dashed |

Race times in `RACES` accept `'XhYY'`, `'NNmin'` or `'mm:ss'` (parsed by `raceSec()` for the pace column and the recurring-race comparison). Race-table footers (`race-foot-{yr}`) are computed at runtime.

### Key conventions

- 2026 (partial year) is always visually distinguished with `borderDash:[6,3]` — apply this to any new dataset that includes 2026.
- `Chart.defaults.plugins.tooltip.*` and `Chart.defaults.animation.*` are set globally near the top of the script — new charts inherit them automatically, no per-chart tooltip styling needed unless overriding.
- No `destroyChart()` — same as `rapport_performance.html`, charts are created once and never re-rendered.
