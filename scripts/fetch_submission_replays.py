"""Download every episode replay of one of our submissions, then report the record.

Why: a converged Elo implies a ~50% win rate at that rating. If the replays show
something very different, the displayed score is not tracking how the episodes
actually went, and that changes what "improving the agent" means.

Usage:
  .venv/Scripts/python scripts/fetch_submission_replays.py --ref 56470877
  .venv/Scripts/python scripts/fetch_submission_replays.py --ref 56470877 --limit 25
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PY = os.path.join(ROOT, ".venv", "Scripts", "python.exe")
PACE = 2.0
THROTTLE_WAIT = 90
THROTTLE_TRIES = 8
OUR_TEAM = "ReD_MooN_rise"


def kaggle(*args, timeout=240):
    cmd = [PY, "-m", "kaggle", *args]
    for attempt in range(THROTTLE_TRIES):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=timeout)
        except subprocess.TimeoutExpired:
            return ""
        out = (r.stdout or "") + "\n" + (r.stderr or "")
        # Match the HTTP error signature, NOT the bare digits "429": episode ids are
        # ~9-digit numbers and 112142921 contains "429", so a substring test on "429"
        # misreads a perfectly good download as a throttle and sleeps for minutes.
        if "Client Error: Too Many Requests" not in out and "429 Client Error" not in out:
            return out
        wait = THROTTLE_WAIT * (attempt + 1)
        print(f"    429; waiting {wait}s ({attempt+1}/{THROTTLE_TRIES})", flush=True)
        time.sleep(wait)
    return out


def episode_ids(ref):
    out = kaggle("competitions", "episodes", str(ref), "--format", "json")
    i, j = out.find("["), out.rfind("]")
    if i < 0 or j <= i:
        return []
    try:
        return [int(e["id"]) for e in json.loads(out[i:j + 1])]
    except Exception:  # noqa: BLE001
        return [int(m) for m in re.findall(r'"id":\s*(\d+)', out)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True)
    ap.add_argument("--limit", type=int, default=0, help="0 = all")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    out_dir = os.path.join(ROOT, args.out or f"replays_v{args.ref}")
    os.makedirs(out_dir, exist_ok=True)
    ids = episode_ids(args.ref)
    if not ids:
        print("no episodes found (throttled?)")
        return
    if args.limit:
        ids = ids[:args.limit]
    print(f"submission {args.ref}: {len(ids)} episodes -> {os.path.relpath(out_dir, ROOT)}")

    # keep the project's existing convention: results/ep_<ref>.txt lists the episodes
    with open(os.path.join(ROOT, "results", f"ep_{args.ref}.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(str(i) for i in sorted(ids)) + "\n")

    got = 0
    for n, eid in enumerate(ids, 1):
        path = os.path.join(out_dir, f"episode-{eid}-replay.json")
        if not os.path.exists(path):
            kaggle("competitions", "replay", str(eid), "-p", out_dir, "-q")
            time.sleep(PACE)
        if os.path.exists(path):
            got += 1
        if n % 10 == 0:
            print(f"    {n}/{len(ids)} ({got} on disk)", flush=True)
    print(f"downloaded/available: {got}/{len(ids)}")


if __name__ == "__main__":
    main()
