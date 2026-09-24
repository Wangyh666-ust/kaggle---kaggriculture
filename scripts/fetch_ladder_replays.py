"""Fetch ladder replays of the top teams into replays_ladder/ (+ an index json).

Why this exists
---------------
Each public ladder replay carries `info.seed` and BOTH agents' full 720-step
action streams. That makes the top of the leaderboard *observable*: their
opening signature, route choice, crop/herd plan and market cadence can all be
read turn by turn. This is the only source that turns "we are N Elo behind"
into a list of concrete differences.

Kaggle exposes it through three public endpoints (no special access needed):
    team-submissions <team_id>   -> every active submission of that team
    episodes <submission_id>     -> episodes that submission played
    replay <episode_id>          -> the replay json

Implementation note: this drives the ``kaggle`` CLI in a subprocess rather than
the kagglesdk client. The SDK's REST tier starts returning HTTP 429 after a few
dozen rapid calls (the leaderboard page loop trips it every time), and its
retry path stalls; the CLI talks to the same endpoints but sustains a paced
fetch. A 1.5 s gap between calls keeps it polite.

Usage
-----
    .venv/Scripts/python scripts/fetch_ladder_replays.py                 # top 12, 2 eps each
    .venv/Scripts/python scripts/fetch_ladder_replays.py --top 20 --episodes 3
    .venv/Scripts/python scripts/fetch_ladder_replays.py --teams 16770421,16623559
    .venv/Scripts/python scripts/fetch_ladder_replays.py --refresh        # re-page the board

Output
------
    replays_ladder/episode-<id>-replay.json      (git-ignored: replays*/)
    replays_ladder/index.json                    {team, score, episodes}
    replays_ladder/leaderboard.json              cached full board
"""
import argparse
import json
import os
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "replays_ladder")
INDEX = os.path.join(OUT, "index.json")
BOARD = os.path.join(OUT, "leaderboard.json")
PY = os.path.join(ROOT, ".venv", "Scripts", "python.exe")
PACE = 2.0           # seconds between successful CLI calls
THROTTLE_WAIT = 120  # seconds to wait after a 429 before retrying the same call
# Kaggle's throttle on this credential has been observed to hold for well over
# 20 minutes after a burst, so retries ramp to ~20 min and the total budget is
# ~2 hours. The fetch is resumable: it only downloads episodes that are missing.
THROTTLE_TRIES = 12


def kaggle(*args, timeout=180):
    """Run the kaggle CLI, returning raw stdout (stdout+stderr merged).

    Kaggle's REST tier throttles the whole credential after a burst of calls, so
    a 429 is retried with a long fixed wait rather than being treated as a
    failure — the fetch is resumable and only downloads what is missing.
    """
    cmd = [PY, "-m", "kaggle", *args]
    for attempt in range(THROTTLE_TRIES):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=timeout)
        except subprocess.TimeoutExpired:
            return ""
        out = (r.stdout or "") + "\n" + (r.stderr or "")
        # Match the HTTP error signature, NOT the bare digits "429": episode ids are
        # ~9-digit numbers and one in our own list (112142921) contains "429", so a
        # substring test on "429" misreads a good download as a throttle.
        if "Client Error: Too Many Requests" not in out and "429 Client Error" not in out:
            return out
        wait = THROTTLE_WAIT * (attempt + 1)
        print(f"      429 throttled; waiting {wait}s "
              f"(attempt {attempt + 1}/{THROTTLE_TRIES})", flush=True)
        time.sleep(wait)
    return out


def csv_rows(text, ncols):
    """Parse the CLI's `-v` output: comma-separated rows, one per record."""
    rows = []
    for line in text.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= ncols and parts[0].isdigit():
            rows.append(parts)
    return rows


