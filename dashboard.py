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
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700;800&display=swap">
<style>
/* Layout: oben die große Depot-Karte (Wert + leuchtende Kurve) neben vier kompakten Kennzahlen,
   darunter eine schwebende Navigationsleiste und ruhige Tabellenkarten. Dunkel zuerst, hell nach Systemeinstellung. */
:root{
  --bg:#0c1020; --surface:#131a2e; --raised:#1a2340; --fill:#1d2645; --fg:#eef1fa; --muted:#8c93ad;
  --line:rgba(160,175,230,.12); --accent:#8b6cff; --accent2:#22d3ee; --accent-soft:rgba(139,108,255,.16);
  --good:#3ddc97; --bad:#ff5c7a; --warn:#ffb547;
  --glow1:rgba(139,108,255,.38); --glow2:rgba(34,211,238,.22);
  --display:"Geist",ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;
  --body:"Geist",ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;
  --mono:"Geist",ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;
  --gutter:max(16px,env(safe-area-inset-left)); --gutter-r:max(16px,env(safe-area-inset-right));
  color-scheme:dark;
}
@media (prefers-color-scheme:light){:root{
  --bg:#f4f5fb; --surface:#ffffff; --raised:#ffffff; --fill:#eef0f8; --fg:#0f1428; --muted:#5e6683;
  --line:#e3e6f1; --accent:#5b3df5; --accent2:#0891b2; --accent-soft:#ece8ff;
  --good:#0f9d63; --bad:#e0294f; --warn:#b86e00;
  --glow1:rgba(91,61,245,.18); --glow2:rgba(8,145,178,.12); color-scheme:light}}
*{box-sizing:border-box}
html,body{margin:0}
html{scroll-behavior:smooth}
body{background:var(--bg);color:var(--fg);font:15px/1.5 var(--body);-webkit-font-smoothing:antialiased;
  font-feature-settings:"ss01","cv11";padding:0 0 64px}
body::before{content:"";position:fixed;inset:0 0 auto;height:env(safe-area-inset-top,0px);z-index:11;background:var(--bg)}
.wrap{max-width:1120px;margin:0 auto;display:grid;gap:40px;padding:32px var(--gutter-r) 0 var(--gutter)}
.wrap>*{min-width:0}
section{scroll-margin-top:84px}
/* Kopf */
.intro{display:flex;flex-wrap:wrap;align-items:end;justify-content:space-between;gap:8px 24px}
h1{font:800 clamp(30px,5.5vw,44px)/1 var(--display);letter-spacing:-.035em;margin:0}
.meta{color:var(--muted);font-size:13px}
.meta span+span::before{content:"";display:inline-block;width:3px;height:3px;border-radius:50%;background:currentColor;margin:0 8px 3px}
/* Hero */
.hero{display:grid;grid-template-columns:minmax(0,1.7fr) minmax(0,1fr);gap:14px;scroll-margin-top:84px}
@media (max-width:820px){.hero{grid-template-columns:1fr}}
.hero-main{position:relative;overflow:hidden;border-radius:28px;padding:24px 24px 8px;background:var(--surface);
  border:1px solid var(--line);isolation:isolate}
.hero-main::before{content:"";position:absolute;inset:-40% -10% auto auto;width:70%;aspect-ratio:1;border-radius:50%;
  background:radial-gradient(closest-side,var(--glow1),transparent);z-index:-1;filter:blur(10px)}
.hero-main::after{content:"";position:absolute;inset:auto auto -45% -15%;width:60%;aspect-ratio:1;border-radius:50%;
  background:radial-gradient(closest-side,var(--glow2),transparent);z-index:-1;filter:blur(10px)}
.hero-top{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}
.label{font-size:14px;color:var(--muted);font-weight:500}
.big{font:700 clamp(40px,8vw,68px)/1.05 var(--display);letter-spacing:-.045em;margin:10px 0 6px;font-variant-numeric:tabular-nums}
.delta{display:inline-flex;align-items:center;gap:6px;font-weight:600;font-size:15px;padding:4px 10px;border-radius:999px;
  background:var(--fill);font-variant-numeric:tabular-nums}
