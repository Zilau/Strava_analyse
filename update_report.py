"""
Pipeline de mise à jour hebdomadaire des rapports Strava.

Usage :
  1. Récupérer les nouvelles activités : mcp list_activities(range_start=<depuis dernière maj>)
  2. Coller le JSON brut ({"activities":[...]}) dans activities_inbox.json
  3. Lancer : python update_report.py
     -> merge activities_inbox.json dans activities_store.json (dédoublonné par id)
     -> recalcule toutes les stats dérivées
     -> patche rapport_performance.html et rapport_annuel.html
     -> imprime un résumé pour rédiger le texte narratif (résumé exécutif,
        badge ACWR, recommandations) à la main

Ce script NE touche PAS :
  - le texte narratif (résumé exécutif, badges ACWR, recommandations P1/P2/P3)
  - les noms d'activités déjà personnalisés dans NAME_OVERRIDES
Ces sections restent une rédaction manuelle, informée par le résumé imprimé en fin de script.
"""
import sys, json, re, math, shutil, unicodedata
from datetime import datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).parent
P1_PATH   = ROOT / 'activities_pre_may2026.json'
STORE_PATH  = ROOT / 'activities_store.json'
INBOX_PATH  = ROOT / 'activities_inbox.json'
HTML_PERF   = ROOT / 'rapport_performance.html'
HTML_ANNUEL = ROOT / 'rapport_annuel.html'
BACKUP_DIR  = ROOT / 'backup'

RACES = {'18912947563', '18448862987', '18725084836', '17248882168', '17810798563', '19854851888', '20148273211'}

# Renommages manuels conservés lors de la régénération de calActs (désambiguïsation / clarté)
NAME_OVERRIDES = {
    '19094984083': 'Un peu de D+ (début prépa Échappée Belle)',
    '19177786747': 'Accompagnement Pierre 100km (1)',
    '19179461024': 'Accompagnement Pierre 100km (2)',
    '19180241862': 'Accompagnement Pierre 100km (3)',
    '18632222472': 'Un peu de D+ Gravelle',
    '18698621123': 'Boucle du dredi midi',
    '18820391514': 'Séance Trail Gravelle',
}

# Températures connues pour les semaines sans description Enduraw exploitable (avant mai 2026)
# Km courus à allure marathon (objectif sub-4h, 5:41/km) ou plus rapide, identifiés
# manuellement dans la description de chaque activité. Démarre au bloc marathon actuel
# (28/08/2026, post-Échappée Belle) — pas de rétro-tagging de la saison antérieure.
MARATHON_PACE_KM = {
    '19939788054': 4.4,   # 28/08 Fractionné long — 2x12' à 5'30 (plus rapide que 5:41 cible)
    '19959802255': 5.3,   # 30/08 Sortie longue — 30' à allure marathon
    '20037252948': 6.0,   # 04/09 Fractionné long — 3000m marathon + 2000m semi + 1000m 10km
}

KNOWN_TEMPS = {
    '04/05': 20.0, '11/05': 20.0, '18/05': 28.9, '25/05': 30.5,
    '01/06': 19.4, '08/06': 20.1, '15/06': 32.1, '22/06': 35.7, '29/06': 25.7,
}

SPORT_MAP = {
    'Run': 'Run', 'TrailRun': 'Trail', 'Hike': 'Trail', 'Walk': 'Marche',
    'Ride': 'Vélo', 'VirtualRide': 'Vélo',
    'WeightTraining': 'Muscu', 'Workout': 'Muscu', 'Yoga': 'Yoga',
}
SPORT_ORDER = ['Run', 'Trail', 'Marche', 'Vélo', 'Muscu', 'Yoga']
# Hike (randonnée) compte comme charge run+trail : en prépa montagne (Chartreuse), les rando
# génèrent du D+/temps/fatigue neuromusculaire comparables au trail — les exclure sous-estimait
# le volume et l'ACWR D+ des semaines à forte proportion de rando (ex. semaine du 27/07 : D+ réel
# 7041 m vs 5714 m compté). Groupées avec TrailRun (terrain, allure) plutôt que Run.
RUN_TRAIL = ('Run', 'TrailRun', 'Hike')

MONTHS = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun', 'Jul', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc']
TEMP_RE = re.compile(r'Heat \((\d+\.?\d*)°C\)|temperature was (\d+\.?\d*)°C')


# ── CHARGEMENT / MERGE ──────────────────────────────────────────────

def load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def backup_file(path, dest_dir):
    if path.exists():
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / f"{path.stem}.{datetime.now():%Y%m%d_%H%M%S}{path.suffix}"
        shutil.copy2(path, dest)
        return dest
    return None


def merge_inbox():
    """Fusionne activities_inbox.json dans activities_store.json (dédoublonné par id)."""
    store = load_json(STORE_PATH) if STORE_PATH.exists() else []
    by_id = {a['id']: a for a in store}
    added = 0
    if INBOX_PATH.exists():
        raw = load_json(INBOX_PATH)
        new_acts = raw['activities'] if isinstance(raw, dict) else raw
        if not isinstance(new_acts, list):
            raise ValueError('activities_inbox.json doit contenir un tableau ou un objet avec la clé "activities".')
        for a in new_acts:
            if a['id'] not in by_id:
                by_id[a['id']] = a
                added += 1
    merged = sorted(by_id.values(), key=lambda a: a['start_local'])
    with open(STORE_PATH, 'w', encoding='utf-8') as f:
        json.dump(merged, f, ensure_ascii=False, indent=1)
    return merged, added


