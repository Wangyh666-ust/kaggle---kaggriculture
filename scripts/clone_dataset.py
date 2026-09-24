"""Build a compact per-game dataset from every ladder replay we have.

Why a separate script: each replay is ~30 MB JSON and there are ~500 of them.
Every downstream question (seat, shop pair, margin, order-book timing) needs the
same extraction, so do it once and cache as a small pickle-parquet-ish JSONL.

Classification of the opponent is by its OWN opening market signature (first 3
steps of its action stream), exactly as scripts/mirror_share.py does.

Self-play episodes (TeamNames[0] == TeamNames[1]) are Kaggle submission
VALIDATION runs, not ladder games: they are excluded, and also reported
separately because they are NOT always $0.

Usage:
  .venv/Scripts/python scripts/clone_dataset.py            # build/refresh cache
  .venv/Scripts/python scripts/clone_dataset.py --force
"""
import argparse
import glob
import hashlib
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OURS = "ReD_MooN_rise"
CACHE = os.path.join(ROOT, "reverse", "clone_games.jsonl")
DIRS = ["replays_v21", "replays_v23", "replays_v23r", "replays_v24", "replays_v24r",
        "replays_v25", "replays_v27", "replays_v28", "replays_v25", "replays_ladder",
        "replays_ladder_ops"]


def sig(act):
    mk = act.get("market") if isinstance(act, dict) else None
    return json.dumps(mk, separators=(",", ":")) if mk is not None else "-"


def count_herd(farm):
    n = 0
    for row in farm["tiles"]:
        for t in row:
            if isinstance(t, dict) and "animal" in t:
                n += 1
    return n


def snapshot(d, seat, idx):
    try:
        o = d["steps"][idx][seat]["observation"]
        f = o["farms"][seat]
        # NOTE: seat 1's observation omits the "step" key in every ladder replay
        # we have (serialisation quirk). Never index it directly.
        return {"day": o["day"], "hour": o["hour"], "step": o.get("step"),
                "money": f["money"], "herd": count_herd(f),
                "shops": list(o["town"].get("unlocked_shops", [])),
                "hands": f.get("hands"), "prices": dict(o["market"]["prices"]),
                "inv": dict(o["market"]["inventory"])}
    except Exception:  # noqa: BLE001
        return None


def extract(f, team):
    d = json.load(open(f, encoding="utf-8"))
    names = list(d["info"]["TeamNames"])
    if team not in names:
        return None
    selfplay = names[0] == names[1]
    us = names.index(team)
    opp = 1 - us
    steps = d["steps"]
    n = len(steps)

    # our own opening signature (from our seat) and the opponent's
    try:
        our_open = sig(steps[2][us].get("action"))
        opp_open = sig(steps[2][opp].get("action"))
    except Exception:  # noqa: BLE001
        our_open = opp_open = None

    # market order stream of each side (every step, non-empty only)
    orders = {0: [], 1: []}
    for i in range(n):
        for s in (0, 1):
            try:
                a = steps[i][s].get("action") or {}
            except Exception:  # noqa: BLE001
                continue
            mk = a.get("market")
            if mk:
                orders[s].append([i] + [list(x) if isinstance(x, list) else x for x in mk])

    # day-3 herd (the early-death signature)
    def d3(seat):
        for st in steps:
            o = st[seat]["observation"]
            if o.get("day") == 3 and o.get("hour") == 23:
                return count_herd(o["farms"][seat])
        return None

    # per-step action digest of each side: lets us locate the FIRST step at which
    # the two sides stop doing the same thing, without storing the full tape.
    def digests(seat):
        out = []
        for i in range(n):
            try:
                a = steps[i][seat].get("action")
            except Exception:  # noqa: BLE001
                a = None
            out.append(hashlib.md5(
                json.dumps(a, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()[:8] if a is not None else "--------")
        return out

    # shop pair router key at step 144 and full unlock timeline
    shops_tl = {}
    for i in range(n):
        try:
            sh = tuple(steps[i][us]["observation"]["town"].get("unlocked_shops", []))
        except Exception:  # noqa: BLE001
            continue
        if sh not in shops_tl:
            shops_tl[str(sh)] = i

    rec = {
        "file": os.path.relpath(f, ROOT).replace("\\", "/"),
        "episode": d["info"].get("EpisodeId"),
        "seed": d["info"].get("seed"),
        "selfplay": selfplay,
        "n_steps": n,
        "our_seat": us,
        "opp": names[opp],
        "margin": d["rewards"][us] - d["rewards"][opp],
        "our": d["rewards"][us],
        "theirs": d["rewards"][opp],
        "our_status": d["statuses"][us],
        "opp_status": d["statuses"][opp],
        "our_open": our_open,
        "opp_open": opp_open,
        "d3_herd": d3(us),
        "opp_d3_herd": d3(opp),
        "snap": [snapshot(d, us, min(i, n - 1)) for i in (2, 143, 359, n - 1)],
        "opp_snap": [snapshot(d, opp, min(i, n - 1)) for i in (2, 143, 359, n - 1)],
        "orders_us": orders[us],
        "orders_opp": orders[opp],
        "shops_tl": shops_tl,
    }
    if not selfplay:
        h_us = digests(us)
        h_opp = digests(opp)
        rec["h_us"] = h_us
        rec["h_opp"] = h_opp
        rec["n_diff_steps"] = sum(1 for a, b in zip(h_us, h_opp) if a != b)
        rec["first_diff"] = next((i for i, (a, b) in enumerate(zip(h_us, h_opp))
                                  if a != b), None)
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--team", default=OURS)
    args = ap.parse_args()
    if os.path.exists(CACHE) and not args.force:
        print(f"cache exists: {CACHE} ({os.path.getsize(CACHE)/1e6:.1f} MB). --force to rebuild")
        return
    files = []
    for d in DIRS:
        files += sorted(glob.glob(os.path.join(ROOT, d, "episode-*-replay.json")))
    files = sorted(set(files))
    print(f"{len(files)} replay files")
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    ok = bad = 0
    with open(CACHE, "w", encoding="utf-8") as out:
        for i, f in enumerate(files, 1):
            try:
                r = extract(f, args.team)
            except Exception as exc:  # noqa: BLE001
                bad += 1
                print(f"  FAIL {os.path.basename(f)}: {exc}")
                continue
            if r is None:
                bad += 1
                continue
            out.write(json.dumps(r) + "\n")
            ok += 1
            if i % 25 == 0:
                print(f"  {i}/{len(files)}", flush=True)
    print(f"wrote {ok} records ({bad} skipped) -> {CACHE}")


if __name__ == "__main__":
    main()
