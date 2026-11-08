"""Erzeugt docs/index.html (GitHub Pages) aus dem Zustand des Screeners."""
from __future__ import annotations

import json
from pathlib import Path

TEMPLATE = r"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Meme-Screener</title>
<style>
/* Layout: Apple-Stil – große Titel, gruppierte Karten auf grauem Grund, Systemschrift, Systemfarben.
   Oben eine durchscheinende Leiste mit Abschnittsnavigation; darunter Depot-Widgets, Kurve, Tabellen. */
:root{
  --bg:#f2f2f7; --surface:#ffffff; --fill:#f2f2f7; --fg:#1c1c1e; --muted:#6e6e73; --line:#e5e5ea;
  --accent:#007aff; --accent-soft:#e5f0ff; --good:#248a3d; --bad:#d70015; --warn:#c93400;
  --display:-apple-system,BlinkMacSystemFont,"SF Pro Display","Helvetica Neue",system-ui,"Segoe UI",Roboto,sans-serif;
  --body:-apple-system,BlinkMacSystemFont,"SF Pro Text","Helvetica Neue",system-ui,"Segoe UI",Roboto,sans-serif;
  --mono:-apple-system,BlinkMacSystemFont,"SF Pro Text","Helvetica Neue",system-ui,"Segoe UI",Roboto,sans-serif;
  --shadow:0 1px 2px rgba(0,0,0,.04),0 4px 16px rgba(0,0,0,.04);
  --gutter:max(16px,env(safe-area-inset-left)); --gutter-r:max(16px,env(safe-area-inset-right));
  color-scheme:light;
}
@media (prefers-color-scheme:dark){:root{
  --bg:#000000; --surface:#1c1c1e; --fill:#2c2c2e; --fg:#f5f5f7; --muted:#98989d; --line:#38383a;
  --accent:#0a84ff; --accent-soft:#0b2a4a; --good:#30d158; --bad:#ff453a; --warn:#ff9f0a;
  --shadow:none; color-scheme:dark}}
*{box-sizing:border-box}
html,body{margin:0}
html{scroll-behavior:smooth}
body{background:var(--bg);color:var(--fg);font:15px/1.47 var(--body);letter-spacing:-.01em;
  -webkit-font-smoothing:antialiased;padding:0 0 56px}
.topbar{position:sticky;top:0;z-index:10;padding-top:env(safe-area-inset-top);
  background:color-mix(in srgb,var(--bg) 78%,transparent);
  -webkit-backdrop-filter:saturate(180%) blur(20px);backdrop-filter:saturate(180%) blur(20px);
  border-bottom:.5px solid var(--line)}
.topbar-in{max-width:1080px;margin:0 auto;padding:10px var(--gutter-r) 10px var(--gutter);
  display:flex;align-items:center;gap:16px;min-width:0}
.topbar-in strong{font:600 15px/1 var(--display);white-space:nowrap}
.seg{display:flex;gap:2px;padding:2px;border-radius:9px;background:var(--fill);overflow-x:auto;
  scrollbar-width:none;margin-left:auto;min-width:0;flex:0 1 auto;max-width:100%}
.seg::-webkit-scrollbar{display:none}
.seg a{flex:none;padding:5px 12px;border-radius:7px;font-size:13px;font-weight:500;color:var(--fg);text-decoration:none}
.seg a:hover{background:color-mix(in srgb,var(--surface) 70%,transparent)}
.seg a:focus-visible{outline:2px solid var(--accent);outline-offset:1px}
@media (max-width:560px){.topbar-in strong{display:none}.seg{margin-left:0}}
.wrap{max-width:1080px;margin:0 auto;display:grid;gap:36px;padding:28px var(--gutter-r) 0 var(--gutter)}
.wrap>*,.head>*{min-width:0}
section,header.head{scroll-margin-top:72px}
h1{font:700 clamp(30px,6vw,40px)/1.08 var(--display);margin:0;letter-spacing:-.025em;text-wrap:balance}
h2{font:700 22px/1.2 var(--display);margin:0 0 12px;letter-spacing:-.02em;text-wrap:balance}
.sub{color:var(--muted);font-size:13px}
.num{font-variant-numeric:tabular-nums}
.head{display:grid;gap:18px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}
.kpi{background:var(--surface);border-radius:16px;padding:14px 16px;box-shadow:var(--shadow);min-width:0}
.panel .kpi{background:var(--fill);box-shadow:none}
.kpi span{display:block;font-size:13px;color:var(--muted);font-weight:500}
.kpi b small{font:500 13px/1 var(--body);color:var(--muted);letter-spacing:0;margin-left:6px;white-space:nowrap}
.kpi b{display:block;font:600 24px/1.2 var(--display);letter-spacing:-.02em;margin-top:4px;font-variant-numeric:tabular-nums;
  overflow-wrap:anywhere}