def load_all_activities():
    p1 = load_json(P1_PATH)['activities']
    store = load_json(STORE_PATH)
    by_id = {a['id']: a for a in (p1 + store)}
    return sorted(by_id.values(), key=lambda a: a['start_local'])


# ── HELPERS ──────────────────────────────────────────────────────────

def week_monday(dt):
    d = dt.date() if isinstance(dt, datetime) else dt
    return d - timedelta(days=d.weekday())


def extract_temp(desc):
    if not desc:
        return None
    m = TEMP_RE.search(desc)
    if not m:
        return None
    return float(m.group(1) or m.group(2))


def clean_name(name):
    name = unicodedata.normalize('NFC', name)
    name = name.replace('"', "'")
    return re.sub(r'[^\x00-\x7FÉÀÈÙÂÊÎÔÛÇŒÆËÏÜéàèùâêîôûçœæëïü\w\s\'\-\(\)\.\,\/]', '', name).strip()


# ── CALCULS DÉRIVÉS ──────────────────────────────────────────────────

def compute_weekly(all_acts):
    dts = [datetime.fromisoformat(a['start_local']) for a in all_acts]
    start_m, end_m = week_monday(min(dts)), week_monday(max(dts))
    week_list = []
    d = start_m
    while d <= end_m:
        week_list.append(d)
        d += timedelta(days=7)

    B = {w: dict(runKm=0.0, runKmOnly=0.0, trailKmOnly=0.0, wkTimeH=0.0, runElev=0, trailElev=0,
                 wkCal=0, reData=0, cadSum=0.0, cadN=0, temp=None, veloOutKm=0.0, veloInKm=0.0, veloElev=0,
                 veloWattsSum=0.0, veloWattsN=0, mpKm=0.0, reAdjSum=0.0) for w in week_list}

    for a in all_acts:
        dt = datetime.fromisoformat(a['start_local'])
        wm = week_monday(dt)
        if wm not in B:
            continue
        b = B[wm]
        s = a.get('summary', {})
        km = s.get('distance', 0) / 1000
        mt = s.get('moving_time', 0) or 0
        elev = s.get('elevation_gain', 0) or 0
        re_ = s.get('relative_effort') or 0
        cal = s.get('total_calories') or 0
        cad = s.get('avg_cadence') or 0
        st = a['sport_type']

        b['wkCal'] += cal
        b['reData'] += re_

        if st in RUN_TRAIL:
            b['runKm'] += km
            b['wkTimeH'] += mt / 3600
            if st == 'Run':
                b['runKmOnly'] += km
                b['runElev'] += elev
            else:
                b['trailKmOnly'] += km
                b['trailElev'] += elev
            if cad:
                b['cadSum'] += cad
                b['cadN'] += 1
            t = extract_temp(a.get('description'))
            if t is not None:
                b['temp'] = max(b['temp'] or 0, t)
            b['mpKm'] += MARATHON_PACE_KM.get(a['id'], 0)
            re_adj = re_ * (7 if a['start_local'][:10] >= RE_SCALE_SHIFT_DATE else 1)
            b['reAdjSum'] += re_adj
        elif st == 'Ride':
            b['veloOutKm'] += km
            b['veloElev'] += elev
            if s.get('avg_watts'):
                b['veloWattsSum'] += s['avg_watts']
                b['veloWattsN'] += 1
        elif st == 'VirtualRide':
            b['veloInKm'] += km
            b['veloElev'] += elev
            if s.get('avg_watts'):
                b['veloWattsSum'] += s['avg_watts']
                b['veloWattsN'] += 1

    labels = [w.strftime('%d/%m') for w in week_list]
    for w, lbl in zip(week_list, labels):
        if B[w]['temp'] is None and lbl in KNOWN_TEMPS:
            B[w]['temp'] = KNOWN_TEMPS[lbl]

    return {
        'weeks':        labels,
        'runKm':        [round(B[w]['runKm'], 1) for w in week_list],
        'runKmOnly':    [round(B[w]['runKmOnly'], 1) for w in week_list],
        'trailKmOnly':  [round(B[w]['trailKmOnly'], 1) for w in week_list],
        'wkTimeH':      [round(B[w]['wkTimeH'], 2) for w in week_list],
        'runElev':      [int(round(B[w]['runElev'])) for w in week_list],
        'trailElev':    [int(round(B[w]['trailElev'])) for w in week_list],
        'wkCal':        [int(round(B[w]['wkCal'])) for w in week_list],
        'reData':       [int(round(B[w]['reData'])) for w in week_list],
        'wkMaxTemp':    [B[w]['temp'] for w in week_list],
        'wkCadence':    [round(B[w]['cadSum'] / B[w]['cadN'], 1) if B[w]['cadN'] else None for w in week_list],
        'wkVeloOutKm':  [round(B[w]['veloOutKm'], 1) for w in week_list],
        'wkVeloInKm':   [round(B[w]['veloInKm'], 1) for w in week_list],
        'wkVeloElev':   [int(round(B[w]['veloElev'])) for w in week_list],
        'wkVeloWatts':  [round(B[w]['veloWattsSum'] / B[w]['veloWattsN'], 1) if B[w]['veloWattsN'] else None for w in week_list],
        'wkMarathonPaceKm': [round(B[w]['mpKm'], 1) for w in week_list],
        'wkEfficiency': [round(B[w]['runKm'] / B[w]['reAdjSum'], 3) if B[w]['reAdjSum'] else None for w in week_list],
    }


