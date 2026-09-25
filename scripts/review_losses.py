"""Build a review dashboard for a submission's LADDER games.

Why this exists. Local simulation can only show us opponents we already have,
and our panel is saturated: 27 local opponents, of which exactly one is a peer.
The ladder is the only source of opponents that actually beat us, and our losses
there are hairline (median |margin| a few hundred dollars), so reading them one
by one is the only way to see what is still missing.

What it produces. One HTML page with three parts:
  * a summary: how many games, win rate, and the margin distribution;
  * an index: every game with its episode id, opponent, result and margin,
    each linking to that game's panels;
  * per-game panels (from field_ledger): cash, labour, tiles, cash flow, order
    mix, order-stream composition, closing book.

Seat handling. Every panel assumes seat 0 is us, but our seat varies game to
game on the ladder. Each game is normalised so seat 0 IS us; without that, half
the games would label the opponent as us and every panel would read backwards.

Cost. A replay is ~33MB and takes 3-4s. Only `--scan` are fetched, the extracted
series are cached as a few-hundred-KB summary, and the raw JSON is deleted after
reading, so a re-run or a wider scan resumes instead of re-downloading.

Usage:
  .venv/Scripts/python scripts/review_losses.py --ref 56539741 --scan 24 --keep 0
  .venv/Scripts/python scripts/review_losses.py --ref 56539741 --wins-too
  # local mode, no network -- any agents, any seeds:
  .venv/Scripts/python scripts/review_losses.py --a experiments/v44/adv6.py \
      --b opponents/tetsutani_cha22/main.py --seeds 1000-1049 --keep 3
"""
import argparse
import collections
import glob
import json
import os
import statistics
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
    eps = json_from(kaggle("competitions", "episodes", str(ref), "--format", "json"))
    # Newest first: the most recent games reflect the agent as submitted.
    eps.sort(key=lambda e: e.get("createTime") or "", reverse=True)
    return [int(e["id"]) for e in eps[:scan]], len(eps)


def summary_path(eid):
    return os.path.join(CACHE, f"ep-{eid}-summary.json")


def fetch_replay(eid):
    os.makedirs(CACHE, exist_ok=True)
    hits = glob.glob(os.path.join(CACHE, f"episode-{eid}-replay.json"))
    if hits:
        return hits[0]
    kaggle("competitions", "replay", str(eid), "-p", CACHE, "-q")
    hits = glob.glob(os.path.join(CACHE, f"episode-{eid}-replay.json"))
    return hits[0] if hits else None


def load_replay(path, eid):
    """Extract the series, cache a small summary, drop the 33MB raw replay."""
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


def swap_seats(steps):
    """Put us in seat 0 (see the module docstring: every panel assumes it)."""
    out = []
    for r in steps:
        n = {"t": r.get("t")}
        for k, v in r.items():
            if k == "t":
                continue
            n[1 - int(k)] = v
        out.append(n)
    return out


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


