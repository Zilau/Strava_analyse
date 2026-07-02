import sys, json, math
sys.stdout.reconfigure(encoding='utf-8')
from datetime import datetime, timedelta
from collections import defaultdict

P1 = r'C:\Users\lmiklic\.claude\projects\c--Users-lmiklic-repository-Strava-analyse\dcb8c533-7024-4104-bf32-aa54c045cd61\tool-results\mcp-claude_ai_Strava-list_activities-1781616842343.txt'
with open(P1, encoding='utf-8') as f:
    d1 = json.load(f)

P2_JSON = r"""{"activities":[{"id":"18403275519","name":"Fractionné court 🔵🟡","sport_type":"Run","start_local":"2026-05-06T19:20:52","summary":{"distance":11000.9,"moving_time":3802,"elevation_gain":18,"avg_speed":2.893,"relative_effort":191,"avg_cadence":86.4}},{"id":"18422502649","name":"Fractionné long 🔵🟡","sport_type":"Run","start_local":"2026-05-08T09:21:23","summary":{"distance":14061.9,"moving_time":5121,"elevation_gain":36,"avg_speed":2.746,"relative_effort":255,"avg_cadence":86.2}},{"id":"18448862987","name":"Trail des Lavoirs","sport_type":"TrailRun","start_local":"2026-05-10T08:50:41","summary":{"distance":22952.6,"moving_time":9140,"elevation_gain":526,"avg_speed":2.511,"relative_effort":554,"avg_cadence":81.4}},{"id":"18481432909","name":"Footing du mardi 🔵🟡","sport_type":"Run","start_local":"2026-05-12T19:19:16","summary":{"distance":12649.8,"moving_time":4254,"elevation_gain":37,"avg_speed":2.974,"relative_effort":203,"avg_cadence":86.9}},{"id":"18494736105","name":"Fractionné court 🔵🟡","sport_type":"Run","start_local":"2026-05-13T19:18:50","summary":{"distance":10652.8,"moving_time":3837,"elevation_gain":25,"avg_speed":2.776,"relative_effort":167,"avg_cadence":86.0}},{"id":"18519001431","name":"Fractionné long","sport_type":"Run","start_local":"2026-05-15T17:47:04","summary":{"distance":9999.2,"moving_time":3373,"elevation_gain":41,"avg_speed":2.964,"relative_effort":191,"avg_cadence":84.8}},{"id":"18538551877","name":"Vimy - Farbus - Willerval - Vimy","sport_type":"Run","start_local":"2026-05-17T09:06:06","summary":{"distance":12430.1,"moving_time":4086,"elevation_gain":86,"avg_speed":3.042,"relative_effort":227,"avg_cadence":85.4}},{"id":"18564480928","name":"Marche retour garage","sport_type":"Walk","start_local":"2026-05-19T09:15:13","summary":{"distance":2708.9,"moving_time":1875,"elevation_gain":14,"avg_speed":1.445,"relative_effort":7,"avg_cadence":61.7}},{"id":"18572378268","name":"Footing du mardi 🔵🟡","sport_type":"Run","start_local":"2026-05-19T19:21:29","summary":{"distance":12596.4,"moving_time":4531,"elevation_gain":35,"avg_speed":2.780,"relative_effort":221,"avg_cadence":85.9}},{"id":"18586264165","name":"Fractionné court 🔵🟡","sport_type":"Run","start_local":"2026-05-20T19:36:00","summary":{"distance":11157.5,"moving_time":4090,"elevation_gain":76,"avg_speed":2.728,"relative_effort":225,"avg_cadence":86.0}},{"id":"18596192483","name":"Marche Aller Garage","sport_type":"Walk","start_local":"2026-05-21T16:18:35","summary":{"distance":3678.4,"moving_time":2259,"elevation_gain":10,"avg_speed":1.628,"relative_effort":11}},{"id":"18607017393","name":"Boucle du dredi midi 🔵🟡","sport_type":"TrailRun","start_local":"2026-05-22T12:02:11","summary":{"distance":10437.9,"moving_time":3763,"elevation_gain":20,"avg_speed":2.774,"relative_effort":182,"avg_cadence":86.2}},{"id":"18612028146","name":"Fractionné long 🔵🟡","sport_type":"Run","start_local":"2026-05-22T19:35:43","summary":{"distance":10572.8,"moving_time":3745,"elevation_gain":21,"avg_speed":2.823,"relative_effort":210,"avg_cadence":86.2}},{"id":"18632222472","name":"Un peu de D+ Gravelle","sport_type":"TrailRun","start_local":"2026-05-24T09:37:12","summary":{"distance":15023.1,"moving_time":6592,"elevation_gain":375,"avg_speed":2.279,"relative_effort":339,"avg_cadence":79.0}},{"id":"18644844506","name":"Quelques tours au polygone","sport_type":"Ride","start_local":"2026-05-25T09:58:01","summary":{"distance":33735.3,"moving_time":4863,"elevation_gain":159,"avg_speed":6.937,"relative_effort":60}},{"id":"18648151357","name":"Marche Tour du Lac","sport_type":"Walk","start_local":"2026-05-25T14:54:40","summary":{"distance":4904.7,"moving_time":3565,"elevation_gain":15,"avg_speed":1.376,"relative_effort":11}},{"id":"18663397535","name":"Marche Retour TAF","sport_type":"Walk","start_local":"2026-05-26T17:53:35","summary":{"distance":4579.9,"moving_time":3321,"elevation_gain":27,"avg_speed":1.379,"relative_effort":10}},{"id":"18679399082","name":"Fractionné court 🔵🟡","sport_type":"Run","start_local":"2026-05-27T19:17:39","summary":{"distance":11435.4,"moving_time":4226,"elevation_gain":21,"avg_speed":2.706,"relative_effort":154,"avg_cadence":85.9}},{"id":"18698621123","name":"Boucle du dredi midi (à la fraîche) 🔵🟡","sport_type":"TrailRun","start_local":"2026-05-29T07:37:04","summary":{"distance":10560.5,"moving_time":3723,"elevation_gain":23,"avg_speed":2.837,"relative_effort":164,"avg_cadence":86.3}},{"id":"18703340006","name":"Marche Bord de Marne","sport_type":"Walk","start_local":"2026-05-29T15:35:50","summary":{"distance":6692.9,"moving_time":4832,"elevation_gain":45,"avg_speed":1.385,"relative_effort":14}},{"id":"18711647967","name":"Reco Foulées 12 avec Team Outdoor","sport_type":"Run","start_local":"2026-05-30T08:17:10","summary":{"distance":10515.8,"moving_time":3600,"elevation_gain":22,"avg_speed":2.921,"relative_effort":152,"avg_cadence":86.9}},{"id":"18725084836","name":"La foulée verte de Clamart","sport_type":"TrailRun","start_local":"2026-05-31T09:00:38","summary":{"distance":17498,"moving_time":6587,"elevation_gain":414,"avg_speed":2.656,"relative_effort":473,"avg_cadence":81.7}},{"id":"18774410815","name":"Fractionné court 🔵🟡","sport_type":"Run","start_local":"2026-06-03T19:22:09","summary":{"distance":11998.6,"moving_time":4399,"elevation_gain":45,"avg_speed":2.728,"relative_effort":193,"avg_cadence":86.5}},{"id":"18795323562","name":"Boucle du dredi midi 🔵🟡","sport_type":"TrailRun","start_local":"2026-06-05T12:03:56","summary":{"distance":10802.8,"moving_time":3822,"elevation_gain":19,"avg_speed":2.826,"relative_effort":144,"avg_cadence":86.3}},{"id":"18800500690","name":"Fractionné long 🔵🟡","sport_type":"Run","start_local":"2026-06-05T19:35:45","summary":{"distance":9839.2,"moving_time":3329,"elevation_gain":17,"avg_speed":2.956,"relative_effort":175,"avg_cadence":85.9}},{"id":"18820391514","name":"Séance Trail Gravelle","sport_type":"TrailRun","start_local":"2026-06-07T09:35:29","summary":{"distance":11559.2,"moving_time":4995,"elevation_gain":314,"avg_speed":2.314,"relative_effort":246,"avg_cadence":81.6}},{"id":"18854968551","name":"Footing du mardi 🔵🟡","sport_type":"TrailRun","start_local":"2026-06-09T19:21:06","summary":{"distance":12448.5,"moving_time":4474,"elevation_gain":39,"avg_speed":2.782,"relative_effort":179,"avg_cadence":85.5}},{"id":"18869053702","name":"Fractionné court 🔵🟡","sport_type":"Run","start_local":"2026-06-10T19:36:41","summary":{"distance":10070.8,"moving_time":3891,"elevation_gain":25,"avg_speed":2.588,"relative_effort":110,"avg_cadence":86.5}},{"id":"18880639981","name":"Marche Retour TAF","sport_type":"Walk","start_local":"2026-06-11T17:52:46","summary":{"distance":4498.8,"moving_time":3067,"elevation_gain":30,"avg_speed":1.467,"relative_effort":9}},{"id":"18888739552","name":"Mini footing du dredi midi 🔵🟡","sport_type":"Run","start_local":"2026-06-12T12:02:06","summary":{"distance":5333.5,"moving_time":1931,"elevation_gain":11,"avg_speed":2.762,"relative_effort":59,"avg_cadence":84.5}},{"id":"18899211359","name":"Séance déblocage veille de course","sport_type":"Run","start_local":"2026-06-13T09:01:56","summary":{"distance":7005,"moving_time":2546,"elevation_gain":16,"avg_speed":2.751,"relative_effort":80,"avg_cadence":85.9}},{"id":"18912280535","name":"Échauffement foulées du 12eme","sport_type":"Run","start_local":"2026-06-14T08:33:51","summary":{"distance":3664.3,"moving_time":1590,"elevation_gain":6,"avg_speed":2.305,"relative_effort":27,"avg_cadence":84.8}},{"id":"18912947563","name":"Les foulées du 12eme","sport_type":"Run","start_local":"2026-06-14T09:30:37","summary":{"distance":10060.9,"moving_time":2886,"elevation_gain":20,"avg_speed":3.486,"relative_effort":211,"avg_cadence":88.96}},{"id":"18947878064","name":"Footing du mardi","sport_type":"Run","start_local":"2026-06-16T19:32:41","summary":{"distance":11851.7,"moving_time":4061,"elevation_gain":34,"avg_speed":2.918,"relative_effort":223,"avg_cadence":86.7}},{"id":"18962101925","name":"Fractionné court 🔵🟡","sport_type":"Run","start_local":"2026-06-17T19:35:35","summary":{"distance":8048,"moving_time":3143,"elevation_gain":18,"avg_speed":2.561,"relative_effort":101,"avg_cadence":86.0}},{"id":"18980615743","name":"Boucle du dredi 🔵🟡","sport_type":"Run","start_local":"2026-06-19T07:20:21","summary":{"distance":10658.7,"moving_time":3883,"elevation_gain":22,"avg_speed":2.745,"relative_effort":147,"avg_cadence":86.4}},{"id":"19023632542","name":"Marche Tour du Lac","sport_type":"Walk","start_local":"2026-06-22T17:03:27","summary":{"distance":3004.6,"moving_time":2307,"elevation_gain":8,"avg_speed":1.302,"relative_effort":6}},{"id":"19039668328","name":"P'tit footing d'acclimatation","sport_type":"TrailRun","start_local":"2026-06-23T20:10:00","summary":{"distance":7024,"moving_time":2547,"elevation_gain":14,"avg_speed":2.758,"relative_effort":129,"avg_cadence":84.4}},{"id":"19064298438","name":"Marche Retour TAF","sport_type":"Walk","start_local":"2026-06-25T18:09:59","summary":{"distance":4445.2,"moving_time":3093,"elevation_gain":39,"avg_speed":1.437,"relative_effort":7}},{"id":"19070200772","name":"Boucle du dredi 🔵🟡","sport_type":"TrailRun","start_local":"2026-06-26T06:54:27","summary":{"distance":10429.8,"moving_time":3924,"elevation_gain":31,"avg_speed":2.658,"relative_effort":16,"avg_cadence":86.2}},{"id":"19094984083","name":"Un peu de D+ (début prépa Échappée Belle 42km)","sport_type":"TrailRun","start_local":"2026-06-28T09:05:24","summary":{"distance":13325.6,"moving_time":5565,"elevation_gain":407,"avg_speed":2.3945,"relative_effort":44,"avg_cadence":80.4}},{"id":"19127862873","name":"Footing du mardi 🔵🟡","sport_type":"Run","start_local":"2026-06-30T19:24:18","summary":{"distance":12576.2,"moving_time":4516,"elevation_gain":43,"avg_speed":2.7848,"relative_effort":21,"avg_cadence":84.8848}},{"id":"19141460361","name":"Fractionné en côte 🔵🟡","sport_type":"Run","start_local":"2026-07-01T19:22:17","summary":{"distance":11584.8,"moving_time":4260,"elevation_gain":115,"avg_speed":2.7194,"relative_effort":38,"avg_cadence":85.3891}}]}"""

