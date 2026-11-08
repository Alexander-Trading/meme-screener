#!/usr/bin/env python3
"""
Meme-Coin-Screener mit fiktivem Musterdepot.

Ablauf pro Lauf (einmal täglich per GitHub Actions):
  1. Kandidaten sammeln (DEX Screener + GeckoTerminal, kostenlos, ohne API-Key)
  2. Marktdaten laden und Basisfilter anwenden
  3. Sicherheitscheck (RugCheck für Solana, GoPlus für EVM-Chains)
  4. Scoring 0-100
  5. Musterdepot aktualisieren (fiktive Käufe/Verkäufe)
  6. Snapshots speichern, Dashboard (docs/index.html) erzeugen, Telegram senden

Keine Anlageberatung. Das Depot ist rein fiktiv.
"""
from __future__ import annotations

import gzip
import json
import math
import os
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
DOCS = ROOT / "docs"
STATE_FILE = DATA / "state.json"
SNAP_FILE = DATA / "snapshots.json"
RUNS_DIR = DATA / "runs"
RAW_DIR = DATA / "raw"
TRACK_FILE = DATA / "tracking.json.gz"  # alt, wird migriert
TOKENS_DIR = DATA / "tokens"
PRICES_DIR = DATA / "prices"
OHLC_DIR = DATA / "ohlc"
OHLC_DONE_FILE = DATA / "ohlc_done.json"
PAIRS_FILE = DATA / "pairs.json"

CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))

DEX = "https://api.dexscreener.com"
GECKO = "https://api.geckoterminal.com/api/v2"
RUGCHECK = "https://api.rugcheck.xyz/v1"
GOPLUS = "https://api.gopluslabs.io/api/v1"

GECKO_NET = {"solana": "solana", "base": "base", "bsc": "bsc", "ethereum": "eth"}
GOPLUS_CHAIN = {"base": "8453", "bsc": "56", "ethereum": "1"}

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "meme-screener/1.0", "Accept": "application/json"})

# Für Tests ersetzbar: Funktion(url, params) -> JSON
def _http_get(url: str, params: dict | None = None):
    for attempt in range(3):
        try:
            r = SESSION.get(url, params=params, timeout=20)
            if r.status_code == 429:
                time.sleep(5 * (attempt + 1))
                continue
            if r.status_code >= 400:
                return None
            return r.json()
        except (requests.RequestException, ValueError):
            time.sleep(2 * (attempt + 1))
    return None

HTTP_GET = _http_get
SLEEP = time.sleep


EVM_CHAINS = {"base", "bsc", "ethereum"}


def norm(chain: str, addr: str) -> str:
    return addr.lower() if chain in EVM_CHAINS and addr else addr


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def fnum(x, default=0.0) -> float:
    try:
        if x is None or x == "":
            return default
        return float(x)
    except (TypeError, ValueError):
        return default


def log(msg: str):
    print(f"[{now_utc():%H:%M:%S}] {msg}", flush=True)


# ---------------------------------------------------------------- 1. Sammeln
def collect_candidates(chains: list[str]) -> dict[str, set[str]]:
    """Gibt {chain: {tokenAddress, ...}} zurück."""
    found: dict[str, set[str]] = {c: set() for c in chains}

    for path in ("/token-profiles/latest/v1", "/token-profiles/recent-updates/v1",
                 "/token-boosts/latest/v1", "/token-boosts/top/v1",
                 "/community-takeovers/latest/v1"):
        data = HTTP_GET(DEX + path)
        if isinstance(data, dict):
            data = [data]
        for item in data or []:
            ch, addr = item.get("chainId"), item.get("tokenAddress")
            if ch in found and addr:
                found[ch].add(norm(ch, addr))
        SLEEP(1)

    # GeckoTerminal: trendende Pools – findet auch ältere "Überlebende"
    for ch in chains:
        net = GECKO_NET.get(ch)
        if not net:
            continue
        for page in (1, 2, 3):
            for kind in ("trending_pools", "pools"):
                params = {"page": page}
                if kind == "pools":
                    params["sort"] = "h24_volume_usd_desc"
                data = HTTP_GET(f"{GECKO}/networks/{net}/{kind}", params)
                for pool in (data or {}).get("data", []) or []:
                    rel = pool.get("relationships", {}).get("base_token", {}).get("data", {})
                    tid = rel.get("id", "")
                    if "_" in tid:
                        found[ch].add(norm(ch, tid.split("_", 1)[1]))
                SLEEP(2.2)  # GeckoTerminal: ca. 30 Abrufe/Minute
    return found


# ---------------------------------------------------------- 2. Marktdaten
def fetch_pairs(chain: str, addresses: list[str]) -> dict[str, dict]:
    """Bester Pool (höchste Liquidität) je Token."""
    best: dict[str, dict] = {}
    for i in range(0, len(addresses), 30):
        chunk = addresses[i:i + 30]
        wanted = {norm(chain, a) for a in chunk}
        data = HTTP_GET(f"{DEX}/tokens/v1/{chain}/{','.join(chunk)}")
        if isinstance(data, dict):
            data = data.get("pairs") or []
        for p in data or []:
            base = norm(chain, (p.get("baseToken") or {}).get("address") or "")
            if not base or base not in wanted:
                continue
            liq = fnum((p.get("liquidity") or {}).get("usd"))
            if base not in best or liq > fnum((best[base].get("liquidity") or {}).get("usd")):
                best[base] = p
        SLEEP(0.3)  # DEX Screener erlaubt 300 Abrufe/Minute auf diesem Endpunkt
    return best