def parse_seeds(spec):
    if "-" in spec:
        a, b = spec.split("-")
        return list(range(int(a), int(b) + 1))
    return [int(x) for x in spec.split(",")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default=None, help="提交 ref（天梯模式）")
    ap.add_argument("--team", default=None, help="我们队名；默认自动推断")
    ap.add_argument("--scan", type=int, default=24, help="抓多少个回放")
    ap.add_argument("--keep", type=int, default=6,
                    help="保留最惨的几局；0 = 全部败局")
    ap.add_argument("--wins-too", action="store_true", help="胜局也一并渲染")
    ap.add_argument("--a", default=None, help="本地模式：我们的 agent")
    ap.add_argument("--b", default=None, help="本地模式：对手")
    ap.add_argument("--seeds", default="")
    ap.add_argument("--out", default="results/ledger/ladder_review.html")
    args = ap.parse_args()

    try:  # this console is GBK; opponent names are arbitrary Unicode
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass

    if not args.ref and not (args.a and args.b):
        sys.exit("要么给 --ref（天梯），要么给 --a 和 --b（本地）")

    if args.ref:
        ids, total = episode_ids(args.ref, args.scan)
        print(f"提交 {args.ref}: 共 {total} 局，抓取最近 {len(ids)} 局")
        games = []
        for n, eid in enumerate(ids, 1):
            sp = summary_path(eid)
            if os.path.exists(sp):
                g = json.load(open(sp, encoding="utf-8"))
                g["steps"] = FL.denormalise(g["steps"])
                games.append(g)
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
            print(f"无法唯一确定队名（每局都出现的名字有 {everyone}）；请用 --team 指定")
            team = args.team or games[0]["teams"][0]
        print(f"我们的队名判定为：{team}")
    else:
        a = args.a if os.path.isabs(args.a) else os.path.join(ROOT, args.a)
        b = args.b if os.path.isabs(args.b) else os.path.join(ROOT, args.b)
        games, names = local_games(a, b, parse_seeds(args.seeds))
        team = names[0]

    mirrors = []
    for g in games:
        seats = [i for i, t in enumerate(g["teams"]) if t == team]
        if len(seats) == 2:
            mirrors.append(g)
            seat = 0
        else:
            seat = seats[0] if seats else 0
        mine, theirs = g["rewards"][seat], g["rewards"][1 - seat]
        g["margin"] = mine - theirs
        g["opp_name"] = g["teams"][1 - seat]
        if seat == 1:
            g["steps"] = swap_seats(g["steps"])
            g["rewards"] = [theirs, mine]
        g["our_seat"] = 0

    wins = [g for g in games if g["margin"] > 0]
    losses = [g for g in games if g["margin"] < 0]
    ties = [g for g in games if g["margin"] == 0]
    print(f"扫到 {len(games)} 局：{len(wins)} 胜 / {len(losses)} 负 / {len(ties)} 平"
          + (f"（{len(mirrors)} 局镜像）" if mirrors else ""))
    print(f"  {'episode':>10} {'我们':>10} {'对手':>10} {'差距':>10}  对手名")
    for g in sorted(games, key=lambda x: x["margin"]):
        print(f"  {str(g['episode']):>10} "
              f"{g['rewards'][0]:>10,.0f} {g['rewards'][1]:>10,.0f} "
              f"{g['margin']:>+10,.0f}  {g['opp_name']}")

    sel = sorted(losses, key=lambda x: x["margin"])
    if args.keep > 0:
        sel = sel[:args.keep]
    if args.wins_too:
        sel = sel + sorted(wins, key=lambda x: -x["margin"])
    if not sel:
        print("没有可复盘的对局（没有败局？用 --wins-too 看胜局）。")
        return

    payload = [{"steps": g["steps"], "seed": g["episode"] or g["seed"],
                "final": g["rewards"], "ladder": bool(args.ref),
                "ref": args.ref or "", "opp_name": g["opp_name"],
                "margin": g["margin"]} for g in sel]

    absm = sorted(abs(g["margin"]) for g in games)
    med = statistics.median(absm)
    close = sum(1 for m in absm if m < 600)
    stats = {
        "n": len(games), "w": len(wins), "l": len(losses), "t": len(ties),
        "rate": 100.0 * len(wins) / max(1, len(games)),
        "median": med, "closest": absm[0], "worst": absm[-1],
        "close_pct": 100.0 * close / max(1, len(absm)),
        "opponents": len(set(g["opp_name"] for g in games)),
        "mirrors": len(mirrors),
    }
    if args.ref:
        blurb = (f"<b>真实天梯对局</b>，来自提交 <b>ref {args.ref}</b>：按最近时间抓取 "
                 f"<b>{stats['n']}</b> 局（对手 {stats['opponents']} 个不同玩家），"
                 f"{stats['w']} 胜 / {stats['l']} 负 / {stats['t']} 平。本页渲染 "
                 f"<b>{len(sel)}</b> 局（{'全部败局' if args.keep <= 0 else '最惨的 %d 局' % len(sel)}）。")
    else:
        blurb = (f"<b>本地模拟</b>（不是天梯）：{stats['n']} 局，"
                 f"{stats['w']} 胜 / {stats['l']} 负。种子固定，用于机制对比。")
    blurb += ("我们的座位已归一到 seat 0 —— <b>左列永远是我们</b>。"
              "索引表里点一行就跳到那一局的全部面板。")

    out = args.out if os.path.isabs(args.out) else os.path.join(ROOT, args.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write(
        FL.build_html(payload, [f"我们（{team}）", "对手"], blurb=blurb, stats=stats))
    print(f"已写入 {out}  ({os.path.getsize(out):,} bytes) —— {len(sel)} 局")


if __name__ == "__main__":
    main()
