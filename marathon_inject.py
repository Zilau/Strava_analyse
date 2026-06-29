import sys, re
sys.stdout.reconfigure(encoding='utf-8')

HTML = r'c:\Users\lmiklic\repository\Strava_analyse\rapport_performance.html'
content = open(HTML, encoding='utf-8').read()

# ── 1. Bouton nav ──
old_btn = '<button id="btn-plan" class="tab-btn" onclick="showTab(\'plan\')">Plan Échappée Belle</button>'
new_btn = old_btn + '\n    <button id="btn-marathon" class="tab-btn" onclick="showTab(\'marathon\')">Plan Marathon NC</button>'
assert old_btn in content, 'btn-plan not found'
content = content.replace(old_btn, new_btn, 1)

# ── 2. showTab ──
old_show = "['global','courses','entrainement','carte','lexique','plan'].forEach"
new_show = "['global','courses','entrainement','carte','lexique','plan','marathon'].forEach"
assert old_show in content, 'showTab array not found'
content = content.replace(old_show, new_show, 1)

# ── 3. Pane HTML ──
PANE = """
<div id="pane-marathon" class="max-w-5xl mx-auto space-y-5" style="display:none">

  <div class="bg-gradient-to-r from-blue-700 to-cyan-600 rounded-2xl p-5 text-white shadow-lg">
    <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
      <div>
        <h1 class="text-2xl font-bold tracking-tight">&#127939; Plan — Marathon Nice-Cannes</h1>
        <p class="text-blue-100 mt-1">42,195 km · bord de mer · <strong>Dimanche 25 octobre 2026</strong> <span class="text-xs opacity-75">(date estimée)</span></p>
      </div>
      <div class="text-center bg-white/20 rounded-xl px-5 py-3">
        <div id="marathon-countdown" class="text-3xl font-black tabular-nums">—</div>
        <div class="text-xs text-blue-100 uppercase tracking-wider mt-1">jours restants</div>
      </div>
    </div>
  </div>

  <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
    <div class="bg-slate-800 rounded-xl p-4">
      <div class="text-xs text-slate-400 uppercase tracking-wider mb-1">Objectif</div>
      <div class="text-2xl font-bold text-cyan-400">sub 4h00</div>
      <div class="text-xs text-slate-400 mt-1">5:41/km exact</div>
    </div>
    <div class="bg-slate-800 rounded-xl p-4">
      <div class="text-xs text-slate-400 uppercase tracking-wider mb-1">Allure tempo cible</div>
      <div class="text-2xl font-bold text-blue-400">5:20–5:30/km</div>
      <div class="text-xs text-slate-400 mt-1">seuil lactique Z4</div>
    </div>
    <div class="bg-slate-800 rounded-xl p-4">
      <div class="text-xs text-slate-400 uppercase tracking-wider mb-1">Long runs cible</div>
      <div class="text-2xl font-bold text-green-400">5:50–6:00/km</div>
      <div class="text-xs text-slate-400 mt-1">Z2–Z3 · finales à allure M</div>
    </div>
  </div>

  <div class="bg-slate-800 rounded-xl p-4">
    <h2 class="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3">Profil de performance — projection sub 4h</h2>
    <div class="grid grid-cols-2 md:grid-cols-4 gap-3 text-center">
      <div>
        <div class="text-xl font-bold text-orange-400">48:06</div>
        <div class="text-xs text-slate-400">PR 10km (14 juin)</div>
        <div class="text-xs text-slate-500 mt-0.5">prédit M ≈ 4h02</div>
      </div>
      <div>
        <div class="text-xl font-bold text-cyan-400">5:41/km</div>
        <div class="text-xs text-slate-400">allure cible race</div>
        <div class="text-xs text-slate-500 mt-0.5">+54s/km vs 10km</div>
      </div>
      <div>
        <div class="text-xl font-bold text-green-400">9 sem.</div>
        <div class="text-xs text-slate-400">entre les 2 courses</div>
        <div class="text-xs text-slate-500 mt-0.5">dont 2 sem. récup</div>
      </div>
      <div>
        <div class="text-xl font-bold text-purple-400">184 bpm</div>
        <div class="text-xs text-slate-400">FCmax mesurée</div>
        <div class="text-xs text-slate-500 mt-0.5">cible race 75–80%</div>
      </div>
    </div>
    <div class="mt-3 p-3 bg-amber-900/30 border border-amber-700/50 rounded-lg text-xs text-amber-200">
      <strong>Point clé :</strong> la formule Riegel donne 4h02 avec ton 10km actuel. Avec 7 semaines de travail route-spécifique post-récup, sub 4h00 est atteignable — sous réserve que l'Échappée Belle se passe sans blessure et que tu assures les 2 semaines de récupération complète.
    </div>
  </div>

  <div class="bg-slate-800 rounded-xl p-4">
    <h2 class="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-4">Plan semaine par semaine</h2>
    <div class="overflow-x-auto">
      <table class="w-full text-sm border-collapse">
        <thead>
          <tr class="text-xs text-slate-400 uppercase tracking-wider border-b border-slate-700">
            <th class="text-left py-2 pr-3 font-medium">Semaine</th>
            <th class="text-center py-2 px-2 font-medium">Km</th>
            <th class="text-center py-2 px-2 font-medium">RE cible</th>
            <th class="text-left py-2 px-2 font-medium">Séances clés</th>
            <th class="text-left py-2 pl-2 font-medium">Focus</th>
          </tr>
        </thead>
        <tbody id="marathon-tbody"></tbody>
      </table>
    </div>
  </div>

  <div class="bg-slate-800 rounded-xl p-4">
    <h2 class="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3">Séances types marathon</h2>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
      <div class="bg-slate-700/50 rounded-lg p-3">
        <div class="flex items-center gap-2 mb-1">
          <span class="text-xs font-bold bg-cyan-700 text-cyan-200 rounded px-1.5 py-0.5">TMP</span>
          <span class="text-sm font-semibold text-slate-200">Tempo marathon</span>
        </div>
        <p class="text-xs text-slate-400">12–18 km à 5:41/km exact · FC 155–165 bpm · "effort confortable mais soutenu" · chaussures de course</p>
      </div>
      <div class="bg-slate-700/50 rounded-lg p-3">
        <div class="flex items-center gap-2 mb-1">
          <span class="text-xs font-bold bg-blue-700 text-blue-200 rounded px-1.5 py-0.5">FSE</span>
          <span class="text-sm font-semibold text-slate-200">Fractionné seuil</span>
        </div>
        <p class="text-xs text-slate-400">4–6×1 500m à 5:00–5:10/km ou 3×3 km à 5:15/km · récup 90s · FC Z4 (165–175 bpm)</p>
      </div>
      <div class="bg-slate-700/50 rounded-lg p-3">
        <div class="flex items-center gap-2 mb-1">
          <span class="text-xs font-bold bg-green-700 text-green-200 rounded px-1.5 py-0.5">SLR</span>
          <span class="text-sm font-semibold text-slate-200">Sortie longue route</span>
        </div>
        <p class="text-xs text-slate-400">26–32 km à 5:50–6:00/km · 5 derniers km à 5:41/km · ravitaillement toutes les 45 min · chaussures race</p>
      </div>
      <div class="bg-slate-700/50 rounded-lg p-3">
        <div class="flex items-center gap-2 mb-1">
          <span class="text-xs font-bold bg-purple-700 text-purple-200 rounded px-1.5 py-0.5">PGS</span>
          <span class="text-sm font-semibold text-slate-200">Progression sur SL</span>
        </div>
        <p class="text-xs text-slate-400">22–28 km : 1/3 à 6:00, 1/3 à 5:45, 1/3 à 5:30 · simule la gestion de course · fort mentalement</p>
      </div>
      <div class="bg-slate-700/50 rounded-lg p-3">
        <div class="flex items-center gap-2 mb-1">
          <span class="text-xs font-bold bg-slate-500 text-slate-300 rounded px-1.5 py-0.5">REC</span>
          <span class="text-sm font-semibold text-slate-200">Récupération active</span>
        </div>
        <p class="text-xs text-slate-400">8–12 km · FC &lt;140 bpm · 6:00–6:30/km · route plate · jamais de dénivelé post-Échappée Belle</p>
      </div>
      <div class="bg-slate-700/50 rounded-lg p-3">
        <div class="flex items-center gap-2 mb-1">
          <span class="text-xs font-bold bg-orange-700 text-orange-200 rounded px-1.5 py-0.5">AMR</span>
          <span class="text-sm font-semibold text-slate-200">Allure marathon rapide</span>
        </div>
        <p class="text-xs text-slate-400">20 km dont 15 km à 5:35/km (légèrement sous allure) · "banque de confiance" · à faire une seule fois S6</p>
      </div>
    </div>
  </div>

  <div class="bg-slate-800 rounded-xl p-4">
    <h2 class="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3">Points de vigilance</h2>
    <ul class="space-y-2 text-sm text-slate-300">
      <li class="flex gap-2"><span class="text-red-400 font-bold shrink-0">&#9888;</span><span><strong>Récupération Échappée Belle :</strong> Ne pas rogner sur les 2 semaines de récup (S1–S2). Un ultra trail de 43 km D+2 500m cause des micro-lésions musculaires importantes — reprendre trop tôt = blessure garantie S5–S6.</span></li>
      <li class="flex gap-2"><span class="text-orange-400 font-bold shrink-0">&#9888;</span><span><strong>Passage trail → route :</strong> Tes chevilles et tibias vont ressentir le changement de surface. Introduire les chaussures route progressivement S3, et surveiller les tibias antérieurs les 2 premières semaines.</span></li>
      <li class="flex gap-2"><span class="text-orange-400 font-bold shrink-0">&#9888;</span><span><strong>Pacing en course :</strong> Ton profil trail = partir trop vite au ressenti. Départ obligatoirement à 5:50/km les 5 premiers km. Le marathon se gagne au 30ème km, pas au départ.</span></li>
      <li class="flex gap-2"><span class="text-green-400 font-bold shrink-0">&#10003;</span><span><strong>Endurance de base :</strong> 21h de mouvement à l'ETP120 + Échappée Belle = tu finiras le marathon. La question est l'allure. La priorité absolue est le travail à allure marathon spécifique.</span></li>
      <li class="flex gap-2"><span class="text-green-400 font-bold shrink-0">&#10003;</span><span><strong>Parcours favorable :</strong> Nice-Cannes est quasi plat (D+ ≈ 130m total). Après 2 500m D+ à l'Échappée Belle, les jambes apprécieront.</span></li>
      <li class="flex gap-2"><span class="text-blue-400 font-bold shrink-0">&#9432;</span><span><strong>Nutrition :</strong> 1 gel toutes les 40 min minimum dès le km 10 (soit ~5 gels + 1 gel coup de boost km 37). Tester le protocole sur les SLR avant la course.</span></li>
    </ul>
  </div>

</div>

"""