def to_metrics(chain: str, p: dict) -> dict:
    t = now_utc().timestamp() * 1000
    created = fnum(p.get("pairCreatedAt"), t)
    tx24 = (p.get("txns") or {}).get("h24") or {}
    tx6 = (p.get("txns") or {}).get("h6") or {}
    info = p.get("info") or {}
    socials = {s.get("type") for s in info.get("socials") or [] if s.get("type")}
    base = p.get("baseToken") or {}
    return {
        "chain": chain,
        "address": norm(chain, base.get("address") or ""),
        "symbol": (base.get("symbol") or "?")[:20],
        "name": (base.get("name") or "")[:40],
        "url": p.get("url"),
        "pair": p.get("pairAddress"),
        "dex": p.get("dexId"),
        "price": fnum(p.get("priceUsd")),
        "liq": fnum((p.get("liquidity") or {}).get("usd")),
        "mcap": fnum(p.get("marketCap")) or fnum(p.get("fdv")),
        "vol24": fnum((p.get("volume") or {}).get("h24")),
        "buys24": int(fnum(tx24.get("buys"))),
        "sells24": int(fnum(tx24.get("sells"))),
        "buys6": int(fnum(tx6.get("buys"))),
        "sells6": int(fnum(tx6.get("sells"))),
        "chg1": fnum((p.get("priceChange") or {}).get("h1")),
        "chg6": fnum((p.get("priceChange") or {}).get("h6")),
        "chg24": fnum((p.get("priceChange") or {}).get("h24")),
        "age_days": max(0.0, (t - created) / 86_400_000),
        "twitter": "twitter" in socials or "x" in socials,
        "telegram": "telegram" in socials,
        "website": bool(info.get("websites")),
        "boosted": fnum((p.get("boosts") or {}).get("active")) > 0,
        "image": info.get("imageUrl"),
    }


def base_filter(m: dict) -> str | None:
    """None = bestanden, sonst Grund."""
    f = CONFIG["filter"]
    if m["symbol"].upper() in {s.upper() for s in CONFIG["exclude_symbols"]}:
        return "ausgeschlossen"
    if m["age_days"] < f["min_age_days"]:
        return "zu jung"
    if m["age_days"] > f["max_age_days"]:
        return "zu alt"
    if m["liq"] < f["min_liquidity_usd"]:
        return "Liquidität zu gering"
    if not (f["min_mcap_usd"] <= m["mcap"] <= f["max_mcap_usd"]):
        return "Marktkapitalisierung außerhalb"
    if m["buys24"] + m["sells24"] < f["min_txns_24h"]:
        return "zu wenig Handel"
    if m["price"] <= 0:
        return "kein Preis"
    return None


# ---------------------------------------------------------- 3. Sicherheit
def safety_solana(addr: str) -> dict:
    rep = HTTP_GET(f"{RUGCHECK}/tokens/{addr}/report")
    if not rep:
        return {"ok": None, "flags": ["RugCheck nicht erreichbar"], "holders": None, "top10": None}
    flags, ok = [], True
    if rep.get("rugged"):
        ok = False; flags.append("als Rug markiert")
    if rep.get("mintAuthority"):
        ok = False; flags.append("Mint aktiv")
    if rep.get("freezeAuthority"):
        ok = False; flags.append("Freeze aktiv")
    for r in rep.get("risks") or []:
        lvl, name = (r.get("level") or "").lower(), r.get("name") or "Risiko"
        if lvl == "danger":
            ok = False; flags.append(name)
        elif lvl == "warn":
            flags.append(name)
    # Top-10 ohne Pool-/AMM-Konten
    top10 = None
    th = rep.get("topHolders") or []
    if th:
        known_pools = {k for k in (rep.get("knownAccounts") or {}).keys()}
        pcts = [fnum(h.get("pct")) for h in th if h.get("owner") not in known_pools and h.get("address") not in known_pools]
        top10 = round(sum(sorted(pcts, reverse=True)[:10]), 1)
    # LP-Sperre
    lp_locked = None
    mk = rep.get("markets") or []
    if mk:
        lp_locked = max(fnum((x.get("lp") or {}).get("lpLockedPct")) for x in mk)
    holders = rep.get("totalHolders")
    return {"ok": ok, "flags": flags[:6], "holders": int(holders) if holders else None,
            "top10": top10, "lp_locked": lp_locked}


