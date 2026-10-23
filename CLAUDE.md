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
| `update_report.py` | **Weekly update pipeline.** Merges `activities_inbox.json` into `activities_store.json`, recomputes every derived stat, and patches both HTML reports directly via regex. See "Weekly update workflow" below. Also holds `MARATHON_PACE_KM`, a manual dict (same spirit as `NAME_OVERRIDES`/`RACES`) mapping activity id → km at marathon-goal pace or faster. Since 20 Oct 2026 it only overrides the automatic lap-based detection (`marathon_pace_km()`). |
| `update_map.py` | Reads raw GPS stream files, samples to 250–500 pts, writes `mapRoutes` into the HTML |
| `plan_inject.py` | One-shot script that injected the Plan Échappée Belle tab into the HTML. The tab has since been removed (race done), so this script is legacy and must not be re-run. |
| `marathon_inject.py` | One-shot script that injected the Plan Marathon NC tab into the HTML |
| `extract_calendar.py` / `extract_extra.py` | **Legacy, superseded by `update_report.py`.** Kept for reference only — do not use for weekly updates (their embedded `P2_JSON` blobs are no longer maintained). |
| `hr_store.json` | Per-activity performance data fetched via MCP `get_activity_performance` (HR, power and best efforts are **not** in `list_activities`): `{id: {avg_hr, max_hr, avg_watts, best: {'400m','1k','5k','10k'} (seconds), laps: [[distance_m, moving_time_s, avg_hr], ...]}}`. Covers easy flat runs (→ `effRuns[]`) and quality sessions/long runs/races (→ `perfRuns[]`). `laps` are present for every session of the marathon block (since 28 Aug 2026) and feed `wkMarathonPaceKm[]` and `mpLaps[]`. Store all laps, including short recoveries — the filter (≥ 1 km, ≤ 5:41/km) is applied by the script. ETP 120 and Échappée Belle deliberately not fetched (mountain ultras, huge payloads, irrelevant for 400 m–10 km bests). |
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

**8 tabs** (toggled by `showTab(name)`). The nav groups the buttons: Plan Marathon NC (the current objective, outlined via `.tab-goal`) · Analyse (global, courses, entrainement) · Autres sports (muscu, velo) · Ressources (carte, lexique) · ↗ Bilan annuel. `showTab` only toggles `tab-active`, so extra classes on a button survive:

| Tab id | Content |
|---|---|
| `global` | Organised in 4 blocks with section headers (`<h3 class="sec-h">`, sentence case, no numbering): **Où j'en suis** (`race-hero` countdown + course ruler, `taper` frieze "D'ici le départ" — weekly target km until race day, same 90 % / −30 % / −50 % hypothesis as the race-day form projection, applied to the mean run+trail km of the last 3 complete weeks, removed once the race is past —, `status-strip` indicator table built from `STATUS`, résumé exécutif, recommandations, KPI cards) · **Charge & risque** (CTL/ATL/TSB + race-day form projection + monotonie, `chart-re` = weekly load coloured by ACWR — the former standalone ACWR chart was merged into it —, ACWR D+; every "current" verdict reads the last complete week, the in-progress week is drawn pale) · **Progression** (efficacité aérobie, économie de course, best efforts 400 m/1 km and 5/10 km, W/kg in races, records table) · **Comment je m'entraîne** (volume, zones FC + distribution d'intensité, cadence + répartition, heatmap folded in a `<details>`) |
| `courses` | `comp-kpi` summary card (computed title: race count, best road pace, then best road pace / max W/kg / marathon power target) + `comp-table` (one row per race, built at runtime from `calActs` `race:true` joined with `perfRuns` by date, enriched by the hand-maintained `RACE_INFO` {name, official time, result} and `NEXT_RACE`; intensity = avg HR as % of FCmax 188) · `chart-comp-power` (W/kg vs race duration, log-log fit on races < 15 m D+/km, extrapolated to ~3h55 for a marathon power target) · 10 km pacing card (`chart-comp-splits` + `chart-comp-fcwatts`, hardcoded per-km data) |
| `entrainement` | `train-sum` summary card on top (current month vs previous one: km, km/sem, qualité, sorties longues, D+, jours sans course, from the same `stats` as `cal-stats`). All generated at runtime by `renderCalendar()` from `calActs` (months up to the latest activity, no hardcoded list). Each run/trail is classified by `classify()` (name regex + km + D+/km) into footing / qualité / sortie longue / D+ montagne / rando / course (palette in `TYPES`; blues for road sessions from light to dark (footing → sortie longue → qualité in ink), greens for D+ / rando, orange only for races) → `chart-session-mix` (weekly km stacked by type) + `mix-status` verdicts on the last 28 days · `cal-stats` monthly table (most recent first: km, km/sem, D+, heures, longest run, counts per type, vélo, muscu, days without running) · calendars with cell colour = main session type and a Σ weekly-km column; last 3 months shown, older ones in a `<details>` |
| `muscu` | `muscu-sum` summary card (session count, days since the last one, total sets, most-worked muscle groups via `MUSCLE_FR`) + per-session sets/reps/weight from `muscuSessions[]`, fetched from the Garmin Connect API by `update_muscu.py`. Body schema shaded with `MUSCLE_RAMP` (grey → report blue) |
| `velo` | Cycling sessions (Ride/VirtualRide): summary card in `velo-kpis` (computed title: rides and km vs running km, last ride) + table (distance, D+, durée, vitesse moy., calories), computed client-side from `veloSessions[]`. Deliberately excluded from run+trail volume/ACWR/CTL-ATL — cycling load isn't comparable to running load |
| `carte` | Leaflet map with the GPS traces of `mapRoutes` (January–June 2026, refreshed only by running `update_map.py` by hand) |
| `lexique` | Definitions of CTL, ATL, TSB, ACWR, zones, cadence, etc. A `Sommaire` nav card on top links to the 5 section cards (`lex-charge`, `lex-risque`, `lex-monotonie`, `lex-physio`, `lex-course`) and lists their terms |
| `marathon` | Plan Marathon Nice-Cannes — 42.195km · 8 novembre 2026 : countdown, `chart-marathon-pace` (last 12 weeks: wide bar = run+trail km coloured by ACWR with the `chart-re` thresholds, in-progress week pale; narrow overlaid bar = km at marathon pace), `chart-mp-hr` (lap HR at marathon pace, normalised to 5:30/km), plan adherence, week-by-week plan. The `mara-*` values (target time and pace from `NEXT_RACE.target`, gap to the 10 km record from `RACE_INFO['2026-06-14']` + `calActs`, longest run since `blockFrom`, HR estimated at 5:35 from the `chart-mp-hr` fit) are computed at load. The « Point clé », the session types, the vigilance list and the S1–S11 plan (`planWeeks`, kept as the original plan) are hand-written |

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
| `STATUS` | JS object declared at the top of the script; each chart registers its verdict `{label, val, txt, color, series}` (forme, charge, dplus, mp, eff, eco, cad, be). `series` is optional, and its last 12 points draw a sparkline. `mp` (weekly marathon-pace km) is only shown while `NEXT_RACE` is upcoming. The `Tableau de bord` IIFE (just before `chart-zones-week`) renders them in `#status-strip` as a table titled "Où en est la forme", one row per indicator. A `txt` of the form `'Tag — détail'` is split into a coloured tag and plain text. To add an indicator, add its key to the IIFE's order list and to `UNITS` |
| `NEXT_RACE` | `{d, n, km, target, from, to, blockFrom}` — drives every countdown and the `#race-hero` card at the top of `global`. That card shows the day count, the target time and pace split from `target` `'time (pace)'`, and a ruler from `from` to `to` over `km`. On the ruler: the longest non-race run since `blockFrom` (from `calActs`), and the session with the most marathon-pace km (laps of `mpLaps` summed by date + name, drawn at the end of that run). The card is removed once the race date has passed. Update `NEXT_RACE`, including `blockFrom`, when the next objective changes |
| `wkMarathonPaceKm[]` | Weekly km run at marathon-goal pace or faster, from `marathon_pace_km()` in `update_report.py`. It uses `MARATHON_PACE_KM` (manual, takes precedence) or else the laps in `hr_store.json`. Tracking starts at the current marathon block (post-Échappée Belle, 24 Aug 2026 onward); the rest of the season is deliberately left at 0, not retro-tagged. Rendered in the `marathon` tab (`chart-marathon-pace`, last 12 weeks only) |
| `mpLaps[]` | One entry per lap ≥ 1 km run at ≤ 5:41/km since `MP_LAPS_FROM` (24 Aug 2026), races excluded: `{d, n, km, pace (s/km), hr}`. Built by `compute_mp_laps()` from the `laps` in `hr_store.json`, which every session of the block has. Rendered in the `marathon` tab as `chart-mp-hr`. The chart normalises each session's lap HR to 5:30/km, using a slope fitted on all laps (falls back to −0.4 bpm per s/km if out of range), and plots a 4-session rolling mean. `mp-hr-status` compares the last 3 weeks with the start of the block and estimates the HR at 5:35 |

