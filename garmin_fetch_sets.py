"""
Récupère le détail des séries de musculation via l'API Garmin Connect
(reflète les corrections faites dans l'app, contrairement au .fit brut).

Nécessite une session déjà sauvegardée par garmin_login.py (~/.garminconnect).

Usage :
  python garmin_fetch_sets.py                 -> liste les séances strength_training récentes
  python garmin_fetch_sets.py <activity_id>    -> détail séries pour une activité donnée
"""
import sys, json
from pathlib import Path
from garminconnect import Garmin

TOKENSTORE = str(Path.home() / '.garminconnect')


def main():
    garmin = Garmin()
    garmin.login(TOKENSTORE)
    print(f'[ok] Connecté en tant que {garmin.full_name or garmin.display_name}\n')

    if len(sys.argv) > 1:
        activity_id = sys.argv[1]
        sets = garmin.get_activity_exercise_sets(activity_id)
        print(json.dumps(sets, ensure_ascii=False, indent=2))
        return

    acts = garmin.get_activities(0, 30)
    strength = [a for a in acts if 'strength' in (a.get('activityType', {}).get('typeKey') or '')]
    if not strength:
        print('Aucune activité strength_training trouvée dans les 30 dernières activités.')
        print('Types vus :', sorted({a.get('activityType', {}).get('typeKey') for a in acts}))
        return
    for a in strength:
        print(f"id={a['activityId']}  {a['startTimeLocal']}  {a['activityName']}  "
              f"({round(a.get('duration',0)/60)} min, {round(a.get('calories',0))} kcal)")


if __name__ == '__main__':
    main()