def safety_evm(chain: str, addresses: list[str]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    cid = GOPLUS_CHAIN.get(chain)
    if not cid:
        return out
    for i in range(0, len(addresses), 20):
        chunk = addresses[i:i + 20]
        data = HTTP_GET(f"{GOPLUS}/token_security/{cid}", {"contract_addresses": ",".join(chunk)})
        res = (data or {}).get("result") or {}
        for addr in chunk:
            r = res.get(addr.lower()) or res.get(addr)
            if not r:
                out[addr] = {"ok": None, "flags": ["GoPlus ohne Daten"], "holders": None, "top10": None}
                continue
            flags, ok = [], True
            def on(k): return str(r.get(k, "0")) == "1"
            for k, label in (("is_honeypot", "Honeypot"), ("is_mintable", "Mint aktiv"),
                             ("owner_change_balance", "Owner kann Guthaben ändern"),
                             ("hidden_owner", "versteckter Owner"), ("selfdestruct", "Selfdestruct"),
                             ("can_take_back_ownership", "Ownership zurückholbar"),
                             ("cannot_sell_all", "Verkauf eingeschränkt"), ("is_blacklisted", "Blacklist")):
                if on(k):
                    ok = False; flags.append(label)
            tax = max(fnum(r.get("buy_tax")), fnum(r.get("sell_tax"))) * 100
            if tax > CONFIG["filter"]["max_tax_pct"]:
                ok = False; flags.append(f"Steuer {tax:.0f}%")
            holders = r.get("holders") or []
            top10 = round(sum(fnum(h.get("percent")) * 100 for h in holders
                              if str(h.get("is_contract")) != "1" and str(h.get("is_locked")) != "1")
                          , 1) if holders else None
            lp = r.get("lp_holders") or []
            lp_locked = round(sum(fnum(h.get("percent")) * 100 for h in lp
                                  if str(h.get("is_locked")) == "1"
                                  or (h.get("address") or "").lower().startswith("0x000000000000000000000000000000000000dead")),
                              1) if lp else None
            hc = r.get("holder_count")
            out[addr] = {"ok": ok, "flags": flags[:6], "holders": int(fnum(hc)) if hc else None,
                         "top10": top10, "lp_locked": lp_locked}
        SLEEP(1.5)
    return out


# ------------------------------------------------------------- 4. Scoring
def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def holder_growth(snaps: dict, key: str, holders_now: int | None, days: int = 7) -> float | None:
    """Wachstum in % gegenüber dem ältesten Snapshot der letzten `days` Tage."""
    hist = snaps.get(key) or []
    if not holders_now or not hist:
        return None
    cutoff = now_utc().timestamp() - days * 86400
    old = [h for h in hist if h.get("t", 0) >= cutoff and h.get("holders")]
    if not old:
        return None
    first = old[0]["holders"]
    if first <= 0 or now_utc().timestamp() - old[0]["t"] < 20 * 3600:
        return None
    return (holders_now / first - 1) * 100


def score(m: dict) -> tuple[int, list[str]]:
    """0-100 Punkte. Gibt (Score, Begründungen) zurück."""
    pts, why = 0.0, []

    # Alter: Überlebende 14-60 Tage am besten (max 12)
    a = m["age_days"]
    s = 12 if 14 <= a <= 60 else 8 if 7 <= a < 14 or 60 < a <= 90 else 4
    pts += s
    if s == 12: why.append(f"{a:.0f} Tage alt (Überlebender)")

    # Liquidität, logarithmisch 30k -> 1M (max 12)
    pts += 12 * clamp(math.log10(max(m["liq"], 1) / 30_000) / math.log10(1_000_000 / 30_000))

    # Liquidität/MCap: 5-30 % gesund (max 8)
    lm = m["liq"] / m["mcap"] * 100 if m["mcap"] else 0
    pts += 8 if 5 <= lm <= 30 else 4 if 2 <= lm < 5 or 30 < lm <= 60 else 0
    if lm < 2: why.append("⚠ dünne Liquidität im Verhältnis zur MCap")

    # Volumen/Liquidität: 0,5-5 aktiv, >15 Wash-Verdacht (max 10)
    vl = m["vol24"] / m["liq"] if m["liq"] else 0
    if 0.5 <= vl <= 5: pts += 10
    elif 0.2 <= vl < 0.5 or 5 < vl <= 15: pts += 5
    elif vl > 15: why.append("⚠ Volumen auffällig hoch (Wash-Trading?)")

    # Kaufdruck 24h und 6h (max 12)
    br24 = m["buys24"] / max(m["sells24"], 1)
    br6 = m["buys6"] / max(m["sells6"], 1)
    pts += 6 * clamp((br24 - 0.9) / 0.6) + 6 * clamp((br6 - 0.9) / 0.6)
    if br24 >= 1.3: why.append(f"Kaufdruck {br24:.2f}x")

    # Aktivität: Transaktionen (max 8)
    tx = m["buys24"] + m["sells24"]
    pts += 8 * clamp(math.log10(max(tx, 1) / 150) / math.log10(20_000 / 150))

    # Trend: positiv, aber kein Pump-Hinterherlaufen (max 10)
    c24, c6 = m["chg24"], m["chg6"]
    if 0 < c24 <= 80: pts += 6
    elif 80 < c24 <= 200: pts += 3
    elif c24 > 300: why.append("⚠ schon stark gepumpt (+%d%%)" % c24)
    if c6 > 0: pts += 4

    # Socials (max 6)
    pts += 2 * m["twitter"] + 2 * m["telegram"] + 2 * m["website"]
    if not (m["twitter"] or m["telegram"]): why.append("⚠ keine Socials")

    # Holder (max 22): Anzahl + Wachstum aus eigenen Snapshots
    h = m.get("holders")
    if h:
        pts += 7 * clamp(math.log10(max(h, 1) / 300) / math.log10(30_000 / 300))
    g = m.get("holder_growth_7d")
    if g is not None:
        pts += 15 * clamp(g / 40)
        if g >= 10: why.append(f"Holder +{g:.0f}% in 7 Tagen")
        if g < 0: why.append(f"⚠ Holder schrumpfen ({g:.0f}%)")
    elif h:
        pts += 5  # neutral, solange noch keine Historie existiert

    # Konzentration (Abzug)
    t10 = m.get("top10")
    if t10 is not None and t10 > 25:
        pts -= min(10, (t10 - 25) / 2)
        why.append(f"Top-10 halten {t10:.0f}%")

    # Bezahlte Boosts leicht negativ
    if m["boosted"]:
        pts -= 2
        why.append("bezahlter Boost aktiv")

    return int(round(clamp(pts, 0, 100))), why


# ------------------------------------------------------- 5. Musterdepot
def update_portfolio(state: dict, prices: dict[str, dict], ranked: list[dict],
                     pos_safety: dict[str, dict] | None = None) -> list[str]:
    """Aktualisiert Positionen, führt Exit-Regeln aus, kauft neue Kandidaten."""
    cfg = CONFIG["portfolio"]
    ex = CONFIG.get("exits", {})
    pos_safety = pos_safety or {}
    pf = state.setdefault("portfolio", {"cash": cfg["start_cash_eur"], "positions": [], "closed": [], "history": []})
    events: list[str] = []
    today = now_utc().date().isoformat()
    ts = now_utc().timestamp()
    fx = state.get("eur_per_usd", 0.92)  # aktueller USD→EUR-Kurs

    # 5a. Bestehende Positionen bewerten
    for pos in pf["positions"]:
        if pos["status"] != "open":
            continue
        prev_liq = pos.get("liq", 0)
        p = prices.get(pos["key"])
        if p and p["price"] > 0:
            pos["price"] = p["price"]
            pos["liq"] = p["liq"]
            pos["updated"] = today
        mult = pos["price"] / pos["entry_price"] if pos["entry_price"] else 0
        pos["max_mult"] = max(pos.get("max_mult", 1.0), mult)
        sf = pos_safety.get(pos["key"]) or {}
        if sf.get("holders"):
            hh = pos.setdefault("holders_hist", [])
            hh[:] = [h for h in hh if h[0] != today] + [[today, sf["holders"]]]
            del hh[:-30]

        def sell(fraction: float, reason: str):
            units = pos["units"] * fraction
            proceeds = units * pos["price"] * fx
            pos["units"] -= units
            pos["realized"] = pos.get("realized", 0.0) + proceeds
            pf["cash"] += proceeds
            pos.setdefault("sales", []).append({"date": today, "mult": round(mult, 3), "price": pos["price"],
                                                "units": units, "eur": round(proceeds, 2), "reason": reason})
            events.append(f"{pos['symbol']}: {reason}, {fraction*100:.0f}% verkauft bei {mult:.2f}x ({proceeds:.0f} €)")

        def close(status: str):
            pos["status"] = status
            pos["closed"] = today
            pf["closed"].append(pos)

        # Token tot (Liquidität weg, keine Daten mehr seit 3 Tagen)
        stale = (ts - datetime.fromisoformat(pos.get("updated", today)).replace(tzinfo=timezone.utc).timestamp()) > 3 * 86400
        if pos.get("liq", 0) < cfg["dead_liquidity_usd"] or stale:
            events.append(f"{pos['symbol']}: Liquidität weg, als Totalverlust gewertet")
            close("dead")
            continue

        # Warnsignale: sofort alles verkaufen
        exit_reason = None
        if sf.get("ok") is False and ex.get("sell_on_safety_fail", True):
            exit_reason = "Sicherheitscheck negativ (" + ", ".join((sf.get("flags") or ["Risiko"])[:2]) + ")"
        elif prev_liq and ex.get("liquidity_drop_pct") and pos["liq"] < prev_liq * (1 - ex["liquidity_drop_pct"] / 100):
            exit_reason = f"Liquidität -{(1 - pos['liq'] / prev_liq) * 100:.0f}% seit gestern"
        if exit_reason:
            sell(1.0, exit_reason)
            close("closed")
            continue

        # Community schrumpft: einmalig halbieren
        hd = ex.get("holder_drop_pct_7d")
        hh = pos.get("holders_hist") or []
        if hd and len(hh) >= 2 and "holderdrop" not in pos.get("done", []):
            ref = [h for h in hh if 5 <= (date.fromisoformat(today) - date.fromisoformat(h[0])).days <= 9]
            if ref and ref[0][1] > 0 and hh[-1][1] < ref[0][1] * (1 - hd / 100):
                sell(ex.get("holder_drop_sell_fraction", 0.5), f"Holder -{(1 - hh[-1][1] / ref[0][1]) * 100:.0f}% in 7 Tagen")
                pos.setdefault("done", []).append("holderdrop")

        for step in cfg["take_profit_steps"]:
            tag = f"tp{step['multiple']}"
            if mult >= step["multiple"] and tag not in pos.get("done", []):
                sell(step["sell_fraction"], f"Gewinnmitnahme {step['multiple']}x")
                pos.setdefault("done", []).append(tag)

        age = (ts - pos["opened_ts"]) / 86400
        tr = ex.get("trailing_stop") or {}
        if (mult - 1) * 100 <= cfg["stop_loss_pct"]:
            sell(1.0, "Stop-Loss")
        elif tr and pos["max_mult"] >= tr["activate_multiple"] and mult <= pos["max_mult"] * (1 - tr["drawdown_pct"] / 100):
            sell(1.0, f"Trailing Stop (-{tr['drawdown_pct']}% vom Hoch {pos['max_mult']:.1f}x)")
        elif age >= cfg["max_hold_days"]:
            sell(1.0, f"Haltedauer {cfg['max_hold_days']} Tage erreicht")
        if pos["units"] <= 1e-12:
            close("closed")

    pf["positions"] = [p for p in pf["positions"] if p["status"] == "open"]

    # 5b. Neue Käufe
    held = {p["key"] for p in pf["positions"]} | {p["key"] for p in pf["closed"]}
    eur_per_usd = fx
    bought = 0
    for c in ranked:
        if bought >= cfg["max_buys_per_day"] or pf["cash"] < cfg["position_size_eur"]:
            break
        if c["score"] < CONFIG["score"]["min_score_for_buy"] or c["key"] in held or c["safety_ok"] is not True:
            continue
        eur = cfg["position_size_eur"]
        units = eur / eur_per_usd / c["price"]
        pf["cash"] -= eur
        pf["positions"].append({
            "key": c["key"], "chain": c["chain"], "address": c["address"], "symbol": c["symbol"],
            "url": c["url"], "opened": today, "opened_ts": ts, "entry_price": c["price"], "price": c["price"],
            "liq": c["liq"], "units": units, "cost": eur, "eur_per_usd": eur_per_usd, "score": c["score"],
            "status": "open", "updated": today, "max_mult": 1.0,
        })
        events.append(f"Kauf {c['symbol']} ({c['chain']}) für {eur:.0f} €, Score {c['score']}")
        bought += 1

    # 5c. Depotwert
    open_val = sum(p["units"] * p["price"] * fx for p in pf["positions"])
    total = pf["cash"] + open_val
    pf["history"] = [h for h in pf["history"] if h["date"] != today]
    pf["history"].append({"date": today, "total": round(total, 2), "cash": round(pf["cash"], 2),
                          "invested": round(open_val, 2), "open": len(pf["positions"])})
    return events


# ------------------------------------------------------------ 6. Ausgabe
def send_telegram(text: str):
    token, chat = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat:
        log("Telegram nicht konfiguriert, übersprungen")
        return
    try:
        SESSION.post(f"https://api.telegram.org/bot{token}/sendMessage",
                     json={"chat_id": chat, "text": text[:4000], "parse_mode": "HTML",
                           "disable_web_page_preview": True}, timeout=20)
    except requests.RequestException as e:
        log(f"Telegram-Fehler: {e}")


def telegram_text(ranked: list[dict], events: list[str], state: dict) -> str:
    pf = state["portfolio"]
    h = pf["history"][-1]
    start = CONFIG["portfolio"]["start_cash_eur"]
    lines = [f"<b>🐸 Meme-Screener {now_utc():%d.%m.%Y}</b>",
             f"Musterdepot: {h['total']:,.0f} € ({(h['total']/start-1)*100:+.1f}%) · {h['open']} offen".replace(",", "."), ""]
    top = [c for c in ranked if c["score"] >= CONFIG["score"]["min_score_for_report"]][:CONFIG["score"]["report_top_n"]]
    if top:
        lines.append("<b>Top-Kandidaten</b>")
        for c in top:
            warn = " ⚠" if any(w.startswith("⚠") for w in c["why"]) or c["safety_ok"] is not True else ""
            lines.append(f"{c['score']} · <a href=\"{c['url']}\">{c['symbol']}</a> ({c['chain']}) "
                         f"MCap {c['mcap']/1e6:.2f}M · {c['age_days']:.0f}d{warn}")
    else:
        lines.append("Heute kein Kandidat über der Mindestpunktzahl.")
    if events:
        lines += ["", "<b>Depot-Bewegungen</b>"] + events[:10]
    url = os.getenv("DASHBOARD_URL")
    if url:
        lines += ["", f"<a href=\"{url}\">Dashboard öffnen</a>"]
    lines += ["", "<i>Fiktiv, keine Anlageberatung.</i>"]
    return "\n".join(lines)


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return default


def save_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")


def eur_rate() -> float:
    data = HTTP_GET("https://api.frankfurter.app/latest", {"from": "USD", "to": "EUR"})
    r = fnum(((data or {}).get("rates") or {}).get("EUR"))
    return r if 0.5 < r < 1.5 else 0.92


RAW_FIELDS = ("key", "symbol", "price", "liq", "mcap", "vol24", "buys24", "sells24", "buys6", "sells6",
              "chg1", "chg6", "chg24", "age_days", "twitter", "telegram", "website", "boosted",
              "pre_score", "filter", "pair", "dex")


def gz_load(path: Path, default):
    try:
        with gzip.open(path, "rt", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, OSError, ValueError):
        return default


def gz_save(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))


