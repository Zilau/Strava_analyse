import sys, re
sys.stdout.reconfigure(encoding='utf-8')

HTML = r'c:\Users\lmiklic\repository\Strava_analyse\rapport_performance.html'
content = open(HTML, encoding='utf-8').read()

# ── 1. Bouton nav ──
old_btn = '<button id="btn-lexique" class="tab-btn" onclick="showTab(\'lexique\')">Lexique</button>'
new_btn = old_btn + '\n    <button id="btn-plan" class="tab-btn" onclick="showTab(\'plan\')">Plan Échappée Belle</button>'
assert old_btn in content, 'btn-lexique not found'
content = content.replace(old_btn, new_btn, 1)

# ── 2. showTab ──
old_show = "['global','courses','entrainement','carte','lexique'].forEach"
new_show = "['global','courses','entrainement','carte','lexique','plan'].forEach"
assert old_show in content, 'showTab array not found'
content = content.replace(old_show, new_show, 1)

# ── 3. Pane HTML ──
PANE = """
<div id="pane-plan" class="max-w-5xl mx-auto space-y-5" style="display:none">

  <div class="bg-gradient-to-r from-orange-600 to-amber-500 rounded-2xl p-5 text-white shadow-lg">
    <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
      <div>
        <h1 class="text-2xl font-bold tracking-tight">&#127956; Plan — Maratrail de l'Échappée Belle</h1>
        <p class="text-orange-100 mt-1">~43 km · ~2 500 m D+ · Massif de Belledonne · <strong>Samedi 22 août 2026</strong></p>
      </div>
      <div class="text-center bg-white/20 rounded-xl px-5 py-3">
        <div id="plan-countdown" class="text-3xl font-black tabular-nums">—</div>
        <div class="text-xs text-orange-100 uppercase tracking-wider mt-1">jours restants</div>
      </div>
    </div>
  </div>

  <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
    <div class="bg-slate-800 rounded-xl p-4">
      <div class="text-xs text-slate-400 uppercase tracking-wider mb-1">Objectif A</div>
      <div class="text-2xl font-bold text-orange-400">sub 6h30</div>
      <div class="text-xs text-slate-400 mt-1">~9:04/km · 75–80% FCmax</div>
    </div>
    <div class="bg-slate-800 rounded-xl p-4">
      <div class="text-xs text-slate-400 uppercase tracking-wider mb-1">Objectif B</div>
      <div class="text-2xl font-bold text-amber-400">sub 7h00</div>
      <div class="text-xs text-slate-400 mt-1">~9:46/km · 70–75% FCmax</div>
    </div>
    <div class="bg-slate-800 rounded-xl p-4">
      <div class="text-xs text-slate-400 uppercase tracking-wider mb-1">Allure D+ cible</div>
      <div class="text-2xl font-bold text-green-400">~7 min/100m</div>
      <div class="text-xs text-slate-400 mt-1">+2 500m → +175 min vs plat</div>
    </div>
  </div>

  <div class="bg-slate-800 rounded-xl p-4">
    <h2 class="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3">Bilan de forme au départ du plan (18 juin)</h2>
    <div class="grid grid-cols-2 md:grid-cols-4 gap-3 text-center">
      <div><div class="text-xl font-bold text-orange-400">0,82</div><div class="text-xs text-slate-400">ACWR · zone optimale</div></div>
      <div><div class="text-xl font-bold text-green-400">48:06</div><div class="text-xs text-slate-400">PR 10km (14 juin)</div></div>
      <div><div class="text-xl font-bold text-blue-400">50 km/sem</div><div class="text-xs text-slate-400">Volume actuel</div></div>
      <div><div class="text-xl font-bold text-purple-400">85 km/sem</div><div class="text-xs text-slate-400">Capacité prouvée jan–mars</div></div>
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
            <th class="text-center py-2 px-2 font-medium">D+</th>
            <th class="text-center py-2 px-2 font-medium">RE cible</th>
            <th class="text-left py-2 px-2 font-medium">Séances clés</th>
            <th class="text-left py-2 pl-2 font-medium">Focus</th>
          </tr>
        </thead>
        <tbody id="plan-tbody"></tbody>
      </table>
    </div>
  </div>

  <div class="bg-slate-800 rounded-xl p-4">
    <h2 class="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3">Séances types</h2>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
      <div class="bg-slate-700/50 rounded-lg p-3">
        <div class="flex items-center gap-2 mb-1">
          <span class="text-xs font-bold bg-orange-500 text-white rounded px-1.5 py-0.5">FC+</span>
          <span class="text-sm font-semibold text-slate-200">Fractionné côte</span>
        </div>
        <p class="text-xs text-slate-400">3×(8×100m&#8599;50m&#8600;) ou 4×(5×150m&#8599;) · FC Z4–Z5 · cadence ↑ · simulation D+</p>
      </div>
      <div class="bg-slate-700/50 rounded-lg p-3">
        <div class="flex items-center gap-2 mb-1">
          <span class="text-xs font-bold bg-blue-500 text-white rounded px-1.5 py-0.5">FL</span>
          <span class="text-sm font-semibold text-slate-200">Fractionné long seuil</span>
        </div>
        <p class="text-xs text-slate-400">3×3 000m ou 2×4 000m à 5:00–5:15/km · FC Z4 (155–170 bpm) · puissance aérobie</p>
      </div>
      <div class="bg-slate-700/50 rounded-lg p-3">
        <div class="flex items-center gap-2 mb-1">
          <span class="text-xs font-bold bg-green-600 text-white rounded px-1.5 py-0.5">SLT</span>
          <span class="text-sm font-semibold text-slate-200">Sortie longue trail</span>
        </div>
        <p class="text-xs text-slate-400">25–38 km avec D+ ciblé · FC Z2–Z3 (128–155 bpm) · gestion descentes · nutrition</p>
      </div>
      <div class="bg-slate-700/50 rounded-lg p-3">
        <div class="flex items-center gap-2 mb-1">
          <span class="text-xs font-bold bg-purple-500 text-white rounded px-1.5 py-0.5">B2B</span>
          <span class="text-sm font-semibold text-slate-200">Back-to-back weekend</span>
        </div>
        <p class="text-xs text-slate-400">Sam trail long D+ · Dim footing récupération 10–12 km Z2 · simulation fatigue race</p>
      </div>
      <div class="bg-slate-700/50 rounded-lg p-3">
        <div class="flex items-center gap-2 mb-1">
          <span class="text-xs font-bold bg-red-500 text-white rounded px-1.5 py-0.5">SIM</span>
          <span class="text-sm font-semibold text-slate-200">Simulation race</span>
        </div>
        <p class="text-xs text-slate-400">30–35 km trail ~1 500 m D+, effort contrôlé 75–80% FCmax · protocole nutrition et hydratation race-day</p>
      </div>
      <div class="bg-slate-700/50 rounded-lg p-3">
        <div class="flex items-center gap-2 mb-1">
          <span class="text-xs font-bold bg-slate-500 text-white rounded px-1.5 py-0.5">Z2</span>
          <span class="text-sm font-semibold text-slate-200">Footing endurance</span>
        </div>
        <p class="text-xs text-slate-400">10–14 km · FC &lt;145 bpm · récupération active · boucles habituelles</p>
      </div>
    </div>
  </div>

  <div class="bg-slate-800 rounded-xl p-4">
    <h2 class="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3">Points de vigilance</h2>
    <ul class="space-y-2 text-sm text-slate-300">
      <li class="flex gap-2"><span class="text-orange-400 font-bold shrink-0">&#9888;</span><span><strong>Volume D+ :</strong> Prépa ETP120 très orientée plat/route. Augmenter le D+ progressivement max +300 m/sem pour prévenir les douleurs tendineuses.</span></li>
      <li class="flex gap-2"><span class="text-orange-400 font-bold shrink-0">&#9888;</span><span><strong>Chaleur estivale :</strong> Juil–août en IDF, températures souvent &gt;25°C. Réduire l'allure de 10–15 s/km par 5°C au-dessus de 15°C. Hydratation +0,5 L/h vs standard.</span></li>
      <li class="flex gap-2"><span class="text-orange-400 font-bold shrink-0">&#9888;</span><span><strong>Descente technique :</strong> 2 500 m de D+ implique autant de D−. Intégrer des séances descente rapide (cf. stage trail mai). FC basse mais quadriceps très sollicités.</span></li>
      <li class="flex gap-2"><span class="text-green-400 font-bold shrink-0">&#10003;</span><span><strong>Point fort :</strong> 21h en mouvement à l'ETP120 — l'endurance de base est là. L'enjeu est la spécificité D+ et la gestion de l'effort sur 6h.</span></li>
      <li class="flex gap-2"><span class="text-green-400 font-bold shrink-0">&#10003;</span><span><strong>Cycle 3:1 :</strong> La semaine de récupération S4 (14–20 juil.) est obligatoire — leçon de la prépa ETP120 où les récups étaient trop rares sur 8 semaines consécutives.</span></li>
    </ul>
  </div>

</div>

"""

