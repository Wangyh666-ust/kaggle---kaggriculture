"""Local end-to-end reproduction of the day-1 hire-failure cascade.

Runs ``main.py`` against a scripted opponent in the real kaggle-environments
engine and reports, for each game:

    money @ step 24 (end of day 0)   -> must be >= $4 to buy the 3 HIREs
    hands @ step 25 (day 1, hour 1)  -> 1 hand instead of 3 when money < $4
    animals on the farm @ day 3 h23  -> the day-0 animal escapes 2 days later
    escapes by day 3

The scripted opponent variants isolate the single online ingredient that flips
the day-0 residue: whether the opponent's step-0 market list co-sells 10 WHEAT
in the same lockstep slot as our own sale.

Usage:
    PYTHONIOENCODING=utf-8 .venv/Scripts/python scripts/early_death_local_repro.py \
        [--opponent cosell|pass|<path to an opponent main.py>] [--games 2] \
        [--outdir .scratch_ed/local_repro]
"""
import argparse
import json
import os
import sys

from kaggle_environments import make

HIRE_COST_3 = 1 + 1 + 2          # _fib(0) + _fib(1) + _fib(2)


def cosell_agent(observation, configuration=None):
    """Mirror-opening opponent: buy 10 WHEAT then sell 10 WHEAT in slot 1.

    The rival's order list has to land on engine step 0: that is the step whose
    market slot 1 our own wheat sale is quoted in (the analysis reports it as
    "step 1" because env.steps[1] is the first observation after it).
    """
    if observation["step"] == 0:
        return {"farmer": ["PASS"], "hands": [],
                "market": [["BUY_PRODUCT", "WHEAT", 10], ["SELL", "WHEAT", 10]]}
    return {"farmer": ["PASS"], "hands": [], "market": []}


def pass_agent(observation, configuration=None):
    return {"farmer": ["PASS"], "hands": [], "market": []}


def animal_count(farm):
    return sum(1 for row in farm["tiles"] for t in row
               if isinstance(t, dict) and t.get("animal"))


def summarise(env, us=0):
    steps = env.steps
    obs24 = steps[24][us]["observation"]
    obs25 = steps[25][us]["observation"]
    farm = obs24["farms"][us]
    # escapes: animal present at d2 h23 that is gone from its structure at d3 h0
    t2 = steps[2 * 24 + 23][us]["observation"]["farms"][us]["tiles"]
    t3 = steps[3 * 24][us]["observation"]["farms"][us]["tiles"]
    esc = 0
    for y in range(len(t2)):
        for x in range(len(t2[y])):
            a, b = t2[y][x], t3[y][x]
            if isinstance(a, dict) and a.get("animal") and isinstance(b, dict) and not b.get("animal"):
                esc += 1
    return {
        "money_t1": steps[1][us]["observation"]["farms"][us]["money"],
        "money_t24": steps[24][us]["observation"]["farms"][us]["money"],
        "hands_t25": len(obs25["farms"][us]["hands"]),
        "herd_d3": animal_count(steps[3 * 24 + 23][us]["observation"]["farms"][us]),
        "escapes_d3": esc,
        "reward": env.steps[-1][us]["reward"],
        "opp_reward": env.steps[-1][1 - us]["reward"],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--opponent", default="cosell")
    ap.add_argument("--games", type=int, default=2)
    ap.add_argument("--outdir", default=".scratch_ed/local_repro")
    ap.add_argument("--seed0", type=int, default=1234)
    args = ap.parse_args()

    if args.opponent == "cosell":
        opp = cosell_agent
        opp_name = "scripted-cosell"
    elif args.opponent == "pass":
        opp = pass_agent
        opp_name = "scripted-pass"
    else:
        opp = args.opponent
        opp_name = args.opponent
    os.makedirs(args.outdir, exist_ok=True)

    print('opponent=%s  games=%d  (a game needs money_t24 >= $%d to buy 3 hands)'
          % (opp_name, args.games, HIRE_COST_3))
    print('%-5s %-10s %-10s %-9s %-8s %-8s %-9s' % (
        'game', 'money_t1', 'money_t24', 'hands_t25', 'herd_d3', 'esc_d3', 'margin'))
    n_bad = 0
    for g in range(args.games):
        env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": args.seed0 + g},
                   debug=False)
        env.run(["main.py", opp])
        s = summarise(env)
        n_bad += s["hands_t25"] < 3
        print('%-5d %-10.0f %-10.0f %-9d %-8d %-8d %+9.0f' % (
            g, s["money_t1"], s["money_t24"], s["hands_t25"], s["herd_d3"],
            s["escapes_d3"], s["reward"] - s["opp_reward"]))
        with open(os.path.join(args.outdir, 'local-%s-%d.json' % (opp_name.replace('/', '_'), g)),
                  'w', encoding='utf-8') as fh:
            json.dump(env.toJSON(), fh)
    print('\n%d/%d games with fewer than 3 hands at day-1 hour 1' % (n_bad, args.games))
    print('replays: %s/local-%s-*.json' % (args.outdir, opp_name.replace('/', '_')))


if __name__ == "__main__":
    main()