The `chart-ctl` status (`ctl-status`) also carries a **race-day form projection**. It extends CTL/ATL from the last complete week up to the race week of `NEXT_RACE`, assuming a load of 90 % of the 3-week mean, then −30 %, then −50 % in race week (marathon itself excluded). In the current week, the actual load is used when it already exceeds the plan.

### Weekly update workflow

1. Fetch new activities: MCP `list_activities(range_start=<date after last update>)`.
2. Paste the raw JSON (`{"activities":[...]}`) into `activities_inbox.json`.
3. Run `python update_report.py` (add `--dry-run` to preview without writing).
   - Merges the inbox into `activities_store.json`, deduplicated by activity id.
   - Recomputes every derived stat (weekly arrays, ACWR, zones, heatmap, sports split, `calActs`, `veloSessions`, monthly 2026 breakdown) directly from real per-activity data — no manual arithmetic.
   - Patches both `rapport_performance.html` and `rapport_annuel.html` in place via regex, and prints a numeric summary: season totals, last 3 weeks (the in-progress one flagged provisional), the last complete week's ACWR / ACWR D+ / economy / marathon-pace km, and countdowns to upcoming races only.
4. **The script does not touch narrative text.** Using the printed summary, manually update by hand:
   - Résumé exécutif (4-section card at the bottom of `global` tab)
   - Recommandations P1/P2/P3

   No longer by hand: the current-week ACWR / ACWR D+ / forme / économie badges (`re-status`, `dplus-status`, `ctl-status`, `eco-status`) are generated at runtime on the **last complete week**, the in-progress week is shown pale and labelled provisional. The hand badges under `chart-re` are only for notable historical peaks. Every race countdown derives from `NEXT_RACE` via `RACE_DAYS`/`RACE_J`. In narrative text, wrap a countdown in `<span class="j-race">J-xx</span>` and it is rewritten on load, so never hardcode a bare `J-xx`.