.pos{color:var(--good)} .neg{color:var(--bad)}
.panel{background:var(--surface);border-radius:16px;padding:16px;box-shadow:var(--shadow)}
.panel.scroll{padding:6px 16px}
svg{display:block;width:100%;height:auto}
.scroll{overflow-x:auto;-webkit-overflow-scrolling:touch}
table{border-collapse:collapse;width:100%;font-size:14px;min-width:680px}
#cands{min-width:900px} #cands td:last-child{min-width:240px}
th{font-size:12px;color:var(--muted);text-align:left;font-weight:600;padding:10px 8px;border-bottom:.5px solid var(--line)}
td{padding:11px 8px;border-bottom:.5px solid var(--line);vertical-align:top}
tbody tr:last-child td{border-bottom:0}
tbody tr:hover td{background:color-mix(in srgb,var(--fill) 55%,transparent)}
td.r,th.r{text-align:right;white-space:nowrap}
a{color:var(--accent);text-decoration:none} a:hover{text-decoration:underline}
a:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:4px}
.score{display:inline-block;min-width:38px;text-align:center;font:600 13px/1 var(--body);font-variant-numeric:tabular-nums;
  padding:6px 7px;border-radius:8px;background:var(--accent-soft);color:var(--accent)}
.score.lo{background:var(--fill);color:var(--muted)}
.chip{display:inline-block;font-size:12px;padding:2px 8px;border-radius:6px;background:var(--fill);color:var(--muted);margin:3px 4px 0 0}
.chip.w{background:color-mix(in srgb,var(--warn) 13%,transparent);color:var(--warn)}
.chip.b{background:color-mix(in srgb,var(--bad) 13%,transparent);color:var(--bad)}
.sym{font-weight:600}
.ev{list-style:none;margin:0;padding:0;display:grid;font-size:14px}
.ev li{padding:10px 0;border-bottom:.5px solid var(--line)}
.ev li:last-child{border-bottom:0}
.ev time{color:var(--muted);font-size:13px;margin-right:10px;font-variant-numeric:tabular-nums}
.note{font-size:13px;color:var(--muted);max-width:68ch;margin:10px 4px 0}
.empty{color:var(--muted);font-size:14px;margin:0}
.live{display:flex;align-items:center;gap:7px;margin-top:4px}
.live::before{content:"";width:8px;height:8px;border-radius:50%;background:var(--good);
  box-shadow:0 0 0 0 color-mix(in srgb,var(--good) 55%,transparent);animation:pulse 2.4s ease-out infinite}
.live.off::before{background:var(--warn);animation:none}
@keyframes pulse{0%{box-shadow:0 0 0 0 color-mix(in srgb,var(--good) 55%,transparent)}70%,100%{box-shadow:0 0 0 7px transparent}}
@media (prefers-reduced-motion:reduce){.live::before{animation:none}html{scroll-behavior:auto}}
.agrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,320px),1fr));gap:24px;margin-top:20px}
.agrid h3,#atop h3{font:600 15px/1.3 var(--display);margin:0 0 6px}
.agrid table,#atop table{min-width:0;font-size:13px}
.agrid>div{overflow-x:auto;min-width:0;-webkit-overflow-scrolling:touch}
#atop{margin-top:24px}
.bar{height:5px;border-radius:3px;background:var(--accent);min-width:2px;margin-top:3px}
</style>
</head>
<body>
<div class="topbar"><div class="topbar-in">
  <strong>Meme-Screener</strong>
  <nav class="seg" aria-label="Abschnitte">
    <a href="#depot">Depot</a><a href="#kandidaten">Kandidaten</a><a href="#positionen">Positionen</a>
    <a href="#verkaeufe">Verkäufe</a><a href="#regeln">Regeln</a><a href="#auswertung">Auswertung</a>
  </nav>
