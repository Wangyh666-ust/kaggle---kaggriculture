"""Measure the ADV clone gate on the real ladder corpus.

Gate G1 ("same turn-0 tape"): the rival's money after the first turn equals ours,
i.e. its first-call market action had the same net cash effect as ours.  We also
record the byte-level turn-0 market signature equality to check that G1 is not
looser than the signature test (they coincide in every local game measured).

Reports, per gate state: n, W/L/T, win rate, mean margin -- and the same for the
ladder's own clone class (turn-1 signature == ours, mirror_share's definition).

Usage: .venv/Scripts/python scripts/adv_gate_ladder.py
"""
import collections
import glob
import json
import multiprocessing as mp
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OURS = "ReD_MooN_rise"
DIRS = ["replays_v21", "replays_v23", "replays_v23r", "replays_v24", "replays_v24r",
        "replays_v25", "replays_v27", "replays_v28", "replays_ladder",
        "replays_ladder_ops", "replays_all", "replays_top"]


def sig(mk):
    return json.dumps([list(o) for o in (mk or [])], separators=(",", ":"))


def one(path):
    try:
        d = json.load(open(path, encoding="utf-8"))
        names = list(d["info"]["TeamNames"])
        if OURS not in names:
            return None
        if names[0] == names[1]:
            return None
        us = names.index(OURS)
        opp = 1 - us
        st = d["steps"]
        m1 = [st[1][s]["observation"]["farms"][s]["money"] for s in (0, 1)]
        a0 = [sig((st[1][s].get("action") or {}).get("market")) for s in (0, 1)]
        a1 = [sig((st[2][s].get("action") or {}).get("market")) for s in (0, 1)]
        sig_eq = a0[0] == a0[1]
        money_eq = abs(m1[0] - m1[1]) < 0.5
        clone = a1[us] == a1[opp]
        return {"file": os.path.relpath(path, ROOT), "us": us,
                "dmoney1": m1[us] - m1[opp], "sig_eq": sig_eq,
                "money_eq": money_eq, "clone": clone,
                "margin": d["rewards"][us] - d["rewards"][opp],
                "opp": names[opp]}
    except Exception as e:  # noqa: BLE001
        return {"file": path, "err": repr(e)}


def main():
    files = []
    for dd in DIRS:
        p = os.path.join(ROOT, dd)
        if os.path.isdir(p):
            files += sorted(glob.glob(os.path.join(p, "episode-*-replay.json")))
    files = sorted(set(files))
    print(f"{len(files)} replay files")
    workers = max(1, min(12, (os.cpu_count() or 4) - 4))
    with mp.Pool(workers) as pool:
        recs = [r for r in pool.imap_unordered(one, files, chunksize=2) if r]
    bad = [r for r in recs if "err" in r]
    recs = [r for r in recs if "err" not in r]
    print(f"{len(recs)} usable ladder games ({len(bad)} unparsed)")

    def show(name, sub):
        n = len(sub)
        if not n:
            print(f"{name:36s} n=0")
            return
        w = sum(1 for r in sub if r["margin"] > 0)
        l = sum(1 for r in sub if r["margin"] < 0)
        m = [r["margin"] for r in sub]
        print(f"{name:36s} n={n:4d} {w:3d}W-{l:3d}L-{n-w-l:3d}T  win {w/n:6.1%}  "
              f"mean ${sum(m)/n:+8.0f}  median ${sorted(m)[n//2]:+8.0f}")

    show("ALL", recs)
    show("G1 fires (money eq @ step1)", [r for r in recs if r["money_eq"]])
    show("G1 silent", [r for r in recs if not r["money_eq"]])
    show("turn-0 sig eq", [r for r in recs if r["sig_eq"]])
    show("ladder clone class (turn-1 sig)", [r for r in recs if r["clone"]])
    show("  clone AND G1 fires", [r for r in recs if r["clone"] and r["money_eq"]])
    show("  clone AND G1 silent", [r for r in recs if r["clone"] and not r["money_eq"]])
    show("  non-clone AND G1 fires", [r for r in recs if not r["clone"] and r["money_eq"]])
    print("\nagreement sig_eq vs money_eq:")
    c = collections.Counter((r["sig_eq"], r["money_eq"]) for r in recs)
    for k, v in sorted(c.items()):
        print(f"  sig_eq={k[0]} money_eq={k[1]}: {v}")
    print("\nG1 fire rate = %.1f%% (%d/%d)" % (
        100 * sum(1 for r in recs if r["money_eq"]) / max(1, len(recs)),
        sum(1 for r in recs if r["money_eq"]), len(recs)))
    print("precision of G1 for the clone class = %.0f%%" % (
        100 * sum(1 for r in recs if r["clone"] and r["money_eq"]) /
        max(1, sum(1 for r in recs if r["money_eq"]))))
    out = os.path.join(ROOT, "reverse", "adv_gate_ladder.json")
    json.dump(recs, open(out, "w", encoding="utf-8"), indent=1)
    print("saved ->", os.path.relpath(out, ROOT))


if __name__ == "__main__":
    main()
