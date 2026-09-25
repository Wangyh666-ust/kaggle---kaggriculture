"""Who are we actually losing to? Fingerprint ladder opponents from replays.

The question this answers, and why it decides strategy. Our recent ladder losses
are hairline: 5 of 6 under $510, the smallest $77. Two very different worlds
produce that pattern, and they call for opposite actions:

  * all opponents run the same code as us -> the margins are coin flips, no local
    improvement can move them, and the right play is score management;
  * some opponents run a different agent and we systematically lose a few hundred
    dollars to it -> there is a concrete target, and it is worth chasing.

A replay does not contain the opponent's source, but it does contain every action
they took, and the first turns are the most identifying part of this architecture:
tapes are FIXED for steps 0..143, so two agents on the same tape emit byte-equal
opening orders regardless of seed. So the opening signature is a code fingerprint,
not a behaviour sample -- it separates "same agent" from "a cousin" exactly.

Usage:
  .venv/Scripts/python scripts/opponent_fingerprint.py                    # cached summaries
  .venv/Scripts/python scripts/opponent_fingerprint.py --ref 56524969 --scan 24
  .venv/Scripts/python scripts/opponent_fingerprint.py --ours experiments/v41/cxd.py
"""
import argparse
import collections
import glob
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
CACHE = os.path.join(ROOT, "tmp_replays")

CROPS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON")


def signature(steps, seat, upto=4):
    """The seat's market orders over its first `upto` turns that emit any.

    The tape's opening is seed-independent, so this is a hash of the CODE, not of
    a lucky game. Reorders by the reflex layers are visible here too, which is
    what lets a stacked agent be told apart from its own base.
    """
    out = []
    for r in steps:
        d = r.get(seat)
        if not d:
            continue
        if d["order_list"]:
            out.append([[str(x) for x in o] for o in d["order_list"]])
            if len(out) >= upto:
                break
    return out


def sigkey(sig):
    return json.dumps(sig, separators=(",", ":"), ensure_ascii=False)


def phase_profile(steps, seat):
    """Coarse behaviour, for the case where two agents share an opening."""
    rs = [r[seat] for r in steps if r.get(seat)]
    if not rs:
        return {}
    last = rs[-1]
    peak_shed = collections.Counter()
    for d in rs:
        for k, v in d["shed"].items():
            peak_shed[k] = max(peak_shed[k], int(v))
    return {
        "quads_end": len(last.get("shops") or []),
        "planted_end": sum(last["tiles"].get(c, 0) for c in CROPS),
        "pasture_end": last["tiles"].get("PASTURE", 0),
        "empty_end": last["tiles"].get("EMPTY", 0),
        "weed_end": last["tiles"].get("WEED", 0),
        "peak_hands": max(d["hands"] for d in rs),
        "idle_share": (sum(d["idle"] for d in rs) / max(1, sum(d["units"] for d in rs))),
        "peak_shed_total": sum(peak_shed.values()),
    }


def load_summaries():
    out = []
    for p in sorted(glob.glob(os.path.join(CACHE, "ep-*-summary.json"))):
        try:
            import field_ledger as FL
            g = json.load(open(p, encoding="utf-8"))
            g["steps"] = FL.denormalise(g["steps"])
            out.append(g)
        except Exception:
            continue
    return out