.delta.pos{background:color-mix(in srgb,var(--good) 14%,transparent)} .delta.neg{background:color-mix(in srgb,var(--bad) 14%,transparent)}
.delta small{color:var(--muted);font-weight:500;font-size:13px}
#curve{display:block;width:100%;height:auto;margin-top:8px}
.hero-side{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.kpi{background:var(--surface);border:1px solid var(--line);border-radius:22px;padding:16px 18px;display:flex;flex-direction:column;
  justify-content:space-between;gap:10px;min-width:0}
.kpi span{font-size:13px;color:var(--muted);font-weight:500}
.kpi b{font:650 26px/1.1 var(--display);letter-spacing:-.03em;font-variant-numeric:tabular-nums;overflow-wrap:anywhere}
.kpi b small{display:block;font:500 13px/1.3 var(--body);color:var(--muted);letter-spacing:0;margin-top:4px}
.panel .kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}
.panel .kpi{background:var(--fill);border:0;border-radius:16px}
.pos{color:var(--good)} .neg{color:var(--bad)}
/* Navigation */
.navwrap{position:sticky;top:calc(env(safe-area-inset-top,0px) + 12px);z-index:10;display:flex;justify-content:center;pointer-events:none}
.seg{pointer-events:auto;display:flex;gap:2px;padding:5px;border-radius:999px;max-width:100%;overflow-x:auto;scrollbar-width:none;
  background:color-mix(in srgb,var(--raised) 72%,transparent);border:1px solid var(--line);
  -webkit-backdrop-filter:saturate(160%) blur(18px);backdrop-filter:saturate(160%) blur(18px);
  box-shadow:0 10px 30px rgba(0,0,0,.18)}
.seg::-webkit-scrollbar{display:none}
.seg a{flex:none;padding:7px 14px;border-radius:999px;font-size:14px;font-weight:500;color:var(--muted);text-decoration:none;transition:background .15s,color .15s}
.seg a:hover,.seg a.on{color:var(--fg);background:var(--fill)}
.seg a:focus-visible{outline:2px solid var(--accent);outline-offset:1px}
/* Abschnitte und Tabellen */
h2{font:700 22px/1.2 var(--display);letter-spacing:-.025em;margin:0 0 14px;display:flex;align-items:center;gap:10px}
.count{font:600 13px/1 var(--body);color:var(--muted);background:var(--fill);padding:5px 9px;border-radius:999px;font-variant-numeric:tabular-nums}
.count:empty{display:none}
.panel{background:var(--surface);border:1px solid var(--line);border-radius:22px;padding:18px}
.panel.scroll{padding:4px 10px}
.scroll{overflow-x:auto;-webkit-overflow-scrolling:touch}
table{border-collapse:separate;border-spacing:0;width:100%;font-size:14px;min-width:680px}
#cands{min-width:920px} #cands td:last-child{min-width:240px}
th{font-size:12.5px;color:var(--muted);text-align:left;font-weight:500;padding:12px 10px;border-bottom:1px solid var(--line);white-space:nowrap}
td{padding:12px 10px;border-bottom:1px solid var(--line);vertical-align:middle}
tbody tr:last-child td{border-bottom:0}
tbody tr{transition:background .12s}
tbody tr:hover{background:color-mix(in srgb,var(--fill) 60%,transparent)}
td.r,th.r{text-align:right;white-space:nowrap}
.num{font-variant-numeric:tabular-nums}
a{color:var(--fg);text-decoration:none}
a:hover{color:var(--accent)}
a:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:6px}
.sub{color:var(--muted);font-size:12.5px}
.tok{display:flex;align-items:center;gap:10px;min-width:0}
.av{flex:none;width:32px;height:32px;border-radius:50%;object-fit:cover;background:var(--fill);display:grid;place-items:center;
  font:700 11px/1 var(--body);color:#fff;letter-spacing:.02em;
  background:linear-gradient(135deg,hsl(var(--h,260) 70% 58%),hsl(calc(var(--h,260) + 50) 75% 48%))}