d2 = json.loads(P2_JSON)
all_acts = d1['activities'] + d2['activities']
RUN = {'Run', 'TrailRun'}

def wksort(w):
    try: return datetime.strptime(w+'/2026','%d/%m/%Y')
    except: return datetime.strptime(w+'/2025','%d/%m/%Y')

# ── 1. CADENCE HEBDOMADAIRE ──
wk_cad = defaultdict(lambda: {'sum':0,'n':0})
for a in all_acts:
    if a['sport_type'] not in RUN: continue
    s = a['summary']
    cad = s.get('avg_cadence') or 0
    if not cad: continue
    dt = datetime.fromisoformat(a['start_local'])
    mon = (dt - timedelta(days=dt.weekday())).strftime('%d/%m')
    wk_cad[mon]['sum'] += cad
    wk_cad[mon]['n']   += 1

weeks_order = ['29/12','05/01','12/01','19/01','26/01','02/02','09/02','16/02','23/02','02/03',
               '09/03','16/03','23/03','30/03','06/04','13/04','20/04','27/04','04/05','11/05',
               '18/05','25/05','01/06','08/06','15/06','22/06','29/06']
wk_cadence = []
for w in weeks_order:
    d = wk_cad.get(w, {'sum':0,'n':0})
    wk_cadence.append(round(d['sum']/d['n'], 1) if d['n'] else None)