5. If a new race happened, add its activity id to `RACES` in `update_report.py`, and an entry keyed by date in `RACE_INFO` (readable name, official time `h:mm:ss`, result text) in `rapport_performance.html` — without it the row still appears, with the raw Strava name and moving time. Fetch its `get_activity_performance` too (step 9) so HR/power show up in the table and the power-duration fit.
6. If an activity needs a shorter/clearer display name in `calActs`, add it to `NAME_OVERRIDES` (keyed by activity id) rather than editing the HTML directly — the array is regenerated wholesale every run.
7. Marathon-pace km are detected automatically since 20 Oct 2026 (`LAPS_TRACK_FROM`): `marathon_pace_km()` sums the laps ≥ 1 km run at ≤ `MP_PACE_S` (341 s = 5:41/km) stored under `laps` in `hr_store.json`. If the summary prints `⚠ Laps manquants`, fetch `get_activity_performance` and store `laps: [[distance_m, moving_time_s, avg_hr], ...]`. Add an entry to `MARATHON_PACE_KM` only to override the detection, e.g. when 1 km auto-laps on a footing produce false positives, or a segment was not split into its own lap. Entries in that dict always take precedence, and all pre-20 Oct activities rely on it. This feeds `wkMarathonPaceKm[]` — see "Key data constants" above.
8. If the summary prints `⚠ FC manquante pour N footing(s)`, call MCP `get_activity_performance` for each listed id, add `{avg_hr, max_hr, avg_watts, best}` to `hr_store.json`, and re-run the script. Easy flat runs without HR are simply left out of `effRuns[]` until then.
9. Same for `⚠ Best efforts manquants pour N séance(s)` (fractionnés, sorties longues, courses since `PERF_TRACK_FROM`): fetch `get_activity_performance`, store `{avg_hr, max_hr, avg_watts, best: {'400m','1k','5k','10k'}, laps}` (best in seconds, from `best_efforts`; `laps` as in step 7), re-run. Feeds `perfRuns[]`.

Historical weekly figures occasionally shift by small amounts (rounding, or a real correction like a previously under-counted week) when re-derived from source data — this is expected and more trustworthy than the old hand-accumulated numbers.

### Musculation update workflow

1. If the Garmin Connect session has expired (`update_muscu.py` raises an auth error), run `garmin_login.py` — **interactively, in the user's own terminal, never by Claude** (it prompts for the Garmin password).
2. Run `python update_muscu.py` (add `--dry-run` to preview). It fetches any new `strength_training` activity from Garmin Connect and patches `rapport_performance.html`. No manual file drop needed.

### Key conventions

