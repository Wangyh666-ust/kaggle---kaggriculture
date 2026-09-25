"""Download a submission's LOSING ladder games and render them as a ledger.

Why this exists. Local simulation can only show us opponents we already have,
and our panel is saturated (27 local opponents, one peer). The ladder is the only
source of opponents that actually beat us -- so reviewing real losses is the only
way to see what we are still missing.

How our seat is identified. `kaggle competitions episodes` returns no scores, so
each replay has to be fetched and read. Replays do carry
`info.TeamNames`, e.g. ['Yaojinming', 'ReD_MooN_rise'], which names both sides.
Our own name is whichever one appears in EVERY episode of this submission (the
opponent varies by game); `--team` overrides that. A mirror game against another
copy of ourselves shows our name twice -- those are reported as mirrors and seat
0 is taken as ours.

Cost. A replay is ~33MB and takes 3-4s. Only `--scan` of them are fetched, only
the `--keep` worst losses are kept, and the raw JSON is deleted after its series
are extracted (the ledger needs the extracted series, not the file).

Usage:
  .venv/Scripts/python scripts/review_losses.py --ref 56539741 --scan 12 --keep 3
  .venv/Scripts/python scripts/review_losses.py --ref 56539741 --team ReD_MooN_rise
  # local mode, no network -- pick any agents and seeds:
  .venv/Scripts/python scripts/review_losses.py --a experiments/v41/cxd.py \
      --b opponents/tetsutani_cha22/main.py --seeds 1000-1049 --keep 3
"""
import argparse
import collections
import glob
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
PY = os.path.join(ROOT, ".venv", "Scripts", "python.exe")
import field_ledger as FL  # noqa: E402

CACHE = os.path.join(ROOT, "tmp_replays")