print(f"wkCadence = {wk_cadence}")

# ── 2. HEATMAP (jour × créneau) ──
JOURS = ['Lun','Mar','Mer','Jeu','Ven','Sam','Dim']
SLOTS = ['Matin\n6h–10h','Midi\n10h–14h','Après-midi\n14h–18h','Soir\n18h–22h']
hmap = [[0]*4 for _ in range(7)]
for a in all_acts:
    if a['sport_type'] not in RUN: continue
    dt = datetime.fromisoformat(a['start_local'])
    day  = dt.weekday()   # 0=Lun
    hour = dt.hour
    if   6  <= hour < 10: slot = 0
    elif 10 <= hour < 14: slot = 1
    elif 14 <= hour < 18: slot = 2
    elif 18 <= hour < 22: slot = 3
    else: continue  # nuit (rare)
    hmap[day][slot] += 1

print("\n// heatmap[jour][créneau] = nb séances")
for j, row in enumerate(hmap):
    print(f"// {JOURS[j]}: {row}")
print(f"heatmap = {hmap}")

# ── 3. ZONES D'INTENSITÉ (RE/h comme proxy FC) ──
# Calibration sur données connues (FC observée vs RE/h):
#  RE/h < 130 → Z1-Z2 (endurance)  FC < 150
#  130–200    → Z2-Z3 (aérobie)    FC 150-163
#  200–280    → Z4 (seuil)         FC 163-176
#  > 280      → Z5 (haute int.)    FC > 176
zones = {'Z1-Z2 Endurance':0, 'Z2-Z3 Aérobie':0, 'Z4 Seuil':0, 'Z5 Haute Int.':0}
zones_h = {'Z1-Z2 Endurance':0., 'Z2-Z3 Aérobie':0., 'Z4 Seuil':0., 'Z5 Haute Int.':0.}
total_h = 0
for a in all_acts:
    if a['sport_type'] not in RUN: continue
    s = a['summary']
    re = s.get('relative_effort') or 0
    mt = s.get('moving_time') or 0
    if re == 0 or mt == 0: continue
    h = mt / 3600
    reph = re / h
    if   reph < 130: z = 'Z1-Z2 Endurance'
    elif reph < 200: z = 'Z2-Z3 Aérobie'
    elif reph < 280: z = 'Z4 Seuil'
    else:            z = 'Z5 Haute Int.'
    zones[z]   += 1
    zones_h[z] += h
    total_h    += h