def compute_acwr(reData_new, old_acwr, old_reData):
    """Continuation calibrée : fige l'historique déjà publié, ne recalcule/ajuste que la queue."""
    kATL, kCTL = math.exp(-7 / 7), math.exp(-7 / 42)
    ATL = CTL = 0.0
    raw = []
    for re_ in reData_new:
        ATL = ATL * kATL + re_ * (1 - kATL)
        CTL = CTL * kCTL + re_ * (1 - kCTL)
        raw.append(ATL / CTL if CTL else 0.0)

    n_old = len(old_acwr)
    if n_old == 0 or n_old > len(reData_new):
        return [round(x, 2) for x in raw]

    anchor = n_old - 1
    while anchor > 0 and (anchor >= len(reData_new) or reData_new[anchor] != old_reData[anchor]):
        anchor -= 1
    scale = (old_acwr[anchor] / raw[anchor]) if raw[anchor] else 1.0

    result = list(old_acwr[:anchor])
    for i in range(anchor, len(reData_new)):
        result.append(round(raw[i] * scale, 2))
    return result


# Strava's raw relative_effort dropped ~7x starting 2026-06-25 (coincides with manual HR zone
# activation, FCmax=188bpm — see "Zones FC recalibrées" commit 2026-06-29). Weekly RE/h averaged
# ~175 before, ~23 after. Thresholds below are scaled accordingly per period.
RE_SCALE_SHIFT_DATE = '2026-06-25'


def compute_zones(all_acts):
    hours = {'Z1-Z2': 0.0, 'Z2-Z3': 0.0, 'Z4': 0.0, 'Z5': 0.0}
    for a in all_acts:
        if a['sport_type'] not in RUN_TRAIL:
            continue
        s = a['summary']
        re_, mt = s.get('relative_effort') or 0, s.get('moving_time') or 0
        if not re_ or not mt:
            continue
        h = mt / 3600
        reph = re_ / h
        recent = a['start_local'][:10] >= RE_SCALE_SHIFT_DATE
        t1, t2, t3 = (19, 29, 40) if recent else (130, 200, 280)
        z = 'Z1-Z2' if reph < t1 else 'Z2-Z3' if reph < t2 else 'Z4' if reph < t3 else 'Z5'
        hours[z] += h
    total = sum(hours.values())
    pct = {k: round(v / total * 100) for k, v in hours.items()} if total else {k: 0 for k in hours}
    return hours, pct, total


def compute_heatmap(all_acts):
    hm = [[0] * 4 for _ in range(7)]
    for a in all_acts:
        if a['sport_type'] not in RUN_TRAIL:
            continue
        dt = datetime.fromisoformat(a['start_local'])
        day, hour = dt.weekday(), dt.hour
        if 6 <= hour < 10: slot = 0
        elif 10 <= hour < 14: slot = 1
        elif 14 <= hour < 18: slot = 2
        elif 18 <= hour < 22: slot = 3
        else: continue
        hm[day][slot] += 1
    return hm


def compute_sports(all_acts):
    sess = {k: 0 for k in SPORT_ORDER}
    km = {k: 0.0 for k in SPORT_ORDER}
    hrs = {k: 0.0 for k in SPORT_ORDER}
    for a in all_acts:
        t = SPORT_MAP.get(a['sport_type'])
        if t not in sess:
            continue
        s = a['summary']
        sess[t] += 1
        km[t] += s.get('distance', 0) / 1000
        hrs[t] += (s.get('moving_time', 0) or 0) / 3600
    return ([sess[k] for k in SPORT_ORDER],
            [round(km[k], 1) for k in SPORT_ORDER],
            [round(hrs[k], 1) for k in SPORT_ORDER])


def compute_calacts(all_acts):
    out = []
    for a in all_acts:
        t = SPORT_MAP.get(a['sport_type'], a['sport_type'])
        s = a.get('summary', {})
        km = round(s.get('distance', 0) / 1000, 1)
        mt = s.get('moving_time', 0) or 0
        re_ = int(s.get('relative_effort') or 0)
        elev = int(s.get('elevation_gain', 0) or 0)
        h, m = mt // 3600, (mt % 3600) // 60
        dur = f"{h}h{m:02d}" if h else f"{m}min"
        name = NAME_OVERRIDES.get(a['id'], clean_name(a['name']))
        out.append({'d': a['start_local'][:10], 't': t, 'km': km, 'dur': dur,
                     're': re_, 'elev': elev, 'n': name, 'race': a['id'] in RACES,
                     'hike': a['sport_type'] == 'Hike'})
    return out


def compute_velo_sessions(all_acts):
    out = []
    for a in all_acts:
        if a['sport_type'] not in ('Ride', 'VirtualRide'):
            continue
        s = a.get('summary', {})
        mt = s.get('moving_time', 0) or 0
        km = s.get('distance', 0) / 1000
        out.append({
            'id': a['id'], 'date': a['start_local'][:10], 'start_local': a['start_local'],
            'name': NAME_OVERRIDES.get(a['id'], clean_name(a['name'])),
            'km': round(km, 1), 'elev': int(s.get('elevation_gain', 0) or 0),
            'duration_s': mt, 'avg_speed_kmh': round(km / (mt / 3600), 1) if mt else 0,
            'calories': int(s.get('total_calories', 0) or 0),
            'indoor': a['sport_type'] == 'VirtualRide',
            'avg_watts': round(s['avg_watts'], 1) if s.get('avg_watts') else None,
        })
    return out


