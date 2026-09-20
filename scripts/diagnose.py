"""Single-episode diagnostic: daily snapshots of our farm's economy."""
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
    opp = sys.argv[2] if len(sys.argv) > 2 else "pass"
    agent_fn = load_agent(os.path.join(ROOT, "main.py"))
    env = make("kaggriculture", configuration={"seed": seed}, debug=False)
    env.run([agent_fn, opp])

    print(f"seed={seed} opp={opp}")
    print(f"{'day':>3} {'money':>9} {'hands':>5} {'animals':>7} {'plants':>6} "
          f"{'shed':>45} {'eggP':>5} {'fertP':>6} {'melonP':>6} {'wheatP':>6}")
    for step_idx in range(3, len(env.steps), 24):
        s = env.steps[step_idx][0]
        obs = s.observation
        farm = obs.farms[0]
        shed = dict(obs.private.shed)
        shed = {k: v for k, v in shed.items() if v}
        animals = 0
        plants = 0
        for row in farm.tiles:
            for t in row:
                if isinstance(t, dict):
                    if "animal" in t:
                        animals += 1
                    elif t.get("kind") == "PLANT":
                        plants += 1
        pr = obs.market.prices
        print(f"{obs.day:>3} {farm.money:>9.0f} {len(farm.hands):>5} "
              f"{animals:>7} {plants:>6} {str(shed):>45} "
              f"{pr['EGG']:>5} {pr['FERTILIZER']:>6} {pr['MELON']:>6} {pr['WHEAT']:>6}")
    final = env.steps[-1]
    print("final:", [f"${s.reward:.0f}" for s in final])


if __name__ == "__main__":
    main()
