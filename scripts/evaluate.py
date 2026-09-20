"""Local evaluation harness for the Kaggriculture agent.

Usage (Git Bash, from repo root):
    ./.venv/Scripts/python scripts/evaluate.py --opp starter --episodes 6
    ./.venv/Scripts/python scripts/evaluate.py --opp self --episodes 4
    ./.venv/Scripts/python scripts/evaluate.py --opp random,pass,starter --episodes 4

Measures win rate, final money, and per-turn agent latency (must stay << 1s).
Results are appended to results/eval_log.json.
"""
import argparse
import importlib.util
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from kaggle_environments import make  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MAIN_PY = os.path.join(ROOT, "main.py")
RESULTS = os.path.join(ROOT, "results")


def load_agent(path):
    spec = importlib.util.spec_from_file_location("candidate_agent", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.agent


class Timer:
    def __init__(self):
        self.max_t = 0.0
        self.total = 0.0
        self.calls = 0

    def wrap(self, fn):
        def wrapped(obs, config=None):
            t0 = time.perf_counter()
            out = fn(obs)
            dt = time.perf_counter() - t0
            self.max_t = max(self.max_t, dt)
            self.total += dt
            self.calls += 1
            return out
        return wrapped

    def summary(self):
        avg = self.total / max(1, self.calls)
        return {"calls": self.calls, "avg_ms": round(avg * 1000, 2),
                "max_ms": round(self.max_t * 1000, 2)}


def run_episode(our_agent, opp, seed, our_seat):
    env = make("kaggriculture", configuration={"seed": seed}, debug=False)
    if our_seat == 0:
        env.run([our_agent, opp])
    else:
        env.run([opp, our_agent])
    final = env.steps[-1]
    rewards = [s.reward for s in final]
    statuses = [s.status for s in final]
    our_reward = rewards[our_seat]
    opp_reward = rewards[1 - our_seat]
    return {
        "seed": seed, "our_seat": our_seat,
        "our_money": our_reward, "opp_money": opp_reward,
        "win": our_reward > opp_reward, "tie": our_reward == opp_reward,
        "status": statuses[our_seat],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--opp", default="starter",
                    help="comma list: starter|random|pass|self|path-to-py")
    ap.add_argument("--episodes", type=int, default=6)
    ap.add_argument("--seed0", type=int, default=1000)
    ap.add_argument("--agent", default=MAIN_PY)
    args = ap.parse_args()

    agent_fn = load_agent(args.agent)
    timer = Timer()
    timed_agent = timer.wrap(agent_fn)

    all_results = []
    for opp_name in args.opp.split(","):
        opp_name = opp_name.strip()
        if opp_name == "self":
            opp = load_agent(args.agent)  # fresh copy, separate module state
        elif opp_name.endswith(".py"):
            opp = opp_name
        else:
            opp = opp_name  # built-in name
        for ep in range(args.episodes):
            seat = ep % 2
            seed = args.seed0 + ep
            t0 = time.time()
            r = run_episode(timed_agent, opp, seed, seat)
            r["opp"] = opp_name
            r["wall_s"] = round(time.time() - t0, 1)
            all_results.append(r)
            print(f"[{opp_name}] ep{ep} seed={seed} seat={seat} "
                  f"us=${r['our_money']:.0f} them=${r['opp_money']:.0f} "
                  f"{'WIN' if r['win'] else ('TIE' if r['tie'] else 'LOSS')} "
                  f"status={r['status']} ({r['wall_s']}s)")

    print("\n==== summary ====")
    by_opp = {}
    for r in all_results:
        by_opp.setdefault(r["opp"], []).append(r)
    for opp, rs in by_opp.items():
        wins = sum(1 for r in rs if r["win"])
        avg_us = sum(r["our_money"] for r in rs) / len(rs)
        avg_them = sum(r["opp_money"] for r in rs) / len(rs)
        print(f"vs {opp:10s}: {wins}/{len(rs)} wins | "
              f"avg us=${avg_us:.0f} them=${avg_them:.0f}")
    print("latency:", timer.summary())

    os.makedirs(RESULTS, exist_ok=True)
    log_path = os.path.join(RESULTS, "eval_log.json")
    log = []
    if os.path.exists(log_path):
        with open(log_path) as f:
            log = json.load(f)
    log.append({"ts": time.strftime("%Y-%m-%d %H:%M:%S"),
                "agent": os.path.basename(args.agent),
                "results": all_results, "latency": timer.summary()})
    with open(log_path, "w") as f:
        json.dump(log, f, indent=1)
    print("logged ->", log_path)


if __name__ == "__main__":
    main()
