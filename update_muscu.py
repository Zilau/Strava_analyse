"""
Pipeline de mise à jour des séances de musculation (API Garmin Connect).

Contexte : Strava n'expose jamais le détail séries/reps/charges pour les séances
WeightTraining (seulement durée/calories globales). Le fichier .fit brut exporté
depuis la montre contient bien des messages `set`, mais avec des valeurs
pré-correction (l'auto-détection de la montre est peu fiable — cf. l'historique
de ce fichier). L'API Garmin Connect (`get_activity_exercise_sets`) renvoie en
revanche les données telles qu'affichées/recalculées côté serveur, nettement
plus fiables — c'est la source utilisée ici.

Prérequis : une session Garmin Connect valide, sauvegardée par garmin_login.py
(~/.garminconnect). Si le token a expiré, relancer garmin_login.py.

Usage :
  python update_muscu.py (--dry-run pour prévisualiser sans écrire)
    -> liste les activités strength_training récentes, upsert celles non
       encore importées (ou dont la source n'est pas encore l'API) dans
       muscu_store.json
    -> régénère `const muscuSessions` et patche rapport_performance.html
"""
import sys, json, re
from pathlib import Path
from garminconnect import Garmin

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).parent
STORE_PATH = ROOT / 'muscu_store.json'
HTML_PERF = ROOT / 'rapport_performance.html'
TOKENSTORE = str(Path.home() / '.garminconnect')

# Correspondance français des catégories d'exercice Garmin (`exerciseSets[].exercises[].category`)
CATEGORY_FR = {
    'SQUAT': 'Squat', 'CALF_RAISE': 'Mollets (calf raise)', 'CRUNCH': 'Crunch',
    'CURL': 'Curl', 'BANDED_EXERCISES': 'Exercice élastique', 'BENCH_PRESS': 'Développé couché',
    'DEADLIFT': 'Soulevé de terre', 'LUNGE': 'Fente', 'PLANK': 'Planche',
    'PULL_UP': 'Traction', 'PUSH_UP': 'Pompe', 'ROW': 'Rowing',
    'SHOULDER_PRESS': 'Développé épaules', 'SIT_UP': 'Sit-up', 'HIP_RAISE': 'Extension de hanche',
    'LEG_RAISE': 'Leg raise', 'LEG_CURL': 'Leg curl', 'TOTAL_BODY': 'Corps entier',
    'WARM_UP': 'Échauffement', 'CARDIO': 'Cardio', 'CORE': 'Gainage',
    'OLYMPIC_LIFT': 'Haltérophilie', 'HYPEREXTENSION': 'Hyperextension', 'FLYE': 'Écarté',
    'CARRY': 'Port de charge', 'CHOP': 'Rotation de tronc', 'SHRUG': 'Shrug',
    'LATERAL_RAISE': 'Élévation latérale', 'SHOULDER_STABILITY': 'Stabilité épaule',
    'HIP_STABILITY': 'Stabilité de hanche', 'HIP_SWING': 'Balancier de hanche',
    'PLYO': 'Pliométrie', 'TRICEPS_EXTENSION': 'Extension triceps', 'RUN': 'Course à pied',
    'UNKNOWN': 'Non identifié',
}
# Noms d'exercice spécifiques (`exercises[].name`), plus précis que la catégorie quand présents
NAME_FR = {
    'HAMSTRING_CURLS': 'Ischio-jambiers (élastique)',
    'TRICEPS_CRUNCH': 'Crunch triceps',
}

# Groupes musculaires sollicités par catégorie Garmin — zones du schéma corporel
# (voir bodySvg() dans rapport_performance.html pour les ids de zone)
MUSCLES_BY_CATEGORY = {
    'SQUAT': ['quads', 'glutes', 'hamstrings'], 'CALF_RAISE': ['calves'], 'CRUNCH': ['abs'],
    'CURL': ['biceps'], 'BENCH_PRESS': ['chest', 'triceps', 'shoulders'],
    'DEADLIFT': ['hamstrings', 'glutes', 'back'], 'LUNGE': ['quads', 'glutes', 'hamstrings'],
    'PLANK': ['abs'], 'PULL_UP': ['back', 'biceps'], 'PUSH_UP': ['chest', 'triceps', 'shoulders'],
    'ROW': ['back', 'biceps'], 'SHOULDER_PRESS': ['shoulders', 'triceps'], 'SIT_UP': ['abs'],
    'HIP_RAISE': ['glutes', 'hamstrings'], 'LEG_RAISE': ['abs'], 'LEG_CURL': ['hamstrings'],
    'TOTAL_BODY': ['quads', 'chest', 'back', 'abs'], 'CORE': ['abs'],
    'OLYMPIC_LIFT': ['quads', 'glutes', 'back', 'shoulders'], 'HYPEREXTENSION': ['back', 'glutes'],
    'FLYE': ['chest'], 'CARRY': ['forearms', 'abs'], 'CHOP': ['abs', 'shoulders'],
    'SHRUG': ['shoulders'], 'LATERAL_RAISE': ['shoulders'], 'SHOULDER_STABILITY': ['shoulders'],
    'HIP_STABILITY': ['glutes'], 'HIP_SWING': ['glutes', 'hamstrings'], 'PLYO': ['quads', 'calves'],
    'TRICEPS_EXTENSION': ['triceps'], 'RUN': ['quads', 'calves', 'hamstrings'],
}
# Override par nom spécifique quand il est plus précis que la catégorie
MUSCLES_BY_NAME = {
    'HAMSTRING_CURLS': ['hamstrings'],
    'TRICEPS_CRUNCH': ['abs', 'triceps'],
}