assert '<div id="legend-tip"' in content, 'legend-tip anchor not found'
content = content.replace('<div id="legend-tip"', PANE + '<div id="legend-tip"', 1)

# ── 4. JS du plan ──
JS = r"""
// ── PLAN ÉCHAPPÉE BELLE ──
(function() {
  var race = new Date('2026-08-22');
  var today = new Date(); today.setHours(0,0,0,0);
  var days = Math.round((race - today) / 86400000);
  var el = document.getElementById('plan-countdown');
  if (el) el.textContent = days;

  var weeks = [
    { label:'S0  16–22 juin', phase:'En cours',     km:20,  dp:100,  re:350,  sessions:['Z2','FC+ côte'],                        focus:'Semaine partielle · conserver l\'élan post-course' },
    { label:'S1  23–29 juin', phase:'Bloc 1',        km:55,  dp:600,  re:950,  sessions:['FC+','Z2','Z2','SLT 22km D+400'],        focus:'Réintroduire D+ · +10 km vs sem. précédente' },
    { label:'S2  30–6 juil.', phase:'Bloc 1',        km:62,  dp:900,  re:1080, sessions:['FL 3×3km','Z2','Z2','SLT 28km D+700'],   focus:'Volume trail ↑ · surveiller tendons' },
    { label:'S3  7–13 juil.', phase:'Bloc 1',        km:70,  dp:1200, re:1250, sessions:['FC+','FL 2×4km','Z2','SLT 32km D+1000'], focus:'Sortie longue >3h · gestion alimentation' },
    { label:'S4  14–20 juil.',phase:'Récupération',  km:45,  dp:500,  re:750,  sessions:['Z2','Z2','Z2','FC+ léger'],              focus:'⭐ Décharge obligatoire · ACWR cible <0,85' },
    { label:'S5  21–27 juil.',phase:'Bloc 2',        km:72,  dp:1500, re:1280, sessions:['FC+','FL 3×3km','B2B Sam+Dim'],          focus:'Back-to-back · simulation fatigue j+1' },
    { label:'S6  28–3 août',  phase:'Bloc 2',        km:78,  dp:1800, re:1420, sessions:['FC+','Z2','SIM 35km D+1500'],            focus:'⭐ Simulation race complète · nutrition' },
    { label:'S7  4–10 août',  phase:'Bloc 2',        km:65,  dp:1200, re:1150, sessions:['FL 2×3km','Z2','Z2','SLT 28km D+900'],  focus:'Maintenir qualité · réduire volume' },
    { label:'S8  11–17 août', phase:'Affûtage',      km:40,  dp:600,  re:700,  sessions:['FC+ court','FL 2×2km','Z2','Z2'],       focus:'-40% volume · conserver 2 séances qualité' },
    { label:'S9  18–22 août', phase:'Race week',     km:12,  dp:100,  re:200,  sessions:['Z2 30min','J-1 déblocage','RACE !!!'],   focus:'Repos actif · protocole pré-course' },
  ];

  var phaseColors = {
    'En cours'   :'text-slate-300 bg-slate-700',
    'Bloc 1'     :'text-blue-300 bg-blue-900/50',
    'Récupération':'text-amber-300 bg-amber-900/50',
    'Bloc 2'     :'text-orange-300 bg-orange-900/50',
    'Affûtage'   :'text-purple-300 bg-purple-900/50',
    'Race week'  :'text-red-300 bg-red-900/50'
  };

  var sessionColors = {
    'FC+':'bg-orange-800 text-orange-200',
    'FL' :'bg-blue-800 text-blue-200',
    'SLT':'bg-green-800 text-green-200',
    'B2B':'bg-green-700 text-green-100',
    'SIM':'bg-red-800 text-red-200',
    'Z2' :'bg-slate-700 text-slate-300',
    'RAC':'bg-yellow-600 text-yellow-100'
  };

  function sessionClass(s) {
    if (s.startsWith('FC+')) return sessionColors['FC+'];
    if (s.startsWith('FL'))  return sessionColors['FL'];
    if (s.startsWith('SLT')) return sessionColors['SLT'];
    if (s.startsWith('B2B')) return sessionColors['B2B'];
    if (s.startsWith('SIM')) return sessionColors['SIM'];
    if (s.startsWith('RACE')) return sessionColors['RAC'] + ' font-bold';
    return sessionColors['Z2'];
  }

  var tbody = document.getElementById('plan-tbody');
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
      '<td class="text-center py-2.5 px-2 font-bold text-orange-400">' + w.km + '</td>' +
      '<td class="text-center py-2.5 px-2 font-bold text-green-400">' + (w.dp > 0 ? '+' + w.dp : '—') + '</td>' +
      '<td class="text-center py-2.5 px-2 text-blue-300">' + w.re + '</td>' +
      '<td class="py-2.5 px-2">' + badges + '</td>' +
      '<td class="py-2.5 pl-2 text-xs text-slate-400">' + w.focus + '</td>';
    tbody.appendChild(tr);
  });
})();
"""

assert '</script>' in content, '</script> not found'
content = content.replace('</script>', JS + '\n</script>', 1)

open(HTML, 'w', encoding='utf-8').write(content)
print('OK')
