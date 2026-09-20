"""Cash-flow tracer: log our market orders + money delta per day."""
import importlib.util
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from kaggle_environments import make  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def load_agent(path):
    spec = importlib.util.spec_from_file_location("candidate_agent", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.agent


def main():
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    agent_fn = load_agent(os.path.join(ROOT, "main.py"))

    day_orders = []
    last_money = [None]
    daily = []  # (day, start_money, orders_summary)

    def spy(obs):
        act = agent_fn(obs)
        day = obs["day"]
        money = obs["farms"][obs["player"]]["money"]
        if not daily or daily[-1][0] != day:
            daily.append([day, money, [], []])
        for o in act.get("market", []):
            daily[-1][2].append(o)
        for u in [act.get("farmer")] + list(act.get("hands", [])):
            if u:
                daily[-1][3].append(u[0] if isinstance(u, list) else u)
        return act

    env = make("kaggriculture", configuration={"seed": seed}, debug=False)
    env.run([spy, "pass"])
    final = env.steps[-1]
    print("final:", [f"${s.reward:.0f}" for s in final])
    for day, money, orders, uops in daily:
        # summarize orders
        from collections import Counter
        c = Counter()
        detail = []
        for o in orders:
            op = o[0]
            if op == "SELL":
                c[f"SELL {o[1]}"] += o[2]
            elif op == "HIRE":
                c["HIRE"] += 1
            elif op in ("BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL"):
                c[f"{op} {o[1]}"] += o[2]
                detail.append(f"{op} {o[1]} x{o[2]}")
            else:
                c[op] += 1
        uc = Counter(uops)
        print(f"day {day:2d} start=${money:8.0f}  " +
              ", ".join(f"{k}x{v}" for k, v in sorted(c.items())) +
              "  || units: " + ", ".join(f"{k}x{v}" for k, v in sorted(uc.items())))


if __name__ == "__main__":
    main()