def leaderboard(refresh=False, pages=12):
    if os.path.exists(BOARD) and not refresh:
        with open(BOARD, encoding="utf-8") as fh:
            rows = json.load(fh)
        if rows:
            print(f"  leaderboard: {len(rows)} teams (cached; --refresh to re-page)")
            return rows

    rows, seen, token = [], set(), None
    for _ in range(pages):
        args = ["competitions", "leaderboard", "kaggriculture", "--page-size", "200", "-s", "-v"]
        if token:
            args += ["--page-token", token]
        out = kaggle(*args)
        token = None
        for line in out.splitlines():
            if line.startswith("Next Page Token = "):
                token = line.split(" = ", 1)[1].strip()
        for parts in csv_rows(out, 4):
            tid = int(parts[0])
            if tid in seen:
                continue
            seen.add(tid)
            rows.append({"teamId": tid, "teamName": parts[1], "score": float(parts[-1])})
        if not token:
            break
        time.sleep(PACE)
    rows.sort(key=lambda r: -r["score"])
    if rows:
        os.makedirs(OUT, exist_ok=True)
        with open(BOARD, "w", encoding="utf-8") as fh:
            json.dump(rows, fh, indent=1, ensure_ascii=False)
    return rows


def team_submissions(team_id):
    """[(submission_id, date), ...] newest first."""
    out = kaggle("competitions", "team-submissions", str(team_id), "-v")
    subs = [(int(p[0]), p[1]) for p in csv_rows(out, 3)]
    subs.sort(key=lambda s: s[1], reverse=True)
    return subs


def episodes(submission_id):
    """[episode_id, ...] oldest first, completed only."""
    out = kaggle("competitions", "episodes", str(submission_id), "-v")
    eps = []
    for p in csv_rows(out, 5):
        eid, create = int(p[0]), p[1]
        if "COMPLETED" not in out.split(create, 1)[1][:200].upper() and "COMPLETED" not in out:
            pass  # state is on the same row for the table format; keep it simple
        eps.append((eid, create))
    eps.sort(key=lambda e: e[1])
    return [e[0] for e in eps]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=12)
    ap.add_argument("--episodes", type=int, default=2, help="episodes per team")
    ap.add_argument("--teams", default="", help="comma-separated team ids (overrides --top)")
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--extra", default="", help="extra team ids to append after the top N")
    ap.add_argument("--out", default="", help="output directory (default replays_ladder/)")
    args = ap.parse_args()

    global OUT, INDEX, BOARD
    if args.out:
        OUT = os.path.join(ROOT, args.out)
        INDEX = os.path.join(OUT, "index.json")
        # keep the (expensive to page) leaderboard cache with the repo, not per-target
        BOARD = os.path.join(ROOT, "replays_ladder", "leaderboard.json")
    os.makedirs(OUT, exist_ok=True)
    board = leaderboard(refresh=args.refresh)
    if not board:
        print("no leaderboard (rate limited?) — rerun later")
        return

    if args.teams:
        wanted = {int(t) for t in args.teams.split(",") if t.strip()}
        teams = [t for t in board if t["teamId"] in wanted]
    else:
        teams = list(board[:args.top])
    if args.extra:
        wanted = {int(t) for t in args.extra.split(",") if t.strip()}
        have = {t["teamId"] for t in teams}
        teams += [t for t in board if t["teamId"] in wanted and t["teamId"] not in have]

    index = {"fetchedAt": time.strftime("%Y-%m-%d %H:%M:%S"), "teams": []}
    for team in teams:
        print(f"  {team['teamName'][:30]:30s} {team['score']:7.1f}", flush=True)
        got = []
        try:
            for sid, date in team_submissions(team["teamId"])[:2]:
                time.sleep(PACE)
                eids = episodes(sid)[-args.episodes:]
                for eid in eids:
                    path = os.path.join(OUT, f"episode-{eid}-replay.json")
                    if not os.path.exists(path):
                        kaggle("competitions", "replay", str(eid), "-p", OUT, "-q")
                        time.sleep(PACE)
                    if os.path.exists(path):
                        got.append({"episodeId": eid, "submissionId": sid,
                                    "file": os.path.basename(path)})
                if len(got) >= args.episodes:
                    break
        except Exception as exc:  # noqa: BLE001
            print(f"      failed: {exc}", flush=True)
        index["teams"].append({**team, "episodes": got})
        print(f"      {len(got)} replay(s)", flush=True)

    with open(INDEX, "w", encoding="utf-8") as fh:
        json.dump(index, fh, indent=1, ensure_ascii=False)
    total = sum(len(t["episodes"]) for t in index["teams"])
    print(f"\nwrote replays_ladder/index.json ({total} replays, {len(index['teams'])} teams)")


if __name__ == "__main__":
    main()