def _add_point(rec: dict, point: list):
    if rec["s"] and rec["s"][-1][0] == point[0]:
        rec["s"][-1] = point
    elif not rec["s"] or rec["s"][-1][0] < point[0]:
        rec["s"].append(point)


def load_tracking(days: int | None = None) -> dict:
    """Baut die Tracking-Datenbank aus den Tagesdateien auf.
    data/tokens/JJJJ-MM-TT.json.gz   – Tokens, die an diesem Tag zum ersten Mal gesehen wurden (Startmerkmale)
    data/prices/JJJJ-MM-TT_HH.json.gz – Kurse je Lauf (einmal geschrieben, nie geändert)
    Ergebnis: {key: {"first", "symbol", "f", "s": [[datum, preis, liquidität, mcap], ...]}}"""
    days = days or CONFIG.get("tracking", {}).get("days", 180)
    today_ord = now_utc().date().toordinal()
    def recent(f: Path) -> bool:
        try:
            return today_ord - date.fromisoformat(f.name[:10]).toordinal() <= days
        except ValueError:
            return False
    track: dict = {}
    for f in sorted(TOKENS_DIR.glob("*.json.gz")):
        if recent(f):
            for k, v in gz_load(f, {}).items():
                track.setdefault(k, {"first": f.name[:10], "symbol": v.get("symbol"), "f": v.get("f") or {}, "s": []})
    for f in sorted(PRICES_DIR.glob("*.json.gz")):
        if recent(f):
            d = f.name[:10]
            for k, pt in gz_load(f, {}).items():
                rec = track.get(k)
                if rec and d >= rec["first"]:
                    _add_point(rec, [d] + list(pt))
    for f in sorted(OHLC_DIR.glob("*.json.gz")):
        for k, candles in gz_load(f, {}).items():
            if k in track:
                track[k]["o"] = candles  # neuere Datei ersetzt ältere
    return track