def kaggle(*args, timeout=300):
    r = subprocess.run([PY, "-m", "kaggle", *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout)
    return (r.stdout or "") + (r.stderr or "")


def json_from(out):
    """Kaggle mixes progress bars into --format json; take the outer array."""
    i, j = out.find("["), out.rfind("]")
    if i < 0 or j <= i:
        return []
    return json.loads(out[i:j + 1])


def episode_ids(ref, scan):
    out = kaggle("competitions", "episodes", str(ref), "--format", "json")
    eps = json_from(out)
    # Newest first: the most recent games reflect the agent as submitted.
    eps.sort(key=lambda e: e.get("createTime") or "", reverse=True)
    return [int(e["id"]) for e in eps[:scan]], len(eps)


def fetch_replay(eid):
    os.makedirs(CACHE, exist_ok=True)
    hits = glob.glob(os.path.join(CACHE, f"episode-{eid}-replay.json"))
    if hits:
        return hits[0]
    kaggle("competitions", "replay", str(eid), "-p", CACHE, "-q")
    hits = glob.glob(os.path.join(CACHE, f"episode-{eid}-replay.json"))
    return hits[0] if hits else None


def summary_path(eid):
    return os.path.join(CACHE, f"ep-{eid}-summary.json")


def load_replay(path, eid):
    """Extract the series, cache a small summary, drop the 33MB raw replay.

    The ledger needs the extracted series, not the file, and a summary is a few
    hundred KB against 33MB -- so a re-run or a wider --scan resumes instead of
    downloading everything again.
    """
    d = json.load(open(path, encoding="utf-8"))
    info = d.get("info") or {}
    steps = FL.collect(d["steps"])
    rewards = [float(x) for x in d.get("rewards", [])]
    if len(rewards) < 2:
        rewards = [float(d["steps"][-1][s].get("reward") or 0) for s in (0, 1)]
    try:
        os.remove(path)
    except OSError:
        pass
    g = {"steps": steps, "teams": list(info.get("TeamNames") or ["?", "?"]),
         "rewards": rewards, "episode": info.get("EpisodeId"), "seed": info.get("seed")}
    try:
        json.dump(g, open(summary_path(eid), "w", encoding="utf-8"))
    except OSError:
        pass
    return g


def local_games(a_path, b_path, seeds):
    import importlib.util
    from kaggle_environments import make

    def load(p, n):
        s = importlib.util.spec_from_file_location(n, p)
        m = importlib.util.module_from_spec(s)
        s.loader.exec_module(m)
        cbs = [v for k, v in vars(m).items() if callable(v) and not k.startswith("__")]
        return cbs[-1]

    A, B = load(a_path, "A"), load(b_path, "B")
    names = [os.path.basename(os.path.dirname(a_path)) or "ours",
             os.path.basename(os.path.dirname(b_path))]
    out = []
    for seed in seeds:
        env = make("kaggriculture", configuration={"seed": seed}, debug=True)
        env.run([A, B])
        rew = [float(env.steps[-1][s].reward) for s in (0, 1)]
        out.append({"steps": FL.collect(env.steps), "teams": names, "rewards": rew,
                    "episode": None, "seed": seed})
    return out, names


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default=None, help="提交的 ref（天梯模式）")
    ap.add_argument("--team", default=None, help="我们队名；默认自动推断")
    ap.add_argument("--scan", type=int, default=12, help="抓多少个回放来找败局")
    ap.add_argument("--keep", type=int, default=3, help="保留最惨的几局")
    ap.add_argument("--a", default=None, help="本地模式：我们的 agent")
    ap.add_argument("--b", default=None, help="本地模式：对手")
    ap.add_argument("--seeds", default="")
    ap.add_argument("--out", default="results/ledger/losses.html")
    args = ap.parse_args()

    try:  # this console is GBK; opponent names are arbitrary Unicode
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass

    if not args.ref and not (args.a and args.b):
        sys.exit("要么给 --ref（天梯），要么给 --a 和 --b（本地）")

    if args.ref:
        ids, total = episode_ids(args.ref, args.scan)
        print(f"提交 {args.ref}: 共 {total} 局，抓取最近 {len(ids)} 局来找败局\n")
        games = []
        for n, eid in enumerate(ids, 1):
            sp = summary_path(eid)
            if os.path.exists(sp):
                games.append(json.load(open(sp, encoding="utf-8")))
                g = games[-1]
                print(f"  [{n}/{len(ids)}] ep {g['episode']}  (cached)")
                continue
            p = fetch_replay(eid)
            if not p:
                print(f"  [{n}/{len(ids)}] {eid} 抓取失败（限流？）")
                continue
            g = load_replay(p, eid)
            games.append(g)
            print(f"  [{n}/{len(ids)}] ep {g['episode']}  "
                  f"{g['teams'][0]} {g['rewards'][0]:,.0f} : "
                  f"{g['teams'][1]} {g['rewards'][1]:,.0f}")
        if not games:
            sys.exit("没有抓到任何回放")

        # Ours is the name present in every episode; opponents differ per game.
        counts = collections.Counter(t for g in games for t in g["teams"])
        everyone = [t for t, c in counts.items() if c == len(games)]
        team = args.team or (everyone[0] if len(everyone) == 1 else None)
        if team is None:
            print(f"\n⚠️ 无法唯一确定队名（每局都出现的名字有 {everyone}）；请用 --team 指定")
            team = args.team or games[0]["teams"][0]
        print(f"\n我们的队名判定为：{team}")
    else:
        a = args.a if os.path.isabs(args.a) else os.path.join(ROOT, args.a)
        b = args.b if os.path.isabs(args.b) else os.path.join(ROOT, args.b)
        seeds = ([int(x) for x in args.seeds.split(",")] if "," in args.seeds else
                 list(range(int(args.seeds.split("-")[0]), int(args.seeds.split("-")[1]) + 1)))
        games, names = local_games(a, b, seeds)
        team = names[0]

    losses, wins, mirrors = [], [], []
    for g in games:
        seats = [i for i, t in enumerate(g["teams"]) if t == team]
        if len(seats) == 2:
            mirrors.append(g)
            seat = 0
        else:
            seat = seats[0] if seats else 0
        mine, theirs = g["rewards"][seat], g["rewards"][1 - seat]
        g.update(our_seat=seat, margin=mine - theirs)
        (losses if mine < theirs else wins).append(g)

    print(f"\n扫到 {len(games)} 局：{len(wins)} 胜 / {len(losses)} 负"
          + (f" / {len(mirrors)} 镜像" if mirrors else ""))
    print(f"  {'episode':>10} {'seed':>12} {'我们':>10} {'对手':>10} {'差距':>10}  对手名")
    for g in sorted(losses, key=lambda x: x["margin"])[:max(args.keep, 5)]:
        s = g["our_seat"]
        print(f"  {str(g['episode']):>10} {str(g['seed']):>12} "
              f"{g['rewards'][s]:>10,.0f} {g['rewards'][1-s]:>10,.0f} "
              f"{g['margin']:>+10,.0f}  {g['teams'][1-s]}")

    if not losses:
        print("\n没有败局可复盘。")
        return
    keep = sorted(losses, key=lambda x: x["margin"])[:args.keep]
    names = [f"我们（{team}）", "对手"]
    payload = [{"steps": g["steps"], "seed": g["episode"] or g["seed"],
                "final": [g["rewards"][0], g["rewards"][1]]} for g in keep]
    out = args.out if os.path.isabs(args.out) else os.path.join(ROOT, args.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write(FL.build_html(payload, names))
    print(f"\n已写入 {out}  ({os.path.getsize(out):,} bytes) —— 含最惨的 {len(keep)} 局")
    # The raw replays were deleted as they were read; the small summaries are
    # kept so a re-run or a wider scan does not re-download them.


if __name__ == "__main__":
    main()
