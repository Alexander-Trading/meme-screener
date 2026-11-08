#!/usr/bin/env python3
"""
Auswertung der gesammelten Daten: Welche Merkmale am ersten Tag hatten die Coins,
die danach am besten liefen?

Für jeden je gesehenen Token werden verbunden:
  - Startmerkmale beim ersten Sehen (data/tokens)
  - Holder, Top-10-Anteil, Sicherheitscheck, voller Score beim ersten Check (data/runs)
  - Kursverlauf aus den Abrufen (data/prices) und echte Tageshochs (data/ohlc)

  python analyze.py          -> Zusammenfassung in der Konsole
  python analyze.py --csv    -> zusätzlich out/analyse.csv (Excel, Semikolon)
Nach jedem Hauptlauf liegt analyse.csv außerdem in GitHub Actions unter "Artifacts".
"""
from __future__ import annotations

import csv
import json
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUNS_DIR = ROOT / "data" / "runs"
FEATURES = ("price", "liq", "mcap", "vol24", "buys24", "sells24", "buys6", "sells6", "chg1", "chg6", "chg24",
            "age_days", "twitter", "telegram", "website", "boosted", "pre_score", "filter", "dex")
CHECK_FIELDS = ("score", "holders", "top10", "safety_ok", "lp_locked", "holder_growth_7d")
HORIZONS = (7, 30, 90)


def _d(s: str) -> int:
    return date.fromisoformat(s).toordinal()


def _day(ts: float) -> int:
    return datetime.fromtimestamp(ts, timezone.utc).date().toordinal()


def load_first_checks() -> dict[str, dict]:
    """Erster Sicherheitscheck je Token (Holder, Top-10, Sicherheit, voller Score)."""
    first: dict[str, dict] = {}
    for f in sorted(RUNS_DIR.glob("*.json")):
        try:
            rows_ = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for r in rows_:
            k = r.get("key")
            if k and k not in first:
                first[k] = {"check_date": f.stem, **{c: r.get(c) for c in CHECK_FIELDS}}
    return first


def outcomes(rec: dict) -> dict:
    """Entwicklung ab dem ersten Sehen. Hochs aus Abrufen UND Tageskerzen (ab dem Folgetag,
    damit keine Spitze vor dem ersten Sehen zählt)."""
    s = rec.get("s") or []
    p0 = (rec.get("f") or {}).get("price") or (s[0][1] if s else 0)
    if not p0 or not s:
        return {}
    d0 = _d(rec["first"])
    candles = [(_day(c[0]) - d0, c[2]) for c in rec.get("o") or [] if _day(c[0]) > d0]
    points = [(_d(x[0]) - d0, x[1]) for x in s]
    covered = max([a for a, _ in points] + [a for a, _ in candles])
    out = {"days_tracked": covered, "last_mult": round(s[-1][1] / p0, 3),
           "alive": int((s[-1][2] or 0) >= 3000), "has_candles": int(bool(candles))}
    highs = points + candles
    out["max_ever"] = round(max(h for _, h in highs) / p0, 3)
    for n in HORIZONS:
        later = [p for a, p in points if a >= n]
        out[f"mult_{n}d"] = round(later[0] / p0, 3) if later else ""
        within = [h for a, h in highs if a <= n]
        out[f"max_{n}d"] = round(max(within) / p0, 3) if covered >= n and within else ""
    return out


def rows(track: dict, checks: dict | None = None):
    checks = load_first_checks() if checks is None else checks
    for key, rec in track.items():
        o = outcomes(rec)
        if not o:
            continue
        f = rec.get("f") or {}
        chain, addr = key.split(":", 1)
        c = checks.get(key) or {}
        yield {"chain": chain, "address": addr, "symbol": rec.get("symbol"), "first_seen": rec["first"],
               "pair": f.get("pair"), **{k: f.get(k) for k in FEATURES},
               **{k: c.get(k) for k in CHECK_FIELDS}, **o}


