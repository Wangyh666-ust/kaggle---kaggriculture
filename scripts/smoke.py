"""Smoke test: run the candidate against real opponents and fail loudly.

Catches the class of bug where an exception hides behind a short-circuiting
`and` (it only fires on some seeds, so a pass-only run can miss it entirely).
Asserts: episode status DONE for both seats, and no early economic collapse.

Usage: .venv/Scripts/python scripts/smoke.py [main.py] [opponent.py|starter]
"""
import importlib.util
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from kaggle_environments import make  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SEEDS = (1000, 1001, 3000, 5000, 8001, 8003, 8005, 8008, 8009)
MIN_REWARD = 10000      # below this the economy died somewhere


def load_agent(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.agent


def main():
    cand = os.path.join(ROOT, sys.argv[1]) if len(sys.argv) > 1 else os.path.join(ROOT, "main.py")
    opp_arg = sys.argv[2] if len(sys.argv) > 2 else None

    failures = []
    for seed in SEEDS:
        for seat in (0, 1):
            agents = [None, None]
            agents[seat] = load_agent(cand, f"cand{seed}{seat}")
            if opp_arg and opp_arg.endswith(".py"):
                opp = os.path.join(ROOT, opp_arg)
                agents[1 - seat] = load_agent(opp, f"opp{seed}{seat}")
            else:
                agents[1 - seat] = opp_arg or "starter"
            env = make("kaggriculture", configuration={"seed": seed}, debug=True)
            try:
                env.run(agents)
            except Exception as e:
                failures.append(f"seed {seed} seat {seat}: RAISED {e!r}")
                continue
            final = env.steps[-1]
            st, rw = final[seat].status, final[seat].reward
            if st != "DONE":
                failures.append(f"seed {seed} seat {seat}: status {st}")
            elif rw < MIN_REWARD:
                failures.append(f"seed {seed} seat {seat}: collapse reward=${rw:.0f}")
            print(f"  seed {seed} seat {seat}: {st} ${rw:.0f} (opp ${final[1 - seat].reward:.0f})")

    if failures:
        print("\nSMOKE TEST FAILED:")
        for f in failures:
            print("  -", f)
        sys.exit(1)
    print("\nsmoke OK")


if __name__ == "__main__":
    main()