img.av{background:var(--fill)}
.sym{font-weight:600}
.ring{--c:var(--accent);width:38px;height:38px;border-radius:50%;display:grid;place-items:center;font:650 12.5px/1 var(--body);
  font-variant-numeric:tabular-nums;background:radial-gradient(closest-side,var(--surface) 76%,transparent 78% 100%),
  conic-gradient(var(--c) calc(var(--v)*1%),var(--line) 0)}
.ring.lo{--c:var(--muted);color:var(--muted)}
.chip{display:inline-block;font-size:12px;padding:3px 9px;border-radius:999px;background:var(--fill);color:var(--muted);margin:3px 4px 0 0;white-space:nowrap}
.chip.w{background:color-mix(in srgb,var(--warn) 14%,transparent);color:var(--warn)}
.chip.b{background:color-mix(in srgb,var(--bad) 14%,transparent);color:var(--bad)}
.ev{list-style:none;margin:0;padding:0;display:grid;font-size:14px}
.ev li{padding:11px 4px;border-bottom:1px solid var(--line)}
.ev li:last-child{border-bottom:0}
.ev time{color:var(--muted);font-size:13px;margin-right:12px;font-variant-numeric:tabular-nums}
.note{font-size:13px;color:var(--muted);max-width:70ch;margin:12px 6px 0}
.empty{color:var(--muted);font-size:14px;margin:0;padding:8px 0}
.live{display:inline-flex;align-items:center;gap:8px;font-size:13px;color:var(--muted)}
.live::before{content:"";width:8px;height:8px;border-radius:50%;background:var(--good);animation:pulse 2.4s ease-out infinite}
.live.off::before{background:var(--warn);animation:none}
@keyframes pulse{0%{box-shadow:0 0 0 0 color-mix(in srgb,var(--good) 60%,transparent)}70%,100%{box-shadow:0 0 0 8px transparent}}
.hero-main{animation:rise .6s cubic-bezier(.2,.7,.2,1) both}
@keyframes rise{from{opacity:.001;transform:translateY(8px)}to{opacity:1;transform:none}}
@media (prefers-reduced-motion:reduce){.live::before,.hero-main{animation:none}html{scroll-behavior:auto}}
.agrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,330px),1fr));gap:26px;margin-top:22px}
.agrid>div{overflow-x:auto;min-width:0;-webkit-overflow-scrolling:touch}
.agrid h3,#atop h3{font:600 15px/1.3 var(--display);margin:0 0 6px;letter-spacing:-.01em}
.agrid table,#atop table{min-width:0;font-size:13px}
#atop{margin-top:26px}
.bar{height:5px;border-radius:3px;background:linear-gradient(90deg,var(--accent),var(--accent2));min-width:2px;margin-top:4px}
</style>
</head>
<body>
<div class="wrap">
  <div class="intro">
    <h1>Meme-Screener</h1>
    <div class="meta"><span>Aktualisiert <span id="lastrun"></span></span><span id="chains"></span></div>
  </div>

  <header class="hero" id="depot">
    <div class="hero-main">
      <div class="hero-top"><span class="label">Musterdepot</span><span class="live" id="live" hidden></span></div>
      <div class="big" id="k-total">–</div>
      <span class="delta" id="k-delta"></span>
      <svg id="curve" viewBox="0 0 800 220" role="img" aria-label="Depotwert über Zeit"></svg>
    </div>
    <div class="hero-side" id="kpis"></div>
  </header>

  <div class="navwrap"><nav class="seg" aria-label="Abschnitte">
    <a href="#kandidaten">Kandidaten</a><a href="#positionen">Positionen</a><a href="#verkaeufe">Verkäufe</a>
    <a href="#geschlossen">Geschlossen</a><a href="#regeln">Regeln</a><a href="#auswertung">Auswertung</a>
  </nav></div>

  <section id="kandidaten">
    <h2>Kandidaten heute <span class="count" id="c-cands"></span></h2>
    <div class="panel scroll"><table id="cands"><thead><tr>
      <th>Score</th><th>Token</th><th class="r">MCap</th><th class="r">Liquidität</th><th class="r">Alter</th>
      <th class="r">24h</th><th class="r">Holder</th><th>Hinweise</th></tr></thead><tbody></tbody></table></div>
  </section>

  <section id="positionen">
    <h2>Offene Positionen <span class="count" id="c-open"></span></h2>
    <div class="panel scroll"><table id="open"><thead><tr>
      <th>Token</th><th>Gekauft</th><th class="r">Einsatz</th><th class="r">Wert</th><th class="r">Entwicklung</th>
      <th class="r">Hoch</th><th class="r">Realisiert</th></tr></thead><tbody></tbody></table></div>
    <p class="note">Kurse kommen beim Öffnen live von DEX Screener und werden jede Minute aktualisiert. Verkäufe nach den Depotregeln prüft das Depot stündlich, Käufe einmal täglich im Hauptlauf.</p>
  </section>

  <section id="verkaeufe">
    <h2>Verkäufe <span class="count" id="c-sales"></span></h2>
    <div class="panel scroll"><table id="sales"><thead><tr>
      <th>Datum</th><th>Token</th><th class="r">Anteil</th><th class="r">Kurs</th><th class="r">Erlös</th><th>Grund</th><th>Status</th></tr></thead><tbody></tbody></table></div>
    <p class="note">Jeder Verkauf des Musterdepots, auch Teilverkäufe. „Anteil“ bezieht sich auf die ursprüngliche Positionsgröße, „Kurs“ auf den Kaufkurs.</p>
  </section>

  <section id="geschlossen">
    <h2>Geschlossene Positionen <span class="count" id="c-closed"></span></h2>
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
const IMG = Object.fromEntries((D.ranked||[]).filter(r=>r.image).map(r=>[r.key,r.image]));
const hue = s => [...String(s)].reduce((h,c)=>(h*31+c.charCodeAt(0))%360,7);
const tok = (x, sub) => {
  const img = x.image || IMG[x.key];
  const av = img ? `<img class="av" src="${esc(img)}" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="const s=document.createElement('span');s.className='av';s.style.setProperty('--h','${hue(x.symbol)}');s.textContent='${esc((x.symbol||'?').slice(0,2).toUpperCase())}';this.replaceWith(s)">`
                 : `<span class="av" style="--h:${hue(x.symbol)}">${esc((x.symbol||'?').slice(0,2).toUpperCase())}</span>`;
  const url = x.url || `https://dexscreener.com/${x.chain}/${x.address}`;
  return `<div class="tok">${av}<div><a class="sym" href="${esc(url)}" target="_blank" rel="noopener">${esc(x.symbol)}</a><div class="sub">${sub}</div></div></div>`;
};
const fmtDate = s => s ? s.split('-').reverse().join('.') : '–';