def compute_monthly_2026(all_acts):
    runKm = [0.0] * 12; trailKm = [0.0] * 12
    runElev = [0] * 12; trailElev = [0] * 12
    sessions = [0] * 12; timeH = [0.0] * 12
    for a in all_acts:
        dt = datetime.fromisoformat(a['start_local'])
        if dt.year != 2026 or a['sport_type'] not in RUN_TRAIL:
            continue
        i = dt.month - 1
        s = a['summary']
        km = s.get('distance', 0) / 1000
        elev = s.get('elevation_gain', 0) or 0
        h = (s.get('moving_time', 0) or 0) / 3600
        sessions[i] += 1
        timeH[i] += h
        if a['sport_type'] == 'Run':
            runKm[i] += km; runElev[i] += elev
        else:
            trailKm[i] += km; trailElev[i] += elev
    last = max([i for i in range(12) if sessions[i] > 0], default=0)
    n = last + 1
    return {
        'runKm': [round(v, 1) for v in runKm[:n]], 'trailKm': [round(v, 1) for v in trailKm[:n]],
        'runElev': [int(round(v)) for v in runElev[:n]], 'trailElev': [int(round(v)) for v in trailElev[:n]],
        'sessions': sessions[:n], 'timeH': [round(v, 1) for v in timeH[:n]],
    }


# ── SERIALISATION JS ─────────────────────────────────────────────────

def js_array(values):
    parts = []
    for v in values:
        if v is None: parts.append('null')
        elif isinstance(v, bool): parts.append('true' if v else 'false')
        elif isinstance(v, str): parts.append(f"'{v}'")
        else: parts.append(str(v))
    return '[' + ','.join(parts) + ']'


def serialize_calacts(entries):
    lines = []
    for e in entries:
        n_json = json.dumps(e['n'], ensure_ascii=False)
        race = 'true' if e['race'] else 'false'
        hike = 'true' if e['hike'] else 'false'
        lines.append(f"  {{d:'{e['d']}',t:'{e['t']}',km:{e['km']},dur:'{e['dur']}',"
                      f"re:{e['re']},elev:{e['elev']},n:{n_json},race:{race},hike:{hike}}}")
    return 'const calActs = [\n' + ',\n'.join(lines) + '\n];'


def serialize_velo(entries):
    lines = []
    for e in entries:
        n_json = json.dumps(e['name'], ensure_ascii=False)
        indoor = 'true' if e['indoor'] else 'false'
        watts = e['avg_watts'] if e['avg_watts'] is not None else 'null'
        lines.append(f"  {{id:'{e['id']}',date:'{e['date']}',start_local:'{e['start_local']}',name:{n_json},"
                      f"km:{e['km']},elev:{e['elev']},duration_s:{e['duration_s']},"
                      f"avg_speed_kmh:{e['avg_speed_kmh']},calories:{e['calories']},indoor:{indoor},avg_watts:{watts}}}")
    return 'const veloSessions = [\n' + ',\n'.join(lines) + '\n];'


# ── PATCHING HTML ────────────────────────────────────────────────────

def read_const_array(html, name):
    m = re.search(rf'const {name}\s*=\s*(\[.*?\]);', html)
    return json.loads(m.group(1)) if m else None


def sub_or_die(html, pattern, replacement, label, flags=0, count=1):
    new_html, n = re.subn(pattern, replacement, html, count=count, flags=flags)
    if n == 0:
        raise RuntimeError(f'Pattern non trouvé : {label}')
    return new_html