- **Visual style** (shared with `rapport_annuel.html`): Archivo font (Google Fonts, also `Chart.defaults.font.family`), `BLUE` = `#1C6E8C` / `SKY` = `#5E98AD` for data series, ink `#102A3A` for headings, orange `#FC4C02` reserved for races and the objective. Every tab uses light `.card`s, including `marathon`, which used to be dark. Labels are in sentence case: no `uppercase tracking-*` and no emoji in headings, labels or badges. Exceptions: `★` stays as a calendar marker (max session, race day), and a race is flagged in text with `(course)` / `Course :`. Verdict colours: good = blue `#1C6E8C` (not green, so verdicts stay readable with red–green colour blindness), caution = amber, alert = red, neutral = grey. Green means trail / D+ only. The HR-zone scale (Z1 blue → Z5 red) is a continuous scale, not a verdict, and keeps its own colours. Each tab opens with a `.card` summary (`.sum-h` computed title + `.sum-grid` of `.sum-val`). Global chart titles are phrased as the question the chart answers. The verdict itself comes from the computed badges, never from a hard-coded title.
- **No `destroyChart()`** — charts are created once on page load, never re-rendered.
- **JS strings with French text**: use `\'` to escape apostrophes in single-quoted strings (e.g. `d\'efficacité`), or the syntax error will silently break all charts.
- **Legend tooltips**: a global Chart.js plugin (`legendTip`) intercepts `onHover`/`onLeave` on all chart legends and shows `<div id="legend-tip">`. Add new labels to `LEGEND_TIPS` at the top of the script.
- **Map**: `initMap()` runs once when tab `carte` is first visited. `mapRoutes` colours come from `colorOf()`: `#FC4C02` race · `#3E6B4B` trail · `#1C6E8C` road.
- **`showTab(name)`** iterates `['global','courses','entrainement','muscu','velo','carte','lexique','marathon']`. Add the id there when adding a tab.
- **Race countdowns**: never hardcode a `J-xx`. `RACE_DAYS` / `RACE_J`, declared right after `NEXT_RACE`, count from today. Narrative text uses `<span class="j-race">`, which is rewritten on load.
- **Partial week**: `RE_ADJ.partial` is true when the latest activity is not a Sunday. Status badges and `STATUS` verdicts then read index `length-2`, and the last bar or point is drawn pale (`#94a3b8`). Charts created before `RE_ADJ` exists (e.g. `chart-acwr-dplus`) are patched afterwards via `Chart.getChart()`.
- **Temperature data** (`wkMaxTemp`): sourced from Enduraw description strings `"Heat (XX°C)"` by `extract_temp()` in `update_report.py`, supplemented by its `KNOWN_TEMPS` dict for weeks without descriptions.
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
- **Sub-tabs per year** (`showSubTab(name)`): `recap` (Vue d'ensemble), `courses`, `mensuel`, in the `#subtabs` row, which is hidden on the synthèse. The cross-year `synthese` view is a top-level button (`btn-synthese`, styled like the year buttons) placed before the years.
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
| `READ{2023..2026}` | One-sentence hand-written reading of each year (no emoji, `<strong>` title). Rendered at the top of its recap (`read_{yr}`) and in the synthèse small multiples |
| `GOAL` | `{y, date:'dd/mm', name, dist}` — upcoming objective drawn as an orange ring on the synthèse race calendar while its date is after `AS_OF`. Hand-maintained, keep in sync with `NEXT_RACE` in `rapport_performance.html` |
| `YR_COLORS` | One hue, darker for recent years (2023 light blue → 2026 ink `#102A3A`). Table headers show the year colour as an underline, not as text colour (the light shades fail text contrast) |

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
| `syn-title` / `ytd-table` / `ytd-delta` | Hero of the synthèse. The title is computed from the rank of 2026 in km at `AS_OF` ("a déjà dépassé…" or "est deuxième…, derrière …"), never hand-written. The table gives km / D+ / heures / séances of each year at `AS_OF`, and a sentence gives the 2026 delta vs 2025 at the same date |
| `synthCumKm` / `synthCumDp` | Cumulative km (in the hero) / D+ (folded in a `<details>`) from Jan 1 (x = day of year). No legend: the `endLabels` plugin writes year + total at the end of each line. 2026 is a thick solid ink line ending on an orange dot, the deliberate exception to the 2026-dashed rule, since the line already stops at `AS_OF`. Grey dashed segment = 2026 projection (YTD + mean of what 2023–2025 did after the same date), explained in `proj-km` / `proj-dp` |
| `sm-grid` | "Quatre saisons, même échelle": one column per year, monthly run (`#1C6E8C`) + trail (`#7FA88A`) stacked bars on a scale shared by all years, totals, part trail, races/DNF, `READ[yr]`, and a button calling `showYear(yr)` |
| `race-tl` | "Où tombent les courses": one row per year, each race placed at its day of year, size ∝ √distance, colour by `fmt` (Run / Trail / Ultra), hollow = DNF. The longest finished race of each year is named, plus `GOAL` |
| `recur-table` | Races run in several years (matched by regex in `RECUR`), compared on pace only between finished editions of similar distance (±10 %), pacer runs (`pacer` in the name) excluded |
| `years-table` | 4-year table with arrows vs the previous year — for 2026, totals vs 2025 at the same date, ratios vs full 2025; D+/km and part trail shown in neutral grey |
| `synthKmLine` / `synthDpLine` | Built by `mkLine()` — monthly lines per year, 2026 dashed |

Race times in `RACES` accept `'XhYY'`, `'NNmin'` or `'mm:ss'` (parsed by `raceSec()` for the pace column and the recurring-race comparison). Race-table footers (`race-foot-{yr}`) are computed at runtime.

### Key conventions

- 2026 (partial year) is always visually distinguished with `borderDash:[6,3]` — apply this to any new dataset that includes 2026. Exception: the cumulative charts, where 2026 is solid and thick (see `synthCumKm`).
- The synthèse uses the Archivo font (also the Chart.js default font) and the same blue/green/ink palette as the top of `rapport_performance.html`, with orange reserved for the current position and the objective.
- `Chart.defaults.plugins.tooltip.*` and `Chart.defaults.animation.*` are set globally near the top of the script — new charts inherit them automatically, no per-chart tooltip styling needed unless overriding.
- No `destroyChart()` — same as `rapport_performance.html`, charts are created once and never re-rendered.