const fmtTs = t => t ? new Date(t).toLocaleString('de-DE',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}) : 'noch nie';
document.getElementById('lastrun').textContent = fmtTs((D.collect||{}).last||D.last_run);
document.getElementById('chains').textContent = 'Hauptlauf ' + fmtTs(D.last_run) + ' · ' + D.chains.map(c=>c[0].toUpperCase()+c.slice(1)).join(' und ');

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
  document.getElementById('k-total').textContent = eur(last);
  const dl=document.getElementById('k-delta');
  dl.className='delta '+cls(last-D.start);
  dl.innerHTML=`${pct((last/D.start-1)*100)} <small>seit Start mit ${eur(D.start)}</small>`;
  const kpis = [
    ['Offene Positionen', String((pf.positions||[]).length), ''],
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
    s+=`<defs><linearGradient id="ga" x1="0" x2="0" y1="0" y2="1"><stop offset="0" style="stop-color:var(--accent);stop-opacity:.32"/><stop offset="1" style="stop-color:var(--accent);stop-opacity:0"/></linearGradient>
      <linearGradient id="gl" x1="0" x2="1" y1="0" y2="0"><stop offset="0" style="stop-color:var(--accent)"/><stop offset="1" style="stop-color:var(--accent2)"/></linearGradient>
      <filter id="gw" x="-10%" y="-30%" width="120%" height="160%"><feGaussianBlur stdDeviation="5"/></filter></defs>`;
    s+=`<path d="${d}L${x(pts.length-1)},${H-P.b}L${x(0)},${H-P.b}Z" fill="url(#ga)"/>`;
    s+=`<path d="${d}" fill="none" stroke="url(#gl)" stroke-width="6" opacity=".45" filter="url(#gw)"/>`;
    s+=`<path d="${d}" fill="none" stroke="url(#gl)" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>`;
    s+=`<text x="${P.l}" y="${H-6}" font-size="11" fill="var(--muted)">${fmtDate(pts[0].date)}</text><text x="${W-P.r}" y="${H-6}" text-anchor="end" font-size="11" fill="var(--muted)">${fmtDate(pts[pts.length-1].date)}</text>`;
  } else {
    s+=`<text x="${W/2}" y="${H/2}" text-anchor="middle" font-size="13" fill="var(--muted)">Die Kurve erscheint ab dem zweiten Lauf.</text>`;
  }
  const lp=pts[pts.length-1]; s+=`<circle cx="${x(pts.length-1)}" cy="${y(lp.total)}" r="9" fill="var(--accent2)" opacity=".2"/><circle cx="${x(pts.length-1)}" cy="${y(lp.total)}" r="4.5" fill="var(--accent2)" stroke="var(--surface)" stroke-width="2"/>`;
  svg.innerHTML=s;
})();