def patch_performance_html(html, all_acts, weekly, calacts, velo_sessions, zones_hours, zones_pct, zones_total_h,
                            heatmap, sports, last_date_str, next_races):
    total_acts = len(all_acts)
    rt_acts = [a for a in all_acts if a['sport_type'] in RUN_TRAIL]
    rt_sessions = len(rt_acts)
    total_km = sum(a['summary'].get('distance', 0) for a in rt_acts) / 1000
    total_elev = sum(a['summary'].get('elevation_gain', 0) or 0 for a in rt_acts)
    total_kcal = sum(a['summary'].get('total_calories', 0) or 0 for a in all_acts)

    # 1. Header
    html = sub_or_die(html,
        r'<p class="text-sm text-slate-500">Laurent Miklic · 1 janv\. → .*?</p>',
        f'<p class="text-sm text-slate-500">Laurent Miklic · 1 janv. → {last_date_str} 2026 · '
        f'{total_acts} activités · Run+Trail : {rt_sessions} séances</p>',
        'header')

    # 2. KPI distance / D+
    html = sub_or_die(html,
        r'(<div class="metric-lbl">Distance totale \(run\+trail\)</div>\s*<div class="metric-val">)[^<]+(</div>)',
        lambda m: f'{m.group(1)}{round(total_km):,} km'.replace(',', ' ') + m.group(2), 'kpi-distance')
    html = sub_or_die(html,
        r'(<div class="metric-lbl">Dénivelé cumulé</div>\s*<div class="metric-val">)[^<]+(</div>)',
        lambda m: f'{m.group(1)}{round(total_elev):,} m'.replace(',', ' ') + m.group(2), 'kpi-elev')

    # 3. Calories caption
    html = sub_or_die(html,
        r'(total saison : <strong>)[^<]+(</strong>)',
        lambda m: f'{m.group(1)}{round(total_kcal):,} kcal'.replace(',', ' ') + m.group(2), 'kcal-caption')

    # 4. Répartition activités (h2 + texte %)
    html = sub_or_die(html,
        r'(<h2>Répartition des activités — )\d+( activités</h2>)',
        lambda m: f'{m.group(1)}{total_acts}{m.group(2)}', 'sports-h2')
    sess, kmS, hrsS = sports
    idx_trail = SPORT_ORDER.index('Trail')
    pct_sess_trail = round(sess[idx_trail] / sum(sess) * 100)
    pct_h_trail = round(hrsS[idx_trail] / sum(hrsS) * 100)
    html = sub_or_die(html,
        r"(Le trail pèse moins en nombre de séances \()\d+( %\) qu'en temps de mouvement \()\d+( %\)\.)",
        lambda m: f'{m.group(1)}{pct_sess_trail}{m.group(2)}{pct_h_trail}{m.group(3)}', 'sports-pct')
    html = sub_or_die(html, r'const sportActuals = \[.*?\];',
        'const sportActuals = [\n  ' + js_array(sess) + ',\n  ' + js_array(kmS) + ',\n  ' + js_array(hrsS) + ',\n];',
        'sportActuals', flags=re.DOTALL)

    # 5. Heatmap (h2, texte pattern, hm JS, total colonne)
    total_seances_hm = sum(sum(row) for row in heatmap)
    html = sub_or_die(html,
        r'(<h2>Heatmap des entraînements — Jour × Créneau horaire \()\d+( séances Run\+Trail\)</h2>)',
        lambda m: f'{m.group(1)}{rt_sessions}{m.group(2)}', 'heatmap-h2')
    dim_matin = heatmap[6][0]
    html = sub_or_die(html,
        r"(Dimanche matin = séance longue principale \()\d+(×\))",
        lambda m: f'{m.group(1)}{dim_matin}{m.group(2)}', 'heatmap-dim')
    html = sub_or_die(html, r'const hm = \[.*?\];',
        'const hm = [' + ','.join(js_array(row) for row in heatmap) + '];', 'heatmap-hm')
    html = sub_or_die(html,
        r'(font-weight:800;color:#374151">)\d+(</td>)',
        lambda m: f'{m.group(1)}{total_seances_hm}{m.group(2)}', 'heatmap-total')

    # 6. Zones FC (panneau HTML + doughnut JS)
    h12, h23, h4, h5 = zones_hours['Z1-Z2'], zones_hours['Z2-Z3'], zones_hours['Z4'], zones_hours['Z5']
    p12, p23, p4, p5 = zones_pct['Z1-Z2'], zones_pct['Z2-Z3'], zones_pct['Z4'], zones_pct['Z5']
    html = sub_or_die(html, r'(font-size:18px;font-weight:700;color:#1e293b;line-height:1">)\d+(h</div>)',
        lambda m: f'{m.group(1)}{round(zones_total_h)}{m.group(2)}', 'zones-total-h')
    html = sub_or_die(html,
        r'(Z1–Z2 Endurance</span>\s*<span style="font-size:12px;color:#64748b">)[\d.]+(h · <strong>)\d+(%</strong>)',
        lambda m: f'{m.group(1)}{h12:.1f}{m.group(2)}{p12}{m.group(3)}', 'zones-panel-z12', flags=re.S)
    html = sub_or_die(html,
        r'(background:#16a34a;width:)\d+(%;height:100%)',
        lambda m: f'{m.group(1)}{p12}{m.group(2)}', 'zones-bar-z12')
    html = sub_or_die(html,
        r'(Z2–Z3 Aérobie</span>\s*<span style="font-size:12px;color:#64748b">)[\d.]+(h · <strong>)\d+(%</strong>)',
        lambda m: f'{m.group(1)}{h23:.1f}{m.group(2)}{p23}{m.group(3)}', 'zones-panel-z23', flags=re.S)
    html = sub_or_die(html,
        r'(background:#2563eb;width:)\d+(%;height:100%)',
        lambda m: f'{m.group(1)}{p23}{m.group(2)}', 'zones-bar-z23')
    html = sub_or_die(html,
        r'(Z4 Seuil</span>\s*<span style="font-size:12px;color:#64748b">)[\d.]+(h · <strong>)\d+(%</strong>)',
        lambda m: f'{m.group(1)}{h4:.1f}{m.group(2)}{p4}{m.group(3)}', 'zones-panel-z4', flags=re.S)
    html = sub_or_die(html,
        r'(background:#f97316;width:)\d+(%;height:100%)',
        lambda m: f'{m.group(1)}{p4}{m.group(2)}', 'zones-bar-z4')
    html = sub_or_die(html, r'(data: \[)[\d.,\s]+(\],\s*\n\s*backgroundColor: \[GREEN)',
        lambda m: f'{m.group(1)}{h12:.1f}, {h23:.1f}, {h4:.1f}, {h5:.1f}{m.group(2)}', 'zones-doughnut-data')
    html = sub_or_die(html,
        r"(tooltip: \{ callbacks:\{ label: ctx => ctx\.label\+' : '\+)\[[\d.,\s]+\](\[ctx\.dataIndex\]\.toFixed\(1\)\+'h \('\+)\[[\d,\s]+\](\[ctx\.dataIndex\]\+'%\)' \} \})",
        lambda m: f'{m.group(1)}[{h12:.1f},{h23:.1f},{h4:.1f},{h5:.1f}]{m.group(2)}[{p12},{p23},{p4},{p5}]{m.group(3)}',
        'zones-tooltip')

    # 7. Arrays hebdomadaires
    for name in ['weeks', 'runKm', 'runKmOnly', 'trailKmOnly', 'wkTimeH', 'runElev',
                 'trailElev', 'wkCal', 'reData', 'wkMaxTemp', 'wkVeloOutKm', 'wkVeloInKm', 'wkVeloElev', 'wkVeloWatts',
                 'wkMarathonPaceKm', 'wkEfficiency']:
        html = sub_or_die(html, rf'const {name}\s*=\s*\[.*?\];',
            f'const {name} = ' + js_array(weekly[name]) + ';', name)
    html = sub_or_die(html, r'const wkCadence = \[.*?\];',
        'const wkCadence = ' + js_array(weekly['wkCadence']) + ';', 'wkCadence')

    # 8. calActs
    html = sub_or_die(html, r'const calActs = \[.*?\];', lambda m: serialize_calacts(calacts),
        'calActs', flags=re.DOTALL)

    # 8b. veloSessions
    html = sub_or_die(html, r'const veloSessions = \[.*?\];', lambda m: serialize_velo(velo_sessions),
        'veloSessions', flags=re.DOTALL)

    # 9. Footer
    html = sub_or_die(html,
        r'<p class="text-xs text-slate-400 text-center pb-4">\d+ activités · 1 janv\. → [^<]+</p>',
        f'<p class="text-xs text-slate-400 text-center pb-4">{total_acts} activités · '
        f'1 janv. → {last_date_str} 2026 · Données : MCP Strava</p>',
        'footer')

    return html, dict(total_acts=total_acts, rt_sessions=rt_sessions, total_km=total_km,
                       total_elev=total_elev, total_kcal=total_kcal)