print(f"\n// Zones d'intensité (nb séances / temps total)")
for z, n in zones.items():
    h = zones_h[z]
    print(f"// {z}: {n} séances · {h:.1f}h · {h/total_h*100:.0f}%")

print(f"\nzoneNames  = {list(zones.keys())}")
print(f"zoneCounts = {list(zones.values())}")
print(f"zoneHours  = {[round(h,1) for h in zones_h.values()]}")

# ── 4. DAILY RE pour CTL/ATL/TSB et Monotonie ──
weekly_re = [1289,1238,960,1353,1447,1479,1378,1249,1550,1419,600,2567,297,399,1053,1062,900,1135,1000,788,1195,1038,758,675,471,202,59]
print(f"\n// CTL/ATL/TSB calculés en JS depuis reData")
print(f"// kATL = exp(-7/7) = {math.exp(-7/7):.4f}")
print(f"// kCTL = exp(-7/42) = {math.exp(-7/42):.4f}")

# ── 5. TEMPÉRATURE HEBDO (Enduraw Heat descriptions) ──
import re as _re
temp_pattern = _re.compile(r'Heat \((\d+\.?\d*)°C\)')
wk_temp_max = {}
for a in all_acts:
    if a['sport_type'] not in RUN: continue
    desc = a.get('description', '') or ''
    m = temp_pattern.search(desc)
    if m:
        t = float(m.group(1))
        dt = datetime.fromisoformat(a['start_local'])
        mon = (dt - timedelta(days=dt.weekday())).strftime('%d/%m')
        wk_temp_max[mon] = max(wk_temp_max.get(mon, 0), t)

# Compléter avec les données connues (P2 ne contient pas les descriptions complètes)
known_temps = {
    '04/05': 20.0, '11/05': 20.0,
    '18/05': 28.9, '25/05': 30.5,
    '01/06': 19.4, '08/06': 20.1,
    '15/06': 32.1, '22/06': 35.7, '29/06': 25.7,
}
for w, t in known_temps.items():
    if w not in wk_temp_max or wk_temp_max[w] < t:
        wk_temp_max[w] = t

wkMaxTemp = [round(wk_temp_max[w], 1) if w in wk_temp_max else 'null' for w in weeks_order]
print(f"\nwkMaxTemp = [{','.join(str(v) for v in wkMaxTemp)}]")

# ── 6. STATS GLOBALES ──
run_trail = [a for a in all_acts if a['sport_type'] in RUN]
total_km  = round(sum(a['summary'].get('distance',0) for a in run_trail)/1000, 0)
total_elev = int(sum(a['summary'].get('elevation_gain',0) for a in run_trail))
total_cals = int(sum(a['summary'].get('total_calories',0) or 0 for a in all_acts))
print(f"\n// Totaux: {total_km} km · {total_elev} m D+ · {total_cals} kcal · {len(run_trail)} séances run+trail")