assert '<div id="legend-tip"' in content, 'legend-tip anchor not found'
content = content.replace('<div id="legend-tip"', PANE + '<div id="legend-tip"', 1)

# ── 4. JS du plan marathon ──
JS = r"""
// ── PLAN MARATHON NICE-CANNES ──
(function() {
  var race = new Date('2026-10-25');
  var today = new Date(); today.setHours(0,0,0,0);
  var days = Math.round((race - today) / 86400000);
  var el = document.getElementById('marathon-countdown');
  if (el) el.textContent = days;

  var weeks = [
    { label:'S1  24–30 août',   phase:'Récupération',   km:15,  re:200,  sessions:['REC','REC','repos'],                         focus:'Jambes vides post-Echappee Belle · marche OK' },
    { label:'S2  31 a–6 sep',   phase:'Récupération',   km:30,  re:380,  sessions:['REC','REC','REC','REC'],                     focus:'Retour running · FC <140 bpm absolument' },
    { label:'S3  7–13 sep',     phase:'Transition',     km:45,  re:600,  sessions:['REC','FSE court','REC','SLR 18km'],           focus:'Premier contact route · FSE très contrôlé' },
    { label:'S4  14–20 sep',    phase:'Build 1',        km:58,  re:800,  sessions:['REC','FSE 4x1500m','TMP 12km','SLR 22km'],   focus:'Ancrer l\'allure 5:41 dans les jambes' },
    { label:'S5  21–27 sep',    phase:'Build 1',        km:65,  re:900,  sessions:['REC','FSE 3x3km','TMP 15km','PGS 26km'],     focus:'PGS = simulation gestion de course' },
    { label:'S6  28–4 oct',     phase:'Build 2',        km:72,  re:1000, sessions:['REC','AMR 20km','REC','SLR 30km'],           focus:'AMR : 15km sous allure · booster la confiance' },
    { label:'S7  5–11 oct',     phase:'Pic',            km:75,  re:1050, sessions:['REC','FSE 4x1500m','TMP 18km','SLR 32km'],   focus:'SLR 32km = sortie cle du cycle · nutrition test' },
    { label:'S8  12–18 oct',    phase:'Affutage',       km:48,  re:650,  sessions:['REC','FSE 3x1000m','TMP 10km','SLR 20km'],   focus:'-35% volume · maintenir allures · fraicheur' },
    { label:'S9  19–25 oct',    phase:'Race week',      km:15,  re:250,  sessions:['REC 5km','strides J-3','RACE !!!'],           focus:'Repos maximum · logistique course · RACE J25' },
  ];

  var phaseColors = {
    'Récupération':'text-amber-300 bg-amber-900/50',
    'Transition'  :'text-slate-300 bg-slate-700',
    'Build 1'     :'text-blue-300 bg-blue-900/50',
    'Build 2'     :'text-cyan-300 bg-cyan-900/50',
    'Pic'         :'text-orange-300 bg-orange-900/50',
    'Affutage'    :'text-purple-300 bg-purple-900/50',
    'Race week'   :'text-red-300 bg-red-900/50'
  };

  var sessionColors = {
    'TMP':'bg-cyan-800 text-cyan-200',
    'FSE':'bg-blue-800 text-blue-200',
    'SLR':'bg-green-800 text-green-200',
    'PGS':'bg-purple-800 text-purple-200',
    'AMR':'bg-orange-800 text-orange-200',
    'REC':'bg-slate-700 text-slate-300',
    'RAC':'bg-yellow-600 text-yellow-100'
  };

  function sessionClass(s) {
    if (s.startsWith('TMP'))  return sessionColors['TMP'];
    if (s.startsWith('FSE'))  return sessionColors['FSE'];
    if (s.startsWith('SLR'))  return sessionColors['SLR'];
    if (s.startsWith('PGS'))  return sessionColors['PGS'];
    if (s.startsWith('AMR'))  return sessionColors['AMR'];
    if (s.startsWith('RACE')) return sessionColors['RAC'] + ' font-bold';
    return sessionColors['REC'];
  }

  var tbody = document.getElementById('marathon-tbody');
  if (!tbody) return;
  weeks.forEach(function(w) {
    var tr = document.createElement('tr');
    tr.className = 'border-b border-slate-700/50 hover:bg-slate-700/30 transition-colors';
    var phaseCls = phaseColors[w.phase] || 'text-slate-300 bg-slate-700';
    var badges = w.sessions.map(function(s) {
      return '<span class="inline-block text-xs rounded px-1.5 py-0.5 mr-1 mb-0.5 ' + sessionClass(s) + '">' + s + '</span>';
    }).join('');
    tr.innerHTML =
      '<td class="py-2.5 pr-3 font-medium text-slate-200 whitespace-nowrap">' +
        '<div>' + w.label + '</div>' +
        '<div class="mt-0.5"><span class="text-xs rounded px-1.5 py-0.5 ' + phaseCls + '">' + w.phase + '</span></div>' +
      '</td>' +
      '<td class="text-center py-2.5 px-2 font-bold text-cyan-400">' + w.km + '</td>' +
      '<td class="text-center py-2.5 px-2 text-blue-300">' + w.re + '</td>' +
      '<td class="py-2.5 px-2">' + badges + '</td>' +
      '<td class="py-2.5 pl-2 text-xs text-slate-400">' + w.focus + '</td>';
    tbody.appendChild(tr);
  });
})();
"""

# Injecter avant la fermeture du script principal (juste avant </script>\n</body>)
anchor = '})();\n</script>\n</body>'
assert anchor in content, 'main script closing anchor not found'
content = content.replace(anchor, '})();\n' + JS + '\n</script>\n</body>', 1)

open(HTML, 'w', encoding='utf-8').write(content)
print('OK')