def patch_annuel_html(html, all_acts, monthly, velo_sessions, last_date_str):
    n_months = len(monthly['sessions'])
    month_lbl = MONTHS[n_months - 1]
    old_month_match = re.search(r'Jan–(\w{3})', html)
    old_month = old_month_match.group(1) if old_month_match else None
    if old_month and old_month != month_lbl:
        html = html.replace(f'Jan–{old_month}', f'Jan–{month_lbl}')

    total_run_km = sum(monthly['runKm'])
    total_trail_km = sum(monthly['trailKm'])
    total_km = round(total_run_km + total_trail_km)
    total_run_elev = sum(monthly['runElev'])
    total_trail_elev = sum(monthly['trailElev'])
    total_elev = total_run_elev + total_trail_elev
    total_sessions = sum(monthly['sessions'])
    total_time = round(sum(monthly['timeH']))

    html = sub_or_die(html,
        r'Année en cours · données Jan – [^<]+2026',
        f'Année en cours · données Jan – {last_date_str} 2026', 'annuel-banner')
    html = sub_or_die(html,
        r'(<div class="metric-lbl">Distance totale \(Jan–\w+\)</div><div class="metric-val">)[\d\s]+( km</div>)',
        lambda m: f'{m.group(1)}{total_km:,}'.replace(',', ' ') + m.group(2), 'annuel-kpi-km')
    html = sub_or_die(html,
        r'(<div class="metric-lbl">Dénivelé cumulé \(Jan–\w+\)</div><div class="metric-val">)[\d\s]+( m</div>)',
        lambda m: f'{m.group(1)}{total_elev:,}'.replace(',', ' ') + m.group(2), 'annuel-kpi-elev')
    # "Séances run+trail" / "Temps de mouvement" labels repeat identically for every year,
    # so these two substitutions must be scoped to the year-2026 block only.
    start = html.index('<div id="year-2026"')
    end = html.index('<!-- ════ SYNTHÈSE')
    section = html[start:end]
    section = sub_or_die(section,
        r'(<div class="metric-lbl">Séances run\+trail</div><div class="metric-val">)\d+(</div>)',
        lambda m: f'{m.group(1)}{total_sessions}{m.group(2)}', 'annuel-kpi-sess')
    section = sub_or_die(section,
        r'(<div class="metric-lbl">Temps de mouvement</div><div class="metric-val">~)\d+( h</div>)',
        lambda m: f'{m.group(1)}{total_time}{m.group(2)}', 'annuel-kpi-time')
    velo_2026 = [v for v in velo_sessions if v['date'][:4] == '2026']
    velo_km = sum(v['km'] for v in velo_2026)
    velo_elev = sum(v['elev'] for v in velo_2026)
    velo_h = sum(v['duration_s'] for v in velo_2026) / 3600
    velo_speed = velo_km / velo_h if velo_h else 0
    velo_out_n = sum(1 for v in velo_2026 if not v['indoor'])
    velo_in_n = sum(1 for v in velo_2026 if v['indoor'])
    section = sub_or_die(section,
        r'(<div class="metric-lbl">Sorties vélo <span class="text-xs font-normal">\(complémentaire\)</span></div><div class="metric-val">)\d+(</div><div class="metric-note">)\d+( extérieur · )\d+( home-trainer</div>)',
        lambda m: f'{m.group(1)}{len(velo_2026)}{m.group(2)}{velo_out_n}{m.group(3)}{velo_in_n}{m.group(4)}',
        'annuel-velo-n')
    section = sub_or_die(section,
        r'(<div class="metric-lbl">Distance vélo</div><div class="metric-val">)[\d\s]+( km</div>)',
        lambda m: f'{m.group(1)}{round(velo_km):,}'.replace(',', ' ') + m.group(2), 'annuel-velo-km')
    section = sub_or_die(section,
        r'(<div class="metric-lbl">D\+ vélo</div><div class="metric-val">)[\d\s]+( m</div>)',
        lambda m: f'{m.group(1)}{round(velo_elev):,}'.replace(',', ' ') + m.group(2), 'annuel-velo-elev')
    section = sub_or_die(section,
        r'(<div class="metric-lbl">Vitesse moy\. vélo</div><div class="metric-val">)[\d.]+( km/h</div>)',
        lambda m: f'{m.group(1)}{velo_speed:.1f}{m.group(2)}', 'annuel-velo-speed')
    html = html[:start] + section + html[end:]

    html = sub_or_die(html,
        r'(<tfoot><tr><td>Total Jan–)\w+(</td><td class="r" style="color:#16a34a">)\d+(</td>'
        r'<td class="r" style="color:#ea580c">)[\d.]+(</td><td class="r">)[\d\s]+( km</td>'
        r'<td class="r" style="color:#2563eb">)[\d\s]+( m</td><td class="r">)\d+(</td><td class="r">~)\d+(h</td></tr></tfoot>)',
        lambda m: (f'{m.group(1)}{month_lbl}{m.group(2)}{round(total_run_km)}{m.group(3)}'
                   f'{round(total_trail_km)}{m.group(4)}{total_km:,}'.replace(',', ' ') + m.group(5) +
                   f'{total_elev:,}'.replace(',', ' ') + m.group(6) + f'{total_sessions}{m.group(7)}{total_time}{m.group(8)}'),
        'annuel-tfoot')

    html = sub_or_die(html,
        r'(<div class="cmp-year" style="color:#d97706">2026 <span class="partial">Jan–)\w+(</span></div>\s*'
        r'<div class="cmp-row"><span class="lbl">km</span><span class="val">)[\d\s]+(</span></div>\s*'
        r'<div class="cmp-row"><span class="lbl">D\+</span><span class="val">)[\d\s]+( m</span></div>\s*'
        r'<div class="cmp-row"><span class="lbl">séances</span><span class="val">)\d+(</span></div>\s*'
        r'<div class="cmp-row"><span class="lbl">temps</span><span class="val">~)\d+(h</span></div>)',
        lambda m: (f'{m.group(1)}{month_lbl}{m.group(2)}{total_km:,}'.replace(',', ' ') + m.group(3) +
                   f'{total_elev:,}'.replace(',', ' ') + m.group(4) + f'{total_sessions}{m.group(5)}{total_time}{m.group(6)}'),
        'annuel-cmp-card', flags=re.S)

    km_str = f'{total_km:,}'.replace(',', ' ')
    elev_str = f'{total_elev:,}'.replace(',', ' ')
    sub_text = (f"{total_sessions} séances · {km_str} km · {elev_str} m D+ · 5 courses · "
                f"Jan–{month_lbl} 2026 (en cours)")
    data2026_block = (f"2026: {{\n    runKm:    {js_array(monthly['runKm'])},\n    trailKm:  {js_array(monthly['trailKm'])},\n"
                       f"    runElev:  {js_array(monthly['runElev'])},\n    trailElev:{js_array(monthly['trailElev'])},\n"
                       f"    sessions: {js_array(monthly['sessions'])},\n    timeH:    {js_array(monthly['timeH'])},\n"
                       f"    sub:'{sub_text}', lowSessions:15, partial:true,\n  }},")
    html = sub_or_die(html,
        r"2026:\s*\{\s*runKm:\s*\[.*?\],\s*trailKm:\s*\[.*?\],\s*runElev:\s*\[.*?\],\s*trailElev:\s*\[.*?\],\s*"
        r"sessions:\s*\[.*?\],\s*timeH:\s*\[.*?\],\s*sub:'[^']*', lowSessions:15, partial:true,\s*\},",
        data2026_block, 'annuel-DATA2026', flags=re.S)

    return html, dict(total_km=total_km, total_elev=total_elev, total_sessions=total_sessions, total_time=total_time)