function fill(id, rows, empty, cols){
  const cnt=document.getElementById('c-'+id); if(cnt) cnt.textContent = rows.length ? String(rows.length) : '';
  const tb=document.querySelector(`#${id} tbody`);
  tb.innerHTML = rows.length ? rows.join('') : `<tr><td colspan="${cols}"><p class="empty">${empty}</p></td></tr>`;
}

fill('cands', (D.ranked||[]).slice(0,25).map(c=>{
  const chips=[...(c.why||[]).map(w=>`<span class="chip ${w.startsWith('⚠')?'w':''}">${esc(w.replace('⚠ ',''))}</span>`),
               ...(c.flags||[]).map(f=>`<span class="chip ${c.safety_ok===false?'b':'w'}">${esc(f)}</span>`)];
  if(c.safety_ok===null) chips.push('<span class="chip w">Sicherheit ungeprüft</span>');
  return `<tr><td><span class="ring ${c.score<D.min_buy?'lo':''}" style="--v:${c.score}" title="Score ${c.score} von 100">${c.score}</span></td>
    <td>${tok(c, esc(c.chain))}</td>
    <td class="r num">${usdShort(c.mcap)}</td><td class="r num">${usdShort(c.liq)}</td>
    <td class="r num">${Math.round(c.age_days)} T</td><td class="r num ${cls(c.chg24)}">${pct(c.chg24)}</td>
    <td class="r num">${c.holders?c.holders.toLocaleString('de-DE'):'–'}${c.holder_growth_7d!=null?`<div class="sub ${cls(c.holder_growth_7d)}">${pct(c.holder_growth_7d)} 7T</div>`:''}</td>
    <td>${chips.join('')}</td></tr>`;
}), 'Noch kein Lauf oder heute keine Kandidaten.', 8);

function renderOpen(){
fill('open', (pf.positions||[]).map(p=>{
  const val=p.units*p.price*fxOf(p), m=p.price/p.entry_price;
  return `<tr><td>${tok(p, `${esc(p.chain)}, Score ${p.score}`)}</td>
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
  return `<tr><td>${tok(p, esc(p.chain))}</td>
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
    <td>${tok(p, esc(p.chain))}</td>
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
  el.textContent=ok?`Live · ${new Date().toLocaleTimeString('de-DE',{hour:'2-digit',minute:'2-digit'})} Uhr`
                   :'Live-Kurse nicht erreichbar, Stand letzter Lauf';
  el.title=ok?`Kurse von ${src}, aktualisiert jede Minute`:'';
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