</div></div>
<div class="wrap">
  <header class="head" id="depot">
    <div>
      <h1>Meme-Screener</h1>
      <div class="sub">Letzte Aktualisierung: <span id="lastrun"></span> · Chains: <span id="chains"></span></div>
      <div class="sub live" id="live" hidden></div>
    </div>
    <div class="kpis" id="kpis"></div>
    <div class="panel"><svg id="curve" viewBox="0 0 800 200" role="img" aria-label="Depotwert über Zeit"></svg></div>
  </header>

  <section id="kandidaten">
    <h2>Kandidaten heute</h2>
    <div class="panel scroll"><table id="cands"><thead><tr>
      <th>Score</th><th>Token</th><th class="r">MCap</th><th class="r">Liquidität</th><th class="r">Alter</th>
      <th class="r">24h</th><th class="r">Holder</th><th>Hinweise</th></tr></thead><tbody></tbody></table></div>
  </section>

  <section id="positionen">
    <h2>Offene Positionen</h2>
    <div class="panel scroll"><table id="open"><thead><tr>
      <th>Token</th><th>Gekauft</th><th class="r">Einsatz</th><th class="r">Wert</th><th class="r">Entwicklung</th>
      <th class="r">Hoch</th><th class="r">Realisiert</th></tr></thead><tbody></tbody></table></div>
    <p class="note">Kurse kommen beim Öffnen live von DEX Screener und werden jede Minute aktualisiert. Verkäufe nach den Depotregeln prüft das Depot stündlich, Käufe einmal täglich im Hauptlauf.</p>
  </section>

  <section id="verkaeufe">
    <h2>Verkäufe</h2>
    <div class="panel scroll"><table id="sales"><thead><tr>
      <th>Datum</th><th>Token</th><th class="r">Anteil</th><th class="r">Kurs</th><th class="r">Erlös</th><th>Grund</th><th>Status</th></tr></thead><tbody></tbody></table></div>
    <p class="note">Jeder Verkauf des Musterdepots, auch Teilverkäufe. „Anteil“ bezieht sich auf die ursprüngliche Positionsgröße, „Kurs“ auf den Kaufkurs.</p>
  </section>

  <section id="geschlossen">
    <h2>Geschlossene Positionen</h2>
    <div class="panel scroll"><table id="closed"><thead><tr>
      <th>Token</th><th>Zeitraum</th><th class="r">Einsatz</th><th class="r">Erlös</th><th class="r">Ergebnis</th><th>Grund</th>
      <th class="r">Hoch danach</th><th class="r">Heute</th><th class="r">Gehalten</th></tr></thead><tbody></tbody></table></div>
    <p class="note">Hier stehen nur komplett verkaufte Positionen. Teilverkäufe findest du unter „Verkäufe“.</p>
    <p class="note">Verkaufte Tokens werden unbegrenzt weiterverfolgt. „Hoch danach“ und „Heute“ zeigen den Kurs als Vielfaches des Kaufkurses. „Gehalten“ ist das Ergebnis, wenn die ganze Position bis heute gehalten worden wäre.</p>
  </section>

  <section id="regeln">
    <h2>Bilanz der Ausstiegsregeln</h2>
    <div class="panel scroll"><table id="rules"><thead><tr>
      <th>Regel</th><th class="r">Fälle</th><th class="r">Ergebnis tatsächlich</th><th class="r">Gehalten bis heute</th><th class="r">Differenz</th><th>Fazit</th></tr></thead><tbody></tbody></table></div>
    <p class="note">Positive Differenz: Der Verkauf hat gegenüber Halten Geld gerettet. Negative Differenz: Halten wäre besser gewesen. Erst nach einigen Wochen aussagekräftig.</p>
  </section>

  <section id="auswertung">
    <h2>Datenbank und Auswertung</h2>
    <div class="panel">
      <div class="kpis" id="dbkpis"></div>
      <p class="note" id="anote"></p>
      <div id="agroups" class="agrid"></div>
      <div id="atop"></div>
    </div>
  </section>

  <section id="bewegungen">
    <h2>Depot-Bewegungen</h2>
    <div class="panel"><ul class="ev" id="events"></ul></div>
  </section>

  <p class="note">Rein fiktives Musterdepot zur Überprüfung der Screener-Regeln. Keine Anlageberatung. Meme-Coins sind hochspekulativ; die meisten verlieren fast vollständig an Wert.</p>
</div>

