"""Check the rival-fingerprint tables against real ladder replays.

Two tables in main.py key on the rival's step-2 fingerprint
`(round(rival_money, 3), market.inventory["WHEAT"])`:

    CT_TABLE           -> a tailored wheat round-trip at steps 3 or 7/8
    _V93_ROUTE_BY_RIVAL -> a specific yarn-world route (128)

The early-death fix changed our step-0 opening wheat trade from BUY 20/SELL 15
to BUY 10/SELL 5. That trade is quoted in the market, so it moves the rival's
money at step 2 — so it can move the fingerprint off these keys and silently
disable both tables. `results/early_death_fix.md` §7 flagged exactly this as the
one unverified risk ("the panel does not hit these tables, so it cannot be
checked locally"). This script checks it against ladder replays instead.

Usage:
  .venv/Scripts/python scripts/rival_fingerprint.py replays_v23 replays_v23r replays_v25
"""
import collections
import glob
import importlib.util
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FINGERPRINT_STEP = 2


def tables():
    spec = importlib.util.spec_from_file_location("_m", os.path.join(ROOT, "main.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return getattr(m, "CT_TABLE", {}), getattr(m, "_V93_ROUTE_BY_RIVAL", {})


def fingerprints(path):
    """[(fingerprint, our_seat, shops_at_route_step, our_step0_market), ...]"""
    d = json.load(open(path, encoding="utf-8"))
    names = d["info"]["TeamNames"]
    out = []
    for seat in (0, 1):
        try:
            o = d["steps"][FINGERPRINT_STEP][seat]["observation"]
            rival = o["farms"][1 - int(o["player"])]
            fp = (round(float(rival["money"]), 3),
                  int(o["market"]["inventory"]["WHEAT"]))
        except Exception:  # noqa: BLE001
            continue
        o144 = d["steps"][144][seat]["observation"]
        shops = tuple((o144.get("town", {}).get("unlocked_shops") or [])[:2])
        s0 = d["steps"][0][seat].get("action")
        mk0 = s0.get("market") if isinstance(s0, dict) else None
        out.append((fp, seat, shops, json.dumps(mk0, separators=(",", ":")), names[seat]))
    return out


def main():
    dirs = sys.argv[1:] or ["replays_v23", "replays_v25"]
    ct, v93 = tables()
    print(f"CT_TABLE keys          : {sorted(ct)}")
    print(f"_V93_ROUTE_BY_RIVAL key: {sorted(v93)}\n")

    files = []
    for a in dirs:
        p = a if os.path.isabs(a) else os.path.join(ROOT, a)
        files += sorted(glob.glob(os.path.join(p, "episode-*-replay.json")))

    per_dir = collections.defaultdict(list)
    for path in files:
        label = os.path.basename(os.path.dirname(path))
        try:
            for fp, seat, shops, mk0, name in fingerprints(path):
                per_dir[label].append({"fp": fp, "seat": seat, "shops": shops,
                                       "mk0": mk0, "name": name,
                                       "ep": os.path.basename(path)})
        except Exception as exc:  # noqa: BLE001
            print("skip", path, exc, file=sys.stderr)

    for label, recs in sorted(per_dir.items()):
        ours = [r for r in recs if r["name"] == "ReD_MooN_rise"]
        print(f"== {label}: {len(ours)} of our seats")
        opens = collections.Counter(r["mk0"] for r in ours)
        for mk, n in opens.most_common():
            print(f"   我们的 step0 市场单 x{n}: {mk[:90]}")
        hit_ct = [r for r in ours if r["fp"] in ct]
        hit_v93 = [r for r in ours if r["fp"] in v93]
        print(f"   命中 CT_TABLE            : {len(hit_ct)}/{len(ours)}")
        print(f"   命中 _V93_ROUTE_BY_RIVAL : {len(hit_v93)}/{len(ours)}")
        fps = collections.Counter(r["fp"] for r in ours)
        print(f"   实际出现的指纹 (top 6):")
        for fp, n in fps.most_common(6):
            tag = ""
            if fp in ct:
                tag += " [CT]"
            if fp in v93:
                tag += " [V93]"
            print(f"      {fp}  x{n}{tag}")
        print()


if __name__ == "__main__":
    main()