def is_dead(rec: dict) -> bool:
    """Seit mindestens 7 Tagen Liquidität unter 1.000 $ → nicht mehr nachpreisen."""
    s = rec.get("s") or []
    if len(s) < 7:
        return False
    last = s[-7:]
    return all((x[2] or 0) < 1000 for x in last) and \
        (date.fromisoformat(last[-1][0]) - date.fromisoformat(last[0][0])).days >= 6


def update_tracking(all_metrics: list[dict], extra_prices: dict[str, dict], track: dict) -> dict:
    """Speichert neue Tokens und die Kurse dieses Laufs; jeder je gesehene Token wird so
    über den Tracking-Zeitraum weiterverfolgt, auch wenn er aussortiert wurde oder stirbt."""
    today = now_utc().date().isoformat()
    new = {}
    for m in all_metrics:
        if m["key"] not in track and m["key"] not in new:
            new[m["key"]] = {"symbol": m["symbol"],
                             "f": {k: (round(m[k], 4) if isinstance(m.get(k), float) else m.get(k))
                                   for k in RAW_FIELDS if k != "key"}}
    if new:
        tf = TOKENS_DIR / f"{today}.json.gz"
        cur = gz_load(tf, {})
        cur.update(new)
        gz_save(tf, cur)
        for k, v in new.items():
            track[k] = {"first": today, **v, "s": []}
    pts = {m["key"]: [m["price"], round(m["liq"]), round(m.get("mcap") or 0)] for m in all_metrics}
    for k, v in extra_prices.items():
        pts.setdefault(k, [v["price"], round(v["liq"]), round(v.get("mcap") or 0)])
    gz_save(PRICES_DIR / f"{now_utc():%Y-%m-%d_%H}.json.gz", pts)
    for k, pt in pts.items():
        if k in track:
            _add_point(track[k], [today] + pt)
    return track