<script id="data" type="application/json">__DATA__</script>
<script>
const D = JSON.parse(document.getElementById('data').textContent);
const eur = v => (v ?? 0).toLocaleString('de-DE',{maximumFractionDigits:0}) + ' €';
const usdShort = v => !v ? '–' : v >= 1e6 ? (v/1e6).toFixed(2).replace('.',',')+' M$' : (v/1e3).toFixed(0)+' k$';
const pct = v => v == null ? '–' : (v>0?'+':'') + v.toFixed(1).replace('.',',') + ' %';
const cls = v => v > 0 ? 'pos' : v < 0 ? 'neg' : '';
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const fmtDate = s => s ? s.split('-').reverse().join('.') : '–';

const fmtTs = t => t ? new Date(t).toLocaleString('de-DE',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}) : 'noch nie';
document.getElementById('lastrun').textContent = `${fmtTs((D.collect||{}).last||D.last_run)} · Hauptlauf ${fmtTs(D.last_run)}`;
document.getElementById('chains').textContent = D.chains.join(', ');

const pf = D.portfolio || {history:[],positions:[],closed:[],cash:D.start};
const hist = pf.history || [];
// aktueller USD→EUR-Kurs aus dem letzten Hauptlauf (Kaufkurs nur als Rückfallwert)
const fxOf = p => D.fx || p.eur_per_usd;
function renderKpis(){
  const openVal=(pf.positions||[]).reduce((t,p)=>t+p.units*p.price*fxOf(p),0);
  const last = D.portfolio ? (pf.cash||0)+openVal : D.start;
  // realisierter Gewinn: Erlös minus anteiliger Einsatz der verkauften Stücke (auch Teilverkäufe)
  const realizedPnl = p => {
    if(p.status!=='open') return (p.realized||0)-p.cost;
    const initial=p.cost/p.eur_per_usd/p.entry_price;
    const sold=(p.sales||[]).reduce((t,x)=>t+(x.units??0),0);
    return (p.realized||0)-(initial?p.cost*Math.min(1,sold/initial):0);
  };
  const realized = [...(pf.positions||[]),...(pf.closed||[])].reduce((t,p)=>t+realizedPnl(p),0);
  const wins = (pf.closed||[]).filter(p=>(p.realized||0)>p.cost).length;
  const partial = [...(pf.positions||[]),...(pf.closed||[])].reduce((t,p)=>t+(p.sales||[]).length,0)
                  - (pf.closed||[]).filter(p=>p.status!=='dead'&&(p.sales||[]).length).length;
  const kpis = [
    ['Depotwert', eur(last), ''],
    ['Seit Start', pct((last/D.start-1)*100), cls(last-D.start)],
    ['Offen', String((pf.positions||[]).length), ''],
    ['Komplett geschlossen', `${(pf.closed||[]).length}<small>${wins} im Plus</small>`, ''],
    ['Teilverkäufe', String(partial), ''],
    ['Realisierter Gewinn', eur(realized), cls(realized)],
  ];
  document.getElementById('kpis').innerHTML = kpis.map(([l,v,c])=>`<div class="kpi"><span>${l}</span><b class="${c}">${v}</b></div>`).join('');
}

