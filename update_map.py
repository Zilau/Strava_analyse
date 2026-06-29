import sys, json, re
sys.stdout.reconfigure(encoding='utf-8')

BASE = r'C:\Users\lmiklic\.claude\projects\c--Users-lmiklic-repository-Strava-analyse\dcb8c533-7024-4104-bf32-aa54c045cd61\tool-results'

ACTS = [
  ('1781680629572', 'Maxicross 25km',             '1 fév',   'Trail', 24.9,  True,  300),
  ('1781680631455', 'ETP 120km',                   '21 mars', 'Trail', 120.9, True,  500),
  ('1781680630664', 'Trail des Lavoirs 23km',       '10 mai',  'Trail', 23.0,  True,  300),
  ('1781680630906', 'Foulée Verte Clamart 17.5km',  '31 mai',  'Trail', 17.5,  True,  250),
  ('1781680631143', 'Foulées du 12ème 10km',        '14 juin', 'Run',   10.1,  True,  999),
  ('1781680632568', 'Rando-Trail Cap Blanc Nez',    '24 jan',  'Trail', 18.5,  False, 300),
  ('1781680632843', 'Station Trail Bures (1)',       '1 mars',  'Trail', 29.8,  False, 300),
  ('1781680633457', 'Station Trail Bures (2)',       '8 mars',  'Trail', 27.5,  False, 300),
  ('1781680634041', 'Stage Trail Grand Serre',       '2 mai',   'Trail', 32.9,  False, 400),
  ('1781680634601', 'Boucle Marne + Vincennes 30km', '11 jan', 'Run',   30.2,  False, 300),
  ('1781680634885', 'Vincennes + Marne + Gravelle',  '8 fév',  'Trail', 30.2,  False, 300),
  ('1781680635215', 'Terrils Pinchonvalles',         '5 avr',  'Trail', 13.1,  False, 250),
  ('1781680635731', 'Séance Trail Gravelle',         '7 juin',  'Trail', 11.6,  False, 250),
  ('1781680636871', 'Sortie longue Gravelle',        '4 jan',   'Trail', 26.4,  False, 300),
  ('1781680636681', 'D+ Gravelle',                   '24 mai',  'Trail', 15.0,  False, 250),
]

lines = ['const mapRoutes = [']
for fid, name, date, t, km, race, maxpts in ACTS:
    fpath = f'{BASE}\\mcp-claude_ai_Strava-get_activity_streams-{fid}.txt'
    with open(fpath, encoding='utf-8') as f:
        data = json.loads(f.read())
    pts = data['location']
    step = max(1, len(pts) // maxpts)
    sampled = pts[::step]
    if sampled[-1] != pts[-1]:
        sampled.append(pts[-1])
    sampled = [[round(p[0], 5), round(p[1], 5)] for p in sampled]
    race_str = 'true' if race else 'false'
    pts_json = json.dumps(sampled, separators=(',', ':'))
    name_json = json.dumps(name, ensure_ascii=False)
    date_json = json.dumps(date, ensure_ascii=False)
    lines.append(f'  {{name:{name_json},date:{date_json},t:"{t}",km:{km},race:{race_str},pts:{pts_json}}},')
    print(f'  {name}: {len(pts)} pts → {len(sampled)} pts (step={step})')
lines.append('];')
new_block = '\n'.join(lines)

HTML = r'c:\Users\lmiklic\repository\Strava_analyse\rapport_performance.html'
with open(HTML, encoding='utf-8') as f:
    content = f.read()

# Remplace le bloc mapRoutes existant
pattern = r'const mapRoutes = \[.*?\];'
new_content = re.sub(pattern, new_block, content, flags=re.DOTALL)

if not re.search(r'const mapRoutes = \[', content):
    print('ERREUR : pattern mapRoutes non trouvé dans le HTML')
    sys.exit(1)
if new_content == content:
    print('HTML déjà à jour, aucun changement nécessaire.')
    sys.exit(0)

with open(HTML, 'w', encoding='utf-8') as f:
    f.write(new_content)

old_size = len(content.encode('utf-8'))
new_size = len(new_content.encode('utf-8'))
print(f'\nHTML mis à jour : {old_size//1024}KB → {new_size//1024}KB')
print(f'Lignes : {content.count(chr(10))} → {new_content.count(chr(10))}')