def update_pairs(all_metrics: list[dict], extra: dict[str, dict]) -> dict[str, str]:
    """Merkt sich die Pool-Adresse jedes verfolgten Tokens (für das Nachladen der Tageshochs)."""
    pairs = load_json(PAIRS_FILE, {})
    for m in all_metrics:
        if m.get("pair"):
            pairs[m["key"]] = m["pair"]
    for k, v in extra.items():
        if v.get("pair"):
            pairs[k] = v["pair"]
    save_json_compact(PAIRS_FILE, dict(sorted(pairs.items())))
    return pairs


def update_ohlc(track: dict, pairs: dict[str, str]):
    """Lädt echte Tageskerzen (Hoch/Tief) von GeckoTerminal, jeweils an Tag 7, 30 und 90 nach dem
    ersten Sehen. So werden Kursspitzen zwischen den Abrufen nicht übersehen."""
    ocfg = CONFIG.get("ohlc", {})
    milestones = ocfg.get("milestones", [7, 30, 90])
    budget = ocfg.get("max_calls_per_run", 100)
    done = load_json(OHLC_DONE_FILE, {})
    today = now_utc().date()
    due = []
    for k, rec in track.items():
        if k not in pairs:
            continue
        age = (today - date.fromisoformat(rec["first"])).days
        open_ms = [m for m in milestones if age >= m and m not in done.get(k, [])]
        if open_ms:
            due.append((rec["first"], k, age))
    due.sort()
    out, calls = {}, 0
    t_start = time.monotonic()
    max_sec = ocfg.get("max_seconds_per_run", 480)
    for first, k, age in due[:budget]:
        if time.monotonic() - t_start > max_sec:
            break
        ch = k.split(":", 1)[0]
        net = GECKO_NET.get(ch)
        if not net:
            done[k] = list(milestones)
            continue
        data = HTTP_GET(f"{GECKO}/networks/{net}/pools/{pairs[k]}/ohlcv/day",
                        {"limit": min(age + 2, 1000), "currency": "usd"})
        calls += 1
        lst = (((data or {}).get("data") or {}).get("attributes") or {}).get("ohlcv_list") or []
        t0 = datetime.fromisoformat(first).replace(tzinfo=timezone.utc).timestamp()
        candles = sorted([[int(c[0])] + [float(x) for x in c[1:6]] for c in lst if len(c) >= 6 and c[0] >= t0])
        if candles:
            out[k] = candles
        if data is not None or age >= max(milestones):
            done[k] = sorted(set(done.get(k, [])) | {m for m in milestones if age >= m})
            if is_dead(track[k]):  # tot: es kommen keine neuen Hochs mehr, spätere Abrufe sparen
                done[k] = list(milestones)
        SLEEP(ocfg.get("pause_seconds", 6))  # GeckoTerminal drosselt kostenlose Abrufe
    if out:
        gz_save(OHLC_DIR / f"{now_utc():%Y-%m-%d_%H}.json.gz", out)
    save_json_compact(OHLC_DONE_FILE, dict(sorted(done.items())))
    log(f"Tageshochs: {len(out)} Tokens nachgeladen ({calls} Abrufe), {max(0, len(due) - calls)} warten noch")


def save_json_compact(path: Path, obj):
    """Eine Zeile je Eintrag – klein und für Git gut vergleichbar."""
    path.parent.mkdir(parents=True, exist_ok=True)
    items = [f"{json.dumps(k)}:{json.dumps(v, ensure_ascii=False, separators=(',', ':'))}" for k, v in obj.items()]
    path.write_text("{\n" + ",\n".join(items) + "\n}\n", encoding="utf-8")


def migrate_old_tracking():
    """Einmalig: alte tracking.json.gz in Tagesdateien umwandeln (spart Speicher im Repository)."""
    if not TRACK_FILE.exists():
        return
    old = gz_load(TRACK_FILE, {})
    by_first: dict[str, dict] = {}
    by_day: dict[str, dict] = {}
    for k, rec in old.items():
        ch, addr = k.split(":", 1)
        k2 = f"{ch}:{norm(ch, addr)}"
        by_first.setdefault(rec["first"], {})[k2] = {"symbol": rec.get("symbol"), "f": rec.get("f") or {}}
        for pt in rec.get("s") or []:
            by_day.setdefault(pt[0], {})[k2] = pt[1:]
    for d, toks in by_first.items():
        gz_save(TOKENS_DIR / f"{d}.json.gz", toks)
    for d, pts in by_day.items():
        gz_save(PRICES_DIR / f"{d}_00.json.gz", pts)
    TRACK_FILE.unlink()
    log(f"Tracking migriert: {len(old)} Tokens, {len(by_day)} Tage")