// Depotkurve
(function(){
  const svg = document.getElementById('curve');
  const W = Math.max(300, Math.round(svg.getBoundingClientRect().width) || 800), H = W < 560 ? 180 : 220, P={l:56,r:12,t:12,b:24};
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  const pts = hist.length ? hist : [{date:'',total:D.start}];
  const vals = pts.map(p=>p.total).concat([D.start]);
  let lo=Math.min(...vals), hi=Math.max(...vals); if(hi-lo<1){hi+=50;lo-=50}
  const pad=(hi-lo)*.1; lo-=pad; hi+=pad;
  const x=i=>P.l+(pts.length<2?0:i*(W-P.l-P.r)/(pts.length-1));
  const y=v=>P.t+(hi-v)*(H-P.t-P.b)/(hi-lo);
  let s='';
  for(let k=0;k<=3;k++){const v=lo+(hi-lo)*k/3;s+=`<line x1="${P.l}" x2="${W-P.r}" y1="${y(v)}" y2="${y(v)}" stroke="var(--line)" stroke-dasharray="2 4"/><text x="${P.l-8}" y="${y(v)+4}" text-anchor="end" font-size="13" fill="var(--muted)" font-family="var(--mono)">${Math.round(v).toLocaleString('de-DE')}</text>`}
  s+=`<line x1="${P.l}" x2="${W-P.r}" y1="${y(D.start)}" y2="${y(D.start)}" stroke="var(--muted)" stroke-dasharray="4 4"/>`;
  if(pts.length>1){
    const d=pts.map((p,i)=>`${i?'L':'M'}${x(i)},${y(p.total)}`).join('');
    s+=`<defs><linearGradient id="ga" x1="0" x2="0" y1="0" y2="1"><stop offset="0" style="stop-color:var(--accent);stop-opacity:.28"/><stop offset="1" style="stop-color:var(--accent);stop-opacity:0"/></linearGradient></defs>`;
    s+=`<path d="${d}L${x(pts.length-1)},${H-P.b}L${x(0)},${H-P.b}Z" fill="url(#ga)"/>`;
    s+=`<path d="${d}" fill="none" stroke="var(--accent)" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>`;
    s+=`<text x="${P.l}" y="${H-6}" font-size="11" fill="var(--muted)">${fmtDate(pts[0].date)}</text><text x="${W-P.r}" y="${H-6}" text-anchor="end" font-size="11" fill="var(--muted)">${fmtDate(pts[pts.length-1].date)}</text>`;
  } else {
    s+=`<text x="${W/2}" y="${H/2}" text-anchor="middle" font-size="13" fill="var(--muted)">Die Kurve erscheint ab dem zweiten Lauf.</text>`;
  }
  const lp=pts[pts.length-1]; s+=`<circle cx="${x(pts.length-1)}" cy="${y(lp.total)}" r="4" fill="var(--accent)"/>`;
  svg.innerHTML=s;
})();

function fill(id, rows, empty, cols){
  const tb=document.querySelector(`#${id} tbody`);
  tb.innerHTML = rows.length ? rows.join('') : `<tr><td colspan="${cols}"><p class="empty">${empty}</p></td></tr>`;
}

fill('cands', (D.ranked||[]).slice(0,25).map(c=>{
  const chips=[...(c.why||[]).map(w=>`<span class="chip ${w.startsWith('⚠')?'w':''}">${esc(w.replace('⚠ ',''))}</span>`),
               ...(c.flags||[]).map(f=>`<span class="chip ${c.safety_ok===false?'b':'w'}">${esc(f)}</span>`)];
  if(c.safety_ok===null) chips.push('<span class="chip w">Sicherheit ungeprüft</span>');
  return `<tr><td><span class="score ${c.score<D.min_buy?'lo':''}">${c.score}</span></td>
    <td><a class="sym" href="${esc(c.url)}" target="_blank" rel="noopener">${esc(c.symbol)}</a><div class="sub">${esc(c.chain)}</div></td>
    <td class="r num">${usdShort(c.mcap)}</td><td class="r num">${usdShort(c.liq)}</td>
    <td class="r num">${Math.round(c.age_days)} T</td><td class="r num ${cls(c.chg24)}">${pct(c.chg24)}</td>
    <td class="r num">${c.holders?c.holders.toLocaleString('de-DE'):'–'}${c.holder_growth_7d!=null?`<div class="sub ${cls(c.holder_growth_7d)}">${pct(c.holder_growth_7d)} 7T</div>`:''}</td>
    <td>${chips.join('')}</td></tr>`;
}), 'Noch kein Lauf oder heute keine Kandidaten.', 8);

function renderOpen(){
fill('open', (pf.positions||[]).map(p=>{
  const val=p.units*p.price*fxOf(p), m=p.price/p.entry_price;
  return `<tr><td><a class="sym" href="${esc(p.url)}" target="_blank" rel="noopener">${esc(p.symbol)}</a><div class="sub">${esc(p.chain)} · Score ${p.score}</div></td>
  <td class="num">${fmtDate(p.opened)}</td><td class="r num">${eur(p.cost)}</td><td class="r num">${eur(val)}</td>
  <td class="r num ${cls(m-1)}">${pct((m-1)*100)}</td><td class="r num">${(p.max_mult||1).toFixed(2).replace('.',',')}x</td>
  <td class="r num">${eur(p.realized||0)}</td></tr>`;
}), 'Noch keine Positionen.', 7);
}