def fetch_more(ref, scan):
    import subprocess
    PY = os.path.join(ROOT, ".venv", "Scripts", "python.exe")

    def kaggle(*a):
        r = subprocess.run([PY, "-m", "kaggle", *a], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=300)
        return (r.stdout or "") + (r.stderr or "")

    raw = kaggle("competitions", "episodes", str(ref), "--format", "json")
    i, j = raw.find("["), raw.rfind("]")
    eps = json.loads(raw[i:j + 1]) if i >= 0 and j > i else []
    eps.sort(key=lambda e: e.get("createTime") or "", reverse=True)
    got = 0
    for e in eps[:scan]:
        eid = int(e["id"])
        if os.path.exists(os.path.join(CACHE, f"ep-{eid}-summary.json")):
            continue
        kaggle("competitions", "replay", str(eid), "-p", CACHE, "-q")
        hits = glob.glob(os.path.join(CACHE, f"episode-{eid}-replay.json"))
        if not hits:
            continue
        import field_ledger as FL
        d = json.load(open(hits[0], encoding="utf-8"))
        info = d.get("info") or {}
        rew = [float(x) for x in d.get("rewards", [])]
        if len(rew) < 2:
            rew = [float(d["steps"][-1][s].get("reward") or 0) for s in (0, 1)]
        json.dump({"steps": FL.collect(d["steps"]),
                   "teams": list(info.get("TeamNames") or ["?", "?"]),
                   "rewards": rew, "episode": info.get("EpisodeId"),
                   "seed": info.get("seed")},
                  open(os.path.join(CACHE, f"ep-{eid}-summary.json"), "w", encoding="utf-8"))
        os.remove(hits[0])
        got += 1
        print(f"  fetched ep {eid}", flush=True)
    return got


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default=None)
    ap.add_argument("--scan", type=int, default=24)
    ap.add_argument("--ours", default="experiments/v41/cxd.py",
                    help="our agent, to compute the reference opening signature")
    ap.add_argument("--team", default=None)
    args = ap.parse_args()

    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass

    if args.ref:
        print(f"抓取提交 {args.ref} 的回放（最多 {args.scan} 局）:")
        fetch_more(args.ref, args.scan)

    games = load_summaries()
    if not games:
        sys.exit("缓存里没有摘要；先给一个 --ref")
    print(f"\n缓存中共 {len(games)} 局")

    # Our reference opening, computed locally: the tape opening is seed-free.
    ours_key = None
    try:
        import importlib.util
        from kaggle_environments import make
        import field_ledger as FL
        p = os.path.join(ROOT, args.ours)
        s = importlib.util.spec_from_file_location("ours", p)
        m = importlib.util.module_from_spec(s)
        s.loader.exec_module(m)
        fn = [v for k, v in vars(m).items() if callable(v) and not k.startswith("__")][-1]
        env = make("kaggriculture", configuration={"seed": 7}, debug=False)
        env.run([fn, fn])
        ours_key = sigkey(signature(FL.collect(env.steps), 0))
        print(f"我们的开局指纹（{os.path.basename(p)}）: {ours_key[:110]}")
    except Exception as exc:  # noqa: BLE001
        print(f"（无法计算我们的基准指纹：{exc}）")

    counts = collections.Counter(t for g in games for t in g["teams"])
    team = args.team or (counts.most_common(1)[0][0] if counts else None)

    rows = []
    for g in games:
        seats = [i for i, t in enumerate(g["teams"]) if t == team]
        our = seats[0] if seats else 0
        opp = 1 - our
        rows.append({
            "episode": g["episode"], "margin": g["rewards"][our] - g["rewards"][opp],
            "opp_name": g["teams"][opp],
            "ours_key": sigkey(signature(g["steps"], our)),
            "opp_key": sigkey(signature(g["steps"], opp)),
            "opp_prof": phase_profile(g["steps"], opp),
            "our_prof": phase_profile(g["steps"], our),
        })

    print(f"\n对手名字分布（{len(set(r['opp_name'] for r in rows))} 个不同对手）:")
    for name, c in collections.Counter(r["opp_name"] for r in rows).most_common(8):
        print(f"  {c:>3}x  {name}")

    print("\n开局指纹聚类（指纹相同 = 同一份代码的开局）:")
    clusters = collections.defaultdict(list)
    for r in rows:
        clusters[r["opp_key"]].append(r)
    for key, rs in sorted(clusters.items(), key=lambda kv: -len(kv[1])):
        same_as_us = (key == ours_key)
        tag = "  ← 与我们相同" if same_as_us else ""
        wins = sum(1 for r in rs if r["margin"] > 0)
        print(f"\n  {len(rs)} 局, 我们赢了 {wins}"
              f"（胜率 {100.0*wins/len(rs):.0f}%）{tag}")
        print(f"    指纹: {key[:150]}")
        for r in rs[:6]:
            print(f"      ep {r['episode']}  我们 {r['margin']:+,.0f}  {r['opp_name']}")

    print("\n=== 对手 vs 我们的行为画像（各取中位数）===")
    prof_keys = ["quads_end", "planted_end", "pasture_end", "empty_end", "weed_end",
                 "peak_hands", "idle_share", "peak_shed_total"]
    print(f"  {'指标':16s} {'对手':>12s} {'我们':>12s}")
    for k in prof_keys:
        ov = sorted(r["opp_prof"].get(k, 0) for r in rows)
        mv = sorted(r["our_prof"].get(k, 0) for r in rows)
        if not ov:
            continue
        med = lambda v: v[len(v) // 2]
        print(f"  {k:16s} {med(ov):>12.3f} {med(mv):>12.3f}")

    # Group by OUR OWN signature first. The cache mixes games from several
    # submissions (v36 opened with BUY 20/SELL 15, v41 with BUY 10/SELL 5, v43
    # with BUY 5), and one average across them describes no version at all --
    # which is exactly how a 38% aggregate appeared for a candidate that is
    # supposed to be our best.
    print("\n=== 按【我们自己的版本】分组（用我们的开局指纹区分）===")
    ours_clusters = collections.defaultdict(list)
    for r in rows:
        ours_clusters[r["ours_key"]].append(r)
    for key, rs in sorted(ours_clusters.items(), key=lambda kv: -len(kv[1])):
        wins = sum(1 for r in rs if r["margin"] > 0)
        m = sorted(abs(r["margin"]) for r in rs)
        tag = "  ← 当前候选 v41" if key == ours_key else ""
        print(f"\n  我们的指纹 {key[:88]}{tag}")
        print(f"    n={len(rs)}  我们赢 {wins}（{100.0*wins/len(rs):.0f}%）  "
              f"|差距| 中位 ${m[len(m)//2]:,.0f}  最大 ${m[-1]:,.0f}")
        fam = collections.Counter(r["opp_key"][:60] for r in rs)
        for fk, c in fam.most_common(3):
            sel = [r for r in rs if r["opp_key"][:60] == fk]
            w = sum(1 for r in sel if r["margin"] > 0)
            print(f"      对手家族 {c:>3} 局, 我们赢 {w}（{100.0*w/len(sel):.0f}%）  {fk[:78]}")

    print("\n=== 差距 vs 指纹是否与我们相同 ===")
    for same in (True, False):
        sel = [r for r in rows if (r["opp_key"] == ours_key) == same]
        if not sel:
            continue
        wins = sum(1 for r in sel if r["margin"] > 0)
        margins = sorted(abs(r["margin"]) for r in sel)
        print(f"  对手与我们{'同' if same else '不同'}指纹: n={len(sel)}  "
              f"我们赢 {wins}（{100.0*wins/len(sel):.0f}%）  "
              f"|差距| 中位数 ${margins[len(margins)//2]:,.0f}")


if __name__ == "__main__":
    main()