def update_after_sale(state: dict, prices: dict[str, dict]):
    """Verfolgt verkaufte Positionen weiter: Höchststand und Kurs nach dem Verkauf."""
    pf = state.get("portfolio") or {}
    today = now_utc().date().isoformat()
    days = CONFIG.get("tracking", {}).get("after_sale_days")  # None/0 = unbegrenzt
    for pos in pf.get("closed", []):
        if days and (date.fromisoformat(today) - date.fromisoformat(pos["closed"])).days > days:
            continue
        q = prices.get(pos["key"])
        if not q or q["price"] <= 0:
            continue
        pos["post_price"] = q["price"]
        pos["post_liq"] = round(q["liq"])
        pos["post_updated"] = today
        if pos["closed"] != today:  # Höchststand erst ab dem Tag nach dem Verkauf
            pos["post_max"] = max(pos.get("post_max", 0), q["price"])
            if pos.get("post_max_date") is None or q["price"] >= pos["post_max"]:
                pos["post_max_date"] = today


def is_main_run(state: dict) -> bool:
    """Erster Lauf des Tages ab 5 Uhr UTC = Hauptlauf (Depot + Telegram), sonst nur Datensammlung."""
    if os.getenv("FORCE_MAIN") == "1":
        return True
    today = now_utc().date().isoformat()
    hist = ((state.get("portfolio") or {}).get("history") or [])
    done_today = bool(hist) and hist[-1]["date"] == today
    return not done_today and now_utc().hour >= 5