const reasonOf = p => {
  if(p.status==='dead') return 'Totalverlust (Liquidität weg)';
  const r=((p.sales||[]).slice(-1)[0]||{}).reason||'';
  return r.replace(/ \(.*\)$/,'').replace(/ -\d+% .*/,'').replace(/^Liquidität.*/,'Liquiditätsabzug').replace(/^Holder.*/,'Holder schrumpfen');
};
const heldVal = p => p.post_price ? p.cost*p.post_price/p.entry_price*((p.post_liq??1e9)<3000?0:1) : (p.status==='dead'?0:null);
const mx = v => v==null ? '–' : (v>=10?v.toFixed(0):v.toFixed(2)).replace('.',',')+'x';
function renderClosed(){
fill('closed', (pf.closed||[]).slice().reverse().map(p=>{
  const res=(p.realized||0)-p.cost, last=(p.sales||[]).slice(-1)[0], hv=heldVal(p);
  const hi=p.post_max?p.post_max/p.entry_price:null, now=p.post_price?p.post_price/p.entry_price:null;
  return `<tr><td><a class="sym" href="${esc(p.url)}" target="_blank" rel="noopener">${esc(p.symbol)}</a><div class="sub">${esc(p.chain)}</div></td>
  <td class="num">${fmtDate(p.opened)} – ${fmtDate(p.closed)}</td><td class="r num">${eur(p.cost)}</td>
  <td class="r num">${eur(p.realized||0)}</td><td class="r num ${cls(res)}">${pct(res/p.cost*100)}</td>
  <td>${p.status==='dead'?'Totalverlust (Liquidität weg)':esc(last?last.reason:'')}</td>
  <td class="r num">${mx(hi)}${p.post_max_date?`<div class="sub">${fmtDate(p.post_max_date)}</div>`:''}</td>
  <td class="r num ${now!=null?cls(now-1):''}">${mx(now)}</td>
  <td class="r num ${hv!=null?cls(hv-p.cost):''}">${hv==null?'–':pct((hv/p.cost-1)*100)}${(p.post_liq??1e9)<3000?'<div class="sub">Liquidität weg</div>':''}</td></tr>`;
}), 'Noch nichts verkauft.', 9);


  const g={};
  for(const p of pf.closed||[]){
    const k=reasonOf(p), hv=heldVal(p);
    g[k]=g[k]||{n:0,real:0,cost:0,held:0,nh:0};
    g[k].n++; g[k].real+=(p.realized||0); g[k].cost+=p.cost;
    if(hv!=null){g[k].held+=hv; g[k].nh++}
  }
  fill('rules', Object.entries(g).sort((a,b)=>b[1].n-a[1].n).map(([k,v])=>{
    const ok=v.nh===v.n, diff=v.real-v.held;
    const verdict=!ok?'noch keine Kursdaten nach Verkauf':Math.abs(diff)<v.cost*0.05?'neutral':diff>0?'Regel hat Geld gerettet':'Halten wäre besser gewesen';
    return `<tr><td>${esc(k)}</td><td class="r num">${v.n}</td><td class="r num ${cls(v.real-v.cost)}">${eur(v.real-v.cost)}</td>
      <td class="r num ${ok?cls(v.held-v.cost):''}">${ok?eur(v.held-v.cost):'–'}</td><td class="r num ${ok?cls(diff):''}">${ok?eur(diff):'–'}</td><td>${verdict}</td></tr>`;
  }), 'Noch keine Verkäufe.', 6);
}

function renderSales(){
  const rows=[];
  for(const p of [...(pf.positions||[]),...(pf.closed||[])]){
    const initial=p.cost/p.eur_per_usd/p.entry_price;
    for(const x of p.sales||[]) rows.push({p,x,share:x.units!=null&&initial?x.units/initial:null});
  }
  rows.sort((a,b)=>a.x.date<b.x.date?1:a.x.date>b.x.date?-1:0);
  fill('sales', rows.map(({p,x,share})=>`<tr><td class="num">${fmtDate(x.date)}</td>
    <td><a class="sym" href="${esc(p.url)}" target="_blank" rel="noopener">${esc(p.symbol)}</a><div class="sub">${esc(p.chain)}</div></td>
    <td class="r num">${share==null?'–':Math.round(share*100)+' %'}</td>
    <td class="r num ${cls(x.mult-1)}">${mx(x.mult)}</td><td class="r num">${eur(x.eur)}</td>
    <td>${esc(x.reason)}</td><td>${p.status==='open'?'Rest offen':p.status==='dead'?'Totalverlust':'geschlossen'}</td></tr>`),
    'Noch keine Verkäufe.', 7);
}
function renderPortfolio(){ renderKpis(); renderOpen(); renderSales(); renderClosed(); }
renderPortfolio();

