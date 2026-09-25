"""Is "what did this top agent plant" predictable from the public state?

Decisive feasibility test for behaviour cloning. If a depth-limited tree on public features
cannot beat the majority-class baseline by much, then the choice is driven by hidden context
(the tape's own scheduling state) that an imitator cannot observe, and cloning is not a path.

Two splits, both reported:
  * by replay (rows are written in replay order, so a 80/20 positional split approximates a
    grouped split) -- in-distribution predictability
  * by team (hold out whole teams) -- generalization to unseen top agents

Usage: .venv/Scripts/python scripts/fit_plant_choice.py
"""
import collections
import json
import math
import os
import random
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "data", "plant_choices.jsonl")
BASE = {"WHEAT": 25, "CARROT": 35, "TOMATO": 60, "STRAWBERRY": 120, "MELON": 250}
CROPS = tuple(BASE)

# public, observable-at-decision-time features
NUM = ("day", "hour", "money", "hands", "empty", "n_wheat", "n_carrot", "n_tomato",
       "n_straw", "n_melon", "n_shops", "n_tomato_shop", "n_yarn",
       "r_wheat", "r_carrot", "r_tomato", "r_straw", "r_melon")


def featurise(r):
    d = {"day": r["day"], "hour": r["hour"], "money": r["money"], "hands": r["hands"],
         "empty": r["empty"], "n_wheat": r["n_wheat"], "n_carrot": r["n_carrot"],
         "n_tomato": r["n_tomato"], "n_straw": r["n_straw"], "n_melon": r["n_melon"],
         "n_shops": r["n_shops"], "n_tomato_shop": r["n_tomato_shop"], "n_yarn": r["n_yarn"]}
    for c in CROPS:
        p = r["p_" + c.lower() if c != "STRAWBERRY" else "p_straw"]
        d["r_" + ("straw" if c == "STRAWBERRY" else c.lower())] = round(p / BASE[c], 2)
    return d


def bucket(name, v):
    if name == "day":
        return min(int(v) // 4, 7)
    if name == "hour":
        return min(int(v) // 6, 3)
    if name == "money":
        return 0 if v < 5000 else 1 if v < 20000 else 2 if v < 60000 else 3
    if name == "hands":
        return min(int(v), 14)
    if name == "empty":
        return min(int(v) // 5, 8)
    if name.startswith("n_"):
        return min(int(v), 12)
    if name.startswith("r_"):
        return max(0, min(int(float(v) * 4), 16))       # price / base, quarter steps
    return int(v)


def entropy(counts):
    n = sum(counts.values())
    if n == 0:
        return 0.0
    return -sum((c / n) * math.log2(c / n) for c in counts.values() if c)


def build(rows, depth, max_depth, min_leaf):
    labels = collections.Counter(r["_y"] for r in rows)
    if depth >= max_depth or len(rows) < min_leaf or len(labels) == 1:
        return ("leaf", labels.most_common(1)[0][0], len(rows))
    base_e = entropy(labels)
    best = None
    for f in NUM:
        groups = collections.defaultdict(collections.Counter)
        for r in rows:
            groups[r["_f"][f]][r["_y"]] += 1
        if len(groups) < 2:
            continue
        e = sum((sum(g.values()) / len(rows)) * entropy(g) for g in groups.values())
        gain = base_e - e
        if best is None or gain > best[0]:
            best = (gain, f, groups)
    if not best or best[0] <= 1e-4:
        return ("leaf", labels.most_common(1)[0][0], len(rows))
    _, f, groups = best
    return ("node", f, {k: build([r for r in rows if r["_f"][f] == k], depth + 1, max_depth, min_leaf)
                        for k in groups}, len(rows))


def predict(tree, r):
    while tree[0] == "node":
        tree = tree[2].get(r["_f"][tree[1]]) or ("leaf", "WHEAT", 0)
    return tree[1]


def evaluate(train, test, max_depth=6, min_leaf=200, label=""):
    tree = build(train, 0, max_depth, min_leaf)
    correct = sum(1 for r in test if predict(tree, r) == r["_y"])
    maj = collections.Counter(r["_y"] for r in train).most_common(1)[0][0]
    base = sum(1 for r in test if r["_y"] == maj) / max(1, len(test))
    acc = correct / max(1, len(test))
    print(f"  {label:22s} train {len(train):6d}  test {len(test):6d}  "
          f"acc {acc:6.1%}   majority-baseline {base:6.1%}   lift {acc - base:+6.1%}")
    return acc, base


def main():
    rows = []
    with open(DATA, encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            r["_f"] = {k: bucket(k, v) for k, v in featurise(r).items()}
            r["_y"] = r["crop"]
            rows.append(r)
    print(f"样本 {len(rows)}\n")

    # --- split 1: by position in the file (rows are contiguous per replay)
    cut = int(len(rows) * 0.8)
    print("切分 1：按局（前 80% 训练 / 后 20% 测试，近似 group split）")
    best = None
    for md, ml in ((4, 200), (6, 200), (8, 100), (10, 50), (12, 20)):
        acc, base = evaluate(rows[:cut], rows[cut:], md, ml, f"depth={md} min_leaf={ml}")

    # --- split 2: hold out whole teams
    teams = sorted({r["team"] for r in rows})
    random.Random(7).shuffle(teams)
    hold = set(teams[:6])
    tr = [r for r in rows if r["team"] not in hold]
    te = [r for r in rows if r["team"] in hold]
    print(f"\n切分 2：按队伍（留出 6 支没见过的队伍：{sorted(hold)}）")
    for md, ml in ((6, 200), (8, 100), (10, 50)):
        evaluate(tr, te, md, ml, f"depth={md} min_leaf={ml}")


if __name__ == "__main__":
    main()