def run():
    chains = CONFIG["chains"]
    state = load_json(STATE_FILE, {})
    snaps = load_json(SNAP_FILE, {})
    migrate_old_tracking()
    main = is_main_run(state)
    log("Hauptlauf (Depot + Telegram)" if main else "Sammellauf (nur Daten)")
    if main:
        state["eur_per_usd"] = eur_rate()

    log("Sammle Kandidaten …")
    found = collect_candidates(chains)
    for ch in chains:
        # bestehende Depot-Positionen immer mit abfragen
        for p in (state.get("portfolio") or {}).get("positions", []):
            if p["chain"] == ch:
                found[ch].add(p["address"])
        log(f"  {ch}: {len(found[ch])} Tokens")

    metrics: list[dict] = []
    all_metrics: list[dict] = []
    prices: dict[str, dict] = {}
    rejected: dict[str, int] = {}
    for ch in chains:
        pairs = fetch_pairs(ch, sorted(found[ch]))
        for addr, p in pairs.items():
            m = to_metrics(ch, p)
            m["key"] = f"{ch}:{addr}"
            prices[m["key"]] = {"price": m["price"], "liq": m["liq"], "mcap": m["mcap"]}
            m["pre_score"], _ = score(m)
            reason = base_filter(m)
            m["filter"] = reason or "ok"
            all_metrics.append(m)
            if reason:
                rejected[reason] = rejected.get(reason, 0) + 1
                continue
            metrics.append(m)
    log(f"Nach Basisfilter: {len(metrics)} · verworfen: {rejected}")

    # Rohdaten ALLER gesehenen Tokens dieses Laufs sichern
    gz_save(RAW_DIR / f"{now_utc():%Y-%m-%d_%H}.json.gz",
            [{k: m.get(k) for k in RAW_FIELDS} for m in all_metrics])

    # Bereits verfolgte Tokens, die heute nicht auftauchen, nachpreisen (tote Tokens nicht mehr)
    track_old = load_tracking()
    today = now_utc().date().isoformat()
    missing: dict[str, list[str]] = {}
    for key, rec in track_old.items():
        if key in prices or (rec["s"] and rec["s"][-1][0] == today) or is_dead(rec):
            continue
        ch, addr = key.split(":", 1)
        if ch in chains:
            missing.setdefault(ch, []).append(addr)
    # verkaufte Positionen ebenfalls nachpreisen
    days = CONFIG.get("tracking", {}).get("after_sale_days")  # None/0 = unbegrenzt
    for pos in (state.get("portfolio") or {}).get("closed", []):
        if pos["key"] in prices or (days and (date.fromisoformat(today) - date.fromisoformat(pos["closed"])).days > days):
            continue
        lst = missing.setdefault(pos["chain"], [])
        if pos["address"] not in lst:
            lst.append(pos["address"])
    extra: dict[str, dict] = {}
    for ch, addrs in missing.items():
        for addr, p in fetch_pairs(ch, addrs).items():
            mm = to_metrics(ch, p)
            extra[f"{ch}:{addr}"] = {"price": mm["price"], "liq": mm["liq"], "mcap": mm["mcap"], "pair": mm["pair"]}
    prices.update(extra)
    track = update_tracking(all_metrics, extra, track_old)
    log(f"Tracking: {len(track)} Tokens in der Datenbank, {len(extra)} nachgepreist")
    try:
        pairs = update_pairs(all_metrics, extra)
        update_ohlc(track, pairs)
    except Exception as e:  # Nachladen darf den Lauf nie abbrechen
        log(f"Tageshochs übersprungen: {e}")

    update_after_sale(state, prices)
    state["collect"] = {"last": now_utc().isoformat(timespec="seconds"), "tracked": len(track),
                        "seen": len(all_metrics), "passed": len(metrics), "rejected": rejected}
    try:
        from analyze import buckets
        state["analysis"] = buckets(track)
    except Exception as e:  # Auswertung darf den Lauf nie abbrechen
        log(f"Auswertung übersprungen: {e}")

    if not main:
        save_json(STATE_FILE, state)
        from dashboard import build_dashboard
        build_dashboard(state, CONFIG, DOCS / "index.html")
        log("Sammellauf fertig.")
        return

    # Vorab-Score ohne Holderdaten, dann nur die besten auf Sicherheit prüfen
    for m in metrics:
        m["score"], _ = score(m)
    metrics.sort(key=lambda m: m["score"], reverse=True)
    to_check = metrics[:CONFIG["safety_checks_per_run"]]

    by_chain: dict[str, list[dict]] = {}
    for m in to_check:
        by_chain.setdefault(m["chain"], []).append(m)
    for ch, items in by_chain.items():
        if ch == "solana":
            for m in items:
                m.update({f"s_{k}": v for k, v in safety_solana(m["address"]).items()})
                SLEEP(1.2)
        else:
            res = safety_evm(ch, [m["address"] for m in items])
            for m in items:
                m.update({f"s_{k}": v for k, v in res.get(m["address"], {"ok": None, "flags": []}).items()})

    ranked: list[dict] = []
    t = now_utc().timestamp()
    for m in to_check:
        m["safety_ok"] = m.get("s_ok")
        m["flags"] = m.get("s_flags") or []
        m["holders"] = m.get("s_holders")
        m["top10"] = m.get("s_top10")
        m["lp_locked"] = m.get("s_lp_locked")
        if m["top10"] is not None and m["top10"] > CONFIG["filter"]["max_top10_pct"]:
            m["safety_ok"] = False
            m["flags"].append(f"Top-10 > {CONFIG['filter']['max_top10_pct']}%")
        m["holder_growth_7d"] = holder_growth(snaps, m["key"], m["holders"])
        m["score"], m["why"] = score(m)
        if m["safety_ok"] is False:
            m["score"] = min(m["score"], 30)
        ranked.append(m)
        # Snapshot für späteres Holder-Wachstum
        snaps.setdefault(m["key"], []).append({"t": int(t), "holders": m["holders"], "liq": round(m["liq"]),
                                               "mcap": round(m["mcap"]), "price": m["price"]})
    ranked.sort(key=lambda m: m["score"], reverse=True)

    # Snapshots: bis 400 Einträge je Token, erst nach 200 Tagen ohne neuen Eintrag entfernen
    # (alle Werte stehen zusätzlich dauerhaft in data/runs/JJJJ-MM-TT.json)
    cutoff = t - 200 * 86400
    snaps = {k: v[-400:] for k, v in snaps.items() if v and v[-1]["t"] >= cutoff}

    # Sicherheitscheck für offene Positionen (Ausstiegssignale)
    pos_safety: dict[str, dict] = {m["key"]: {"ok": m["safety_ok"], "flags": m["flags"], "holders": m["holders"]}
                                   for m in ranked}
    todo: dict[str, list[str]] = {}
    for pos in (state.get("portfolio") or {}).get("positions", []):
        if pos["key"] not in pos_safety:
            todo.setdefault(pos["chain"], []).append(pos["address"])
    for ch, addrs in todo.items():
        if ch == "solana":
            for addr in addrs:
                pos_safety[f"{ch}:{addr}"] = safety_solana(addr)
                SLEEP(1.2)
        else:
            for addr, r in safety_evm(ch, addrs).items():
                pos_safety[f"{ch}:{addr}"] = r
    for k, r in pos_safety.items():
        t10 = r.get("top10")
        if t10 is not None and t10 > CONFIG["filter"]["max_top10_pct"] and r.get("ok") is not None:
            r["ok"] = False
            r["flags"] = list(r.get("flags") or []) + [f"Top-10 > {CONFIG['filter']['max_top10_pct']}%"]
        if r.get("ok") is None or any(f in ("RugCheck nicht erreichbar", "GoPlus ohne Daten") for f in r.get("flags") or []):
            r["ok"] = None  # fehlende Daten sind kein Verkaufsgrund

    events = update_portfolio(state, prices, ranked, pos_safety)
    update_after_sale(state, prices)
    state["last_run"] = now_utc().isoformat(timespec="seconds")
    state["last_stats"] = {"collected": sum(len(v) for v in found.values()), "passed_filter": len(metrics),
                           "checked": len(to_check), "rejected": rejected}
    keep = ("chain", "address", "symbol", "name", "url", "price", "liq", "mcap", "vol24", "chg24",
            "age_days", "score", "why", "flags", "safety_ok", "holders", "holder_growth_7d", "top10",
            "lp_locked", "buys24", "sells24", "key", "image", "pair", "lp_locked", "chg6", "vol24",
            "buys6", "sells6", "twitter", "telegram", "website", "boosted")
    run_rows = [{k: m.get(k) for k in keep} for m in ranked]
    state["last_ranked"] = run_rows[:40]
    state.setdefault("events", [])
    state["events"] = ([{"date": now_utc().date().isoformat(), "text": e} for e in events] + state["events"])[:200]

    save_json(STATE_FILE, state)
    save_json(SNAP_FILE, snaps)
    save_json(RUNS_DIR / f"{now_utc():%Y-%m-%d}.json", run_rows)

    from dashboard import build_dashboard
    build_dashboard(state, CONFIG, DOCS / "index.html")
    try:
        from analyze import export
        export(track, ROOT / "out" / "analyse.csv")
    except Exception as e:  # Auswertung darf den Lauf nie abbrechen
        log(f"Auswertung übersprungen: {e}")
    send_telegram(telegram_text(ranked, events, state))
    log(f"Fertig. {len(ranked)} geprüft, {len(events)} Depot-Ereignisse.")


if __name__ == "__main__":
    sys.exit(run())