// Live-Kurse direkt von DEX Screener
async function liveUpdate(){
  const items=[...(pf.positions||[]),...(pf.closed||[])];
  if(!items.length) return;
  const by={};
  for(const p of items){(by[p.chain]=by[p.chain]||new Set()).add(p.address)}
  const best={};
  let src='DEX Screener';
  try{
    for(const [ch,set] of Object.entries(by)){
      const a=[...set];
      for(let i=0;i<a.length;i+=30){
        const r=await fetch(`https://api.dexscreener.com/tokens/v1/${ch}/${a.slice(i,i+30).join(',')}`,{cache:'no-store'});
        if(!r.ok) throw new Error('HTTP '+r.status);
        const js=await r.json();
        for(const x of (Array.isArray(js)?js:(js.pairs||[]))){
          const k=(ch+':'+(x.baseToken&&x.baseToken.address||'')).toLowerCase(), liq=+((x.liquidity||{}).usd||0);
          if(!best[k]||liq>best[k].liq) best[k]={price:+x.priceUsd||0,liq};
        }
      }
    }
  }catch(e){
    console.warn('DEX Screener nicht erreichbar, versuche GeckoTerminal', e);
    src='GeckoTerminal';
    const NET={solana:'solana',base:'base',bsc:'bsc',ethereum:'eth'};
    try{
      for(const [ch,set] of Object.entries(by)){
        if(!NET[ch]) continue;
        const a=[...set];
        for(let i=0;i<a.length;i+=30){
          const r=await fetch(`https://api.geckoterminal.com/api/v2/networks/${NET[ch]}/tokens/multi/${a.slice(i,i+30).join(',')}`,{headers:{accept:'application/json'},cache:'no-store'});
          if(!r.ok) throw new Error('HTTP '+r.status);
          const js=await r.json();
          for(const x of js.data||[]){
            const at=x.attributes||{}, k=(ch+':'+(at.address||'')).toLowerCase();
            const liq=+(at.total_reserve_in_usd||0);
            if(+at.price_usd>0) best[k]={price:+at.price_usd,liq:liq||null};
          }
        }
      }
    }catch(e2){ console.warn('Live-Kurse nicht erreichbar', e2); showLive(false); return }
  }
  if(!Object.keys(best).length){ showLive(false); return }
  const today=new Date().toISOString().slice(0,10);
  for(const p of pf.positions||[]){
    const b=best[p.key.toLowerCase()];
    if(b&&b.price>0){p.price=b.price;if(b.liq!=null)p.liq=b.liq;p.max_mult=Math.max(p.max_mult||1,p.price/p.entry_price)}
  }
  for(const p of pf.closed||[]){
    const b=best[p.key.toLowerCase()];
    if(b&&b.price>0){
      p.post_price=b.price;if(b.liq!=null)p.post_liq=b.liq;
      if(p.closed!==today&&b.price>(p.post_max||0)){p.post_max=b.price;p.post_max_date=today}
    }
  }
  renderPortfolio();
  showLive(true, src);
}
function showLive(ok, src){
  const el=document.getElementById('live');
  el.hidden=false;
  el.classList.toggle('off',!ok);
  el.textContent=ok?`Live-Kurse (${src}) · Stand ${new Date().toLocaleTimeString('de-DE',{hour:'2-digit',minute:'2-digit'})} Uhr · aktualisiert jede Minute`
                   :'Live-Kurse gerade nicht erreichbar · angezeigt wird der Stand des letzten Laufs';
}
liveUpdate();
setInterval(()=>{ if(!document.hidden) liveUpdate() }, 60000);
document.addEventListener('visibilitychange',()=>{ if(!document.hidden) liveUpdate() });


