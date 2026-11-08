#!/usr/bin/env python3
"""
Auswertung der gesammelten Daten.

Für jeden je gesehenen Token: Merkmale am ersten Tag + spätere Entwicklung
(Kurs nach 7/30/90 Tagen, bestes Vielfaches, ob er noch lebt).
Damit lässt sich prüfen, welche Startmerkmale Gewinner wirklich ausgezeichnet haben.

  python analyze.py          -> Zusammenfassung in der Konsole
  data/analyse.csv           -> wird bei jedem Hauptlauf neu geschrieben (Excel-tauglich)
"""
from __future__ import annotations

import csv
import gzip
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FEATURES = ("price", "liq", "mcap", "vol24", "buys24", "sells24", "buys6", "sells6", "chg1", "chg6", "chg24",
            "age_days", "twitter", "telegram", "website", "boosted", "pre_score", "filter")


def _d(s: str) -> int:
    return date.fromisoformat(s).toordinal()


def outcomes(rec: dict) -> dict:
    s = rec.get("s") or []
    p0 = (rec.get("f") or {}).get("price") or (s[0][1] if s else 0)
    if not p0 or not s:
        return {}
    d0 = _d(rec["first"])
    out = {"days_tracked": _d(s[-1][0]) - d0, "last_mult": round(s[-1][1] / p0, 3),
           "alive": int(s[-1][2] >= 3000)}
    for n in (7, 30, 90):
        pts = [x for x in s if _d(x[0]) - d0 <= n]
        later = [x for x in s if _d(x[0]) - d0 >= n]
        out[f"mult_{n}d"] = round(later[0][1] / p0, 3) if later else ""
        out[f"max_{n}d"] = round(max(x[1] for x in pts) / p0, 3) if pts and later else ""
    return out


def rows(track: dict):
    for key, rec in track.items():
        o = outcomes(rec)
        if not o:
            continue
        f = rec.get("f") or {}
        chain, addr = key.split(":", 1)
        yield {"chain": chain, "address": addr, "symbol": rec.get("symbol"), "first_seen": rec["first"],
               **{k: f.get(k) for k in FEATURES}, **o}


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


def summary(track: dict, horizon: int = 30, win_mult: float = 3.0):
    data = [r for r in rows(track) if r.get(f"max_{horizon}d") not in ("", None)]
    print(f"{len(data)} Tokens mit mindestens {horizon} Tagen Verlauf")
    if not data:
        print("Noch zu wenig Daten – nach einigen Wochen erneut ausführen.")
        return

    def stat(group):
        n = len(group)
        wins = sum(1 for r in group if r[f"max_{horizon}d"] >= win_mult)
        dead = sum(1 for r in group if not r["alive"])
        med = sorted(r[f"mult_{horizon}d"] or 0 for r in group)[n // 2]
        return f"n={n:4d}  ≥{win_mult:g}x: {wins/n*100:5.1f}%  tot: {dead/n*100:5.1f}%  Median: {med:.2f}x"

    print("\nNach Score am ersten Tag:")
    for lo, hi in ((0, 40), (40, 55), (55, 65), (65, 75), (75, 101)):
        g = [r for r in data if lo <= (r["pre_score"] or 0) < hi]
        if g:
            print(f"  {lo:3d}-{hi-1:<3d} {stat(g)}")
    print("\nNach Alter beim ersten Sehen:")
    for lo, hi in ((0, 3), (3, 14), (14, 60), (60, 9999)):
        g = [r for r in data if lo <= (r["age_days"] or 0) < hi]
        if g:
            print(f"  {lo:3d}-{hi:<4d}T {stat(g)}")
    print("\nNach Basisfilter:")
    for flt in sorted({r["filter"] for r in data}):
        print(f"  {flt[:28]:28s} {stat([r for r in data if r['filter'] == flt])}")


def buckets(track: dict, win_mult: float = 3.0) -> dict:
    """Strukturierte Auswertung fürs Dashboard. Nutzt 30 Tage, solange zu wenig Daten da sind 7 Tage."""
    all_rows = list(rows(track))
    res = {"tracked": len(track), "with_history": len(all_rows), "horizon": None, "groups": [], "top": []}
    for horizon in (30, 7):
        data = [r for r in all_rows if r.get(f"max_{horizon}d") not in ("", None)]
        if len(data) >= 20:
            break
    else:
        return res
    res["horizon"], res["n"] = horizon, len(data)

    def stat(label, group):
        n = len(group)
        if not n:
            return None
        mults = sorted(r[f"mult_{horizon}d"] or 0 for r in group)
        return {"label": label, "n": n,
                "win": round(sum(r[f"max_{horizon}d"] >= win_mult for r in group) / n * 100, 1),
                "dead": round(sum(not r["alive"] for r in group) / n * 100, 1),
                "median": round(mults[n // 2], 2)}

    def add(title, items):
        g = [s for s in items if s]
        if g:
            res["groups"].append({"title": title, "rows": g})

    add("Score am ersten Tag", [stat(f"{lo}–{hi-1}", [r for r in data if lo <= (r["pre_score"] or 0) < hi])
                                for lo, hi in ((0, 40), (40, 55), (55, 65), (65, 75), (75, 101))])
    add("Alter beim ersten Sehen", [stat(lbl, [r for r in data if lo <= (r["age_days"] or 0) < hi])
                                    for lbl, lo, hi in (("unter 3 Tage", 0, 3), ("3–14 Tage", 3, 14),
                                                        ("14–60 Tage", 14, 60), ("über 60 Tage", 60, 1e9))])
    add("Liquidität", [stat(lbl, [r for r in data if lo <= (r["liq"] or 0) < hi])
                       for lbl, lo, hi in (("unter 30k $", 0, 3e4), ("30–100k $", 3e4, 1e5),
                                           ("100–500k $", 1e5, 5e5), ("über 500k $", 5e5, 1e12))])
    add("Socials", [stat("X und Telegram", [r for r in data if r["twitter"] and r["telegram"]]),
                    stat("nur eins", [r for r in data if bool(r["twitter"]) != bool(r["telegram"])]),
                    stat("keine", [r for r in data if not r["twitter"] and not r["telegram"]])])
    add("Basisfilter", [stat(f, [r for r in data if r["filter"] == f]) for f in sorted({r["filter"] for r in data})])

    best = sorted(data, key=lambda r: r[f"max_{horizon}d"], reverse=True)[:10]
    res["top"] = [{"symbol": r["symbol"], "chain": r["chain"], "address": r["address"], "first": r["first_seen"],
                   "max": r[f"max_{horizon}d"], "score": r["pre_score"], "age": r["age_days"],
                   "liq": r["liq"], "mcap": r["mcap"], "filter": r["filter"]} for r in best]
    return res


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