def label_exercise(category, name):
    if name:
        return NAME_FR.get(name, name.replace('_', ' ').capitalize())
    if category:
        return CATEGORY_FR.get(category, category.replace('_', ' ').capitalize())
    return 'Exercice non identifié'


def muscles_for(category, name):
    if name and name in MUSCLES_BY_NAME:
        return MUSCLES_BY_NAME[name]
    return MUSCLES_BY_CATEGORY.get(category, [])


def build_session(activity_id, act, raw):
    exercises = []
    cur = None
    for s in raw.get('exerciseSets', []):
        if s.get('setType') != 'ACTIVE':
            continue
        exs = s.get('exercises') or []
        best = max(exs, key=lambda e: e.get('probability', -999)) if exs else None
        cat = best.get('category') if best else None
        name = best.get('name') if best else None
        label = label_exercise(cat, name)
        if cur is None or cur['category_name'] != label:
            cur = {'category_name': label, 'muscles': muscles_for(cat, name), 'sets': []}
            exercises.append(cur)
        cur['sets'].append({
            'reps': s.get('repetitionCount') or 0,
            'weight': round(s.get('weight') or 0, 1),
            'duration_s': round(s.get('duration') or 0, 1),
        })
    return {
        'id': activity_id,
        'date': act['startTimeLocal'][:10],
        'start_local': act['startTimeLocal'].replace(' ', 'T'),
        'name': (act.get('activityName') or 'Musculation').strip(),
        'duration_s': round(act.get('duration') or 0),
        'calories': int(act.get('calories') or 0),
        'avg_hr': act.get('averageHR'),
        'max_hr': act.get('maxHR'),
        'exercises': exercises,
        'source': 'garmin_api',
    }


def fetch_and_merge():
    store = json.loads(STORE_PATH.read_text(encoding='utf-8')) if STORE_PATH.exists() else []
    by_id = {s['id']: s for s in store}

    garmin = Garmin()
    garmin.login(TOKENSTORE)

    acts = garmin.get_activities(0, 30)
    strength = [a for a in acts if 'strength' in (a.get('activityType', {}).get('typeKey') or '')]

    updated = []
    for a in strength:
        aid = str(a['activityId'])
        if by_id.get(aid, {}).get('source') == 'garmin_api':
            continue
        raw = garmin.get_activity_exercise_sets(aid)
        by_id[aid] = build_session(aid, a, raw)
        updated.append(aid)

    merged = sorted(by_id.values(), key=lambda s: s['start_local'])
    with open(STORE_PATH, 'w', encoding='utf-8') as f:
        json.dump(merged, f, ensure_ascii=False, indent=1)
    return merged, updated


def sub_or_die(html, pattern, replacement, label, flags=0):
    new_html, n = re.subn(pattern, replacement, html, count=1, flags=flags)
    if n == 0:
        raise RuntimeError(f'Pattern non trouvé : {label}')
    return new_html


def main():
    sessions, updated = fetch_and_merge()
    print(f'[merge] {len(updated)} séance(s) importée(s)/mise(s) à jour depuis Garmin Connect '
          f'({len(sessions)} séance(s) au total)')
    for aid in updated:
        print(f'         + activity {aid}')

    html = HTML_PERF.read_text(encoding='utf-8')
    new_html = sub_or_die(html, r'const muscuSessions\s*=\s*\[.*?\];',
        'const muscuSessions = ' + json.dumps(sessions, ensure_ascii=False, separators=(',', ':')) + ';',
        'muscuSessions', flags=re.DOTALL)

    if '--dry-run' in sys.argv:
        print('[dry-run] Aucun fichier écrit.')
    else:
        HTML_PERF.write_text(new_html, encoding='utf-8')
        print(f'[write] {HTML_PERF.name} mis à jour.')

    print('\n' + '=' * 60)
    for s in sessions:
        n_sets = sum(len(e['sets']) for e in s['exercises'])
        exs = ', '.join(f"{e['category_name']} ({len(e['sets'])})" for e in s['exercises'])
        print(f"{s['date']} · {s['name']} · {round(s['duration_s']/60)} min · {s['calories']} kcal · "
              f"{n_sets} séries — {exs}")


if __name__ == '__main__':
    main()