# ── MAIN ──────────────────────────────────────────────────────────────

FR_MONTHS_FULL = ['janv.', 'fév.', 'mars', 'avr.', 'mai', 'juin', 'juil.', 'août', 'sep.', 'oct.', 'nov.', 'déc.']


def fmt_date_fr(iso_date):
    dt = datetime.strptime(iso_date, '%Y-%m-%d')
    return f'{dt.day} {FR_MONTHS_FULL[dt.month - 1]}'


def main():
    merged, added = merge_inbox()
    print(f'[merge] {added} nouvelle(s) activité(s) fusionnée(s) dans activities_store.json '
          f'({len(merged)} activités depuis mai 2026)')

    all_acts = load_all_activities()
    last_date = max(a['start_local'][:10] for a in all_acts)
    last_date_str = fmt_date_fr(last_date)

    weekly = compute_weekly(all_acts)
    zones_hours, zones_pct, zones_total_h = compute_zones(all_acts)
    heatmap = compute_heatmap(all_acts)
    sports = compute_sports(all_acts)
    calacts = compute_calacts(all_acts)
    velo_sessions = compute_velo_sessions(all_acts)
    monthly = compute_monthly_2026(all_acts)

    perf_html = HTML_PERF.read_text(encoding='utf-8')
    old_acwr = read_const_array(perf_html, 'acwr')
    old_reData = read_const_array(perf_html, 'reData')
    weekly['acwr'] = compute_acwr(weekly['reData'], old_acwr, old_reData)

    # ACWR D+ : même modèle EWMA aigu(7j)/chronique(42j), appliqué au D+ hebdo au lieu du Relative
    # Effort — capture la charge excentrique/neuromusculaire que le RE seul ne reflète pas.
    old_acwr_dplus = read_const_array(perf_html, 'acwrDplus')
    old_run_elev = read_const_array(perf_html, 'runElev')
    old_trail_elev = read_const_array(perf_html, 'trailElev')
    old_total_elev = [r + t for r, t in zip(old_run_elev, old_trail_elev)] if old_run_elev else []
    total_elev_new = [r + t for r, t in zip(weekly['runElev'], weekly['trailElev'])]
    weekly['acwrDplus'] = compute_acwr(total_elev_new, old_acwr_dplus, old_total_elev)

    new_perf_html, perf_totals = patch_performance_html(
        perf_html, all_acts, weekly, calacts, velo_sessions, zones_hours, zones_pct, zones_total_h,
        heatmap, sports, last_date_str, None)
    # patch acwr/acwrDplus arrays last (séparément, dérivés des anciens arrays pré-patch)
    new_perf_html = sub_or_die(new_perf_html, r'const acwr\s*=\s*\[.*?\];',
        'const acwr = ' + js_array(weekly['acwr']) + ';', 'acwr')
    new_perf_html = sub_or_die(new_perf_html, r'const acwrDplus\s*=\s*\[.*?\];',
        'const acwrDplus = ' + js_array(weekly['acwrDplus']) + ';', 'acwrDplus')

    annuel_html = HTML_ANNUEL.read_text(encoding='utf-8')
    new_annuel_html, annuel_totals = patch_annuel_html(annuel_html, all_acts, monthly, velo_sessions, last_date_str)

    dry_run = '--dry-run' in sys.argv
    skip_backup = '--no-backup' in sys.argv
    clean_inbox = '--clean-inbox' in sys.argv

    if not dry_run and not skip_backup:
        if BACKUP_DIR.exists() or True:
            backup_file(STORE_PATH, BACKUP_DIR)
            backup_file(HTML_PERF, BACKUP_DIR)
            backup_file(HTML_ANNUEL, BACKUP_DIR)
            print(f'[backup] sauvegarde créée dans {BACKUP_DIR}')

    if dry_run:
        print('[dry-run] Aucun fichier écrit.')
    else:
        HTML_PERF.write_text(new_perf_html, encoding='utf-8')
        HTML_ANNUEL.write_text(new_annuel_html, encoding='utf-8')
        print(f'[write] {HTML_PERF.name} et {HTML_ANNUEL.name} mis à jour.')
        if clean_inbox and INBOX_PATH.exists():
            INBOX_PATH.write_text('[]', encoding='utf-8')
            print('[clean-inbox] activities_inbox.json vidé.')

    # ── Résumé pour rédaction du texte narratif ──
    print('\n' + '=' * 60)
    print(f'RÉSUMÉ — jusqu\'au {last_date_str} 2026')
    print('=' * 60)
    print(f"Saison : {perf_totals['total_acts']} activités · {perf_totals['rt_sessions']} séances run+trail · "
          f"{perf_totals['total_km']:.0f} km · D+ {perf_totals['total_elev']:.0f} m · "
          f"{perf_totals['total_kcal']:.0f} kcal")
    w = weekly
    print(f"\nDernières semaines ({w['weeks'][-3]} / {w['weeks'][-2]} / {w['weeks'][-1]}) :")
    for i in range(-3, 0):
        print(f"  {w['weeks'][i]:>6} : {w['runKm'][i]:>5.1f} km · D+ {w['trailElev'][i]+w['runElev'][i]:>4} m · "
              f"RE {w['reData'][i]:>4} · ACWR {w['acwr'][i]} · ACWR D+ {w['acwrDplus'][i]}")
    print(f"\nACWR actuel : {w['acwr'][-1]} · ACWR D+ actuel : {w['acwrDplus'][-1]}")
    print(f"Économie de course (km/RE ajusté) : {w['wkEfficiency'][-1]} · "
          f"Allure marathon cette semaine : {w['wkMarathonPaceKm'][-1]} km")
    for label, date_str in [('Échappée Belle (22 août 2026)', '2026-08-22'),
                             ('Marathon Nice-Cannes (8 nov. 2026)', '2026-11-08')]:
        days = (datetime.strptime(date_str, '%Y-%m-%d') - datetime.strptime(last_date, '%Y-%m-%d')).days
        print(f"  J-{days} · {label}")
    print(f"\nBilan annuel 2026 (Jan–{MONTHS[len(monthly['sessions'])-1]}) : "
          f"{annuel_totals['total_sessions']} séances · {annuel_totals['total_km']} km · "
          f"D+ {annuel_totals['total_elev']} m")
    print('\n→ Il reste à rédiger/ajuster à la main : badge ACWR (texte), résumé exécutif, recommandations P1/P2/P3.')


if __name__ == '__main__':
    main()