def export(track: dict, path: Path):
    data = list(rows(track))
    if not data:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = list(data[0].keys())
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, delimiter=";")
        w.writeheader()
        for r in data:
            w.writerow({k: (str(v).replace(".", ",") if isinstance(v, float) else v) for k, v in r.items()})


def _stat(label: str, group: list[dict], horizon: int) -> dict | None:
    n = len(group)
    if not n:
        return None
    mults = sorted((r[f"mult_{horizon}d"] if r[f"mult_{horizon}d"] != "" else r["last_mult"]) for r in group)
    return {"label": label, "n": n,
            "win": round(sum(r[f"max_{horizon}d"] >= 3 for r in group) / n * 100, 1),
            "win10": round(sum(r[f"max_{horizon}d"] >= 10 for r in group) / n * 100, 1),
            "dead": round(sum(not r["alive"] for r in group) / n * 100, 1),
            "median": round(mults[n // 2], 2)}


def _num(r: dict, k: str):
    v = r.get(k)
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _ranges(data, key, bands, horizon):
    out = []
    for label, lo, hi in bands:
        g = [r for r in data if _num(r, key) is not None and lo <= r[key] < hi]
        out.append(_stat(label, g, horizon))
    g = [r for r in data if _num(r, key) is None]
    if g and len(g) < len(data):
        out.append(_stat("keine Daten", g, horizon))
    return out


def buckets(track: dict) -> dict:
    """Strukturierte Auswertung fürs Dashboard. 30 Tage, solange zu wenig Daten da sind 7 Tage."""
    all_rows = list(rows(track))
    res = {"tracked": len(track), "with_history": len(all_rows), "horizon": None, "groups": [], "top": []}
    for horizon in (30, 7):
        data = [r for r in all_rows if r.get(f"max_{horizon}d") not in ("", None)]
        if len(data) >= 20:
            break
    else:
        return res
    res["horizon"], res["n"] = horizon, len(data)
    res["with_candles"] = sum(r["has_candles"] for r in data)
    for r in data:
        r["bratio"] = r["buys24"] / max(r["sells24"] or 0, 1) if r.get("buys24") is not None else None
        r["vl"] = (r["vol24"] / r["liq"]) if r.get("liq") else None
        r["lm"] = (r["liq"] / r["mcap"] * 100) if r.get("mcap") else None

    def add(title, items):
        g = [s for s in items if s]
        if g:
            res["groups"].append({"title": title, "rows": g})

    H = horizon
    add("Score beim ersten Sehen", _ranges(data, "pre_score", [("0–39", 0, 40), ("40–54", 40, 55), ("55–64", 55, 65),
                                                                ("65–74", 65, 75), ("75–100", 75, 101)], H))
    add("Voller Score (mit Holderdaten)", _ranges(data, "score", [("0–39", 0, 40), ("40–54", 40, 55), ("55–64", 55, 65),
                                                                  ("65–74", 65, 75), ("75–100", 75, 101)], H))
    add("Sicherheitscheck", [_stat("bestanden", [r for r in data if r["safety_ok"] is True], H),
                             _stat("durchgefallen", [r for r in data if r["safety_ok"] is False], H),
                             _stat("nicht geprüft", [r for r in data if r["safety_ok"] is None], H)])
    add("Alter beim ersten Sehen", _ranges(data, "age_days", [("unter 3 Tage", 0, 3), ("3–14 Tage", 3, 14),
                                                              ("14–60 Tage", 14, 60), ("über 60 Tage", 60, 1e9)], H))
    add("Marktkapitalisierung", _ranges(data, "mcap", [("unter 250k $", 0, 2.5e5), ("250k–1 M $", 2.5e5, 1e6),
                                                       ("1–5 M $", 1e6, 5e6), ("5–50 M $", 5e6, 5e7),
                                                       ("über 50 M $", 5e7, 1e15)], H))
    add("Liquidität", _ranges(data, "liq", [("unter 30k $", 0, 3e4), ("30–100k $", 3e4, 1e5),
                                            ("100–500k $", 1e5, 5e5), ("über 500k $", 5e5, 1e12)], H))
    add("Liquidität/MCap", _ranges(data, "lm", [("unter 5 %", 0, 5), ("5–15 %", 5, 15), ("15–30 %", 15, 30),
                                                ("über 30 %", 30, 1e9)], H))
    add("Volumen/Liquidität (24 h)", _ranges(data, "vl", [("unter 0,5", 0, .5), ("0,5–2", .5, 2), ("2–5", 2, 5),
                                                          ("5–15", 5, 15), ("über 15", 15, 1e12)], H))
    add("Käufe/Verkäufe (24 h)", _ranges(data, "bratio", [("unter 0,9", 0, .9), ("0,9–1,1", .9, 1.1),
                                                          ("1,1–1,5", 1.1, 1.5), ("über 1,5", 1.5, 1e9)], H))
    add("Kursänderung 24 h", _ranges(data, "chg24", [("unter −20 %", -1e9, -20), ("−20 bis 0 %", -20, 0),
                                                     ("0–50 %", 0, 50), ("50–200 %", 50, 200),
                                                     ("über 200 %", 200, 1e12)], H))
    add("Holder beim ersten Check", _ranges(data, "holders", [("unter 500", 0, 500), ("500–2.000", 500, 2000),
                                                              ("2.000–10.000", 2000, 1e4), ("über 10.000", 1e4, 1e12)], H))
    add("Top-10-Anteil", _ranges(data, "top10", [("unter 15 %", 0, 15), ("15–25 %", 15, 25), ("25–35 %", 25, 35),
                                                 ("über 35 %", 35, 101)], H))
    add("Socials", [_stat("X und Telegram", [r for r in data if r["twitter"] and r["telegram"]], H),
                    _stat("nur eins", [r for r in data if bool(r["twitter"]) != bool(r["telegram"])], H),
                    _stat("keine", [r for r in data if not r["twitter"] and not r["telegram"]], H)])
    add("Bezahlter Boost", [_stat("ja", [r for r in data if r["boosted"]], H),
                            _stat("nein", [r for r in data if not r["boosted"]], H)])
    add("Chain", [_stat(ch, [r for r in data if r["chain"] == ch], H) for ch in sorted({r["chain"] for r in data})])
    add("Basisfilter", [_stat(f, [r for r in data if r["filter"] == f], H) for f in sorted({r["filter"] for r in data})])

    best = sorted(data, key=lambda r: r[f"max_{H}d"], reverse=True)[:15]
    res["top"] = [{"symbol": r["symbol"], "chain": r["chain"], "address": r["address"], "first": r["first_seen"],
                   "max": r[f"max_{H}d"], "score": r["pre_score"], "full_score": r["score"], "age": r["age_days"],
                   "liq": r["liq"], "mcap": r["mcap"], "holders": r["holders"], "top10": r["top10"],
                   "filter": r["filter"]} for r in best]
    return res


def summary(track: dict):
    res = buckets(track)
    if not res["horizon"]:
        print(f"{res['tracked']} Tokens verfolgt – noch zu wenig Verlauf für eine Auswertung.")
        return
    print(f"{res['n']} Tokens mit mindestens {res['horizon']} Tagen Verlauf "
          f"({res['with_candles']} mit Tageskerzen)\n")
    for g in res["groups"]:
        print(g["title"])
        for r in g["rows"]:
            print(f"  {r['label'][:24]:24s} n={r['n']:5d}  ≥3x {r['win']:5.1f}%  ≥10x {r['win10']:5.1f}%  "
                  f"tot {r['dead']:5.1f}%  Median {r['median']:.2f}x")
        print()


if __name__ == "__main__":
    import sys
    from screener import load_tracking
    track = load_tracking()
    if not track:
        print("Noch keine Daten. Erst den Screener einige Tage laufen lassen.")
    else:
        summary(track)
        if "--csv" in sys.argv:
            export(track, ROOT / "out" / "analyse.csv")
            print("CSV geschrieben: out/analyse.csv")