// Datenbank und Auswertung
(function(){
  const c=D.collect||{}, a=D.analysis||{};
  const k=[['Verfolgte Tokens',(c.tracked??0).toLocaleString('de-DE')],
           ['Zuletzt gesehen',(c.seen??0).toLocaleString('de-DE')],
           ['Davon Filter bestanden',(c.passed??0).toLocaleString('de-DE')],
           ['Letzte Sammlung',c.last?new Date(c.last).toLocaleString('de-DE',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}):'–']];
  document.getElementById('dbkpis').innerHTML=k.map(([l,v])=>`<div class="kpi"><span>${l}</span><b>${v}</b></div>`).join('');
  const note=document.getElementById('anote');
  if(!a.horizon){note.textContent='Die Auswertung erscheint, sobald genug Tokens mindestens 7 Tage verfolgt wurden. Sie zeigt dann, wie oft Tokens je Gruppe später das 3-Fache erreicht haben oder gestorben sind.';return}
  note.textContent=`Grundlage: ${a.n} Tokens mit mindestens ${a.horizon} Tagen Verlauf, davon ${a.with_candles??0} mit echten Tageshochs. „≥3x“ bzw. „≥10x“ = Anteil, der innerhalb von ${a.horizon} Tagen zeitweise das 3- bzw. 10-Fache des Kurses beim ersten Sehen erreichte. „Tot“ = Liquidität inzwischen unter 3.000 $. „Median“ = typischer Kurs nach ${a.horizon} Tagen.`;
  const maxWin=Math.max(1,...a.groups.flatMap(g=>g.rows.map(r=>r.win)));
  document.getElementById('agroups').innerHTML=a.groups.map(g=>`<div><h3>${esc(g.title)}</h3><table><thead><tr><th>Gruppe</th><th class="r">n</th><th>≥3x</th><th class="r">≥10x</th><th class="r">Tot</th><th class="r">Median</th></tr></thead><tbody>${
    g.rows.map(r=>`<tr><td>${esc(r.label)}</td><td class="r num">${r.n}</td><td><div class="num">${r.win.toFixed(1).replace('.',',')} %</div><div class="bar" style="width:${r.win/maxWin*100}%"></div></td><td class="r num">${(r.win10??0).toFixed(1).replace('.',',')} %</td><td class="r num">${r.dead.toFixed(0)} %</td><td class="r num">${r.median.toFixed(2).replace('.',',')}x</td></tr>`).join('')
  }</tbody></table></div>`).join('');
  if(a.top&&a.top.length) document.getElementById('atop').innerHTML=`<h3>Beste Tokens seit dem ersten Sehen</h3><div class="scroll"><table style="min-width:760px"><thead><tr><th>Token</th><th>Erstmals</th><th class="r">Bestes</th><th class="r">Score</th><th class="r">Alter</th><th class="r">MCap</th><th class="r">Liquidität</th><th class="r">Holder</th><th class="r">Top-10</th><th>Filter</th></tr></thead><tbody>${
    a.top.map(t=>`<tr><td><a class="sym" href="https://dexscreener.com/${esc(t.chain)}/${esc(t.address)}" target="_blank" rel="noopener">${esc(t.symbol)}</a></td><td class="num">${fmtDate(t.first)}</td><td class="r num pos">${t.max.toFixed(1).replace('.',',')}x</td><td class="r num">${t.full_score??t.score??'–'}</td><td class="r num">${Math.round(t.age)} T</td><td class="r num">${usdShort(t.mcap)}</td><td class="r num">${usdShort(t.liq)}</td><td class="r num">${t.holders?t.holders.toLocaleString('de-DE'):'–'}</td><td class="r num">${t.top10!=null?Math.round(t.top10)+' %':'–'}</td><td>${esc(t.filter)}</td></tr>`).join('')
  }</tbody></table></div>`;
})();

const ev=document.getElementById('events');
ev.innerHTML=(D.events||[]).slice(0,40).map(e=>`<li><time>${fmtDate(e.date)}</time>${esc(e.text)}</li>`).join('') || '<li class="empty">Noch keine Bewegungen.</li>';
</script>
</body>
</html>
"""


def build_dashboard(state: dict, config: dict, out: Path):
    data = {
        "last_run": state.get("last_run"),
        "chains": config["chains"],
        "start": config["portfolio"]["start_cash_eur"],
        "min_buy": config["score"]["min_score_for_buy"],
        "portfolio": state.get("portfolio"),
        "ranked": state.get("last_ranked", []),
        "events": state.get("events", []),
        "collect": state.get("collect"),
        "fx": state.get("eur_per_usd"),
        "analysis": state.get("analysis"),
    }
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(TEMPLATE.replace("__DATA__", payload), encoding="utf-8")
