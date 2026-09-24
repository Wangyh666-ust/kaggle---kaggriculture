"""Build experiments/v32/*.py = main.py + the v32 preempt-with-repay block.

Pure append: the first `len(main.py)` bytes of every candidate are byte-identical
to main.py, so no existing layer is rebound.  The entry point rule (main.py's
`agent` must stay the LAST callable in the module namespace) is preserved by the
block's own `_V32_PARENT = agent; del agent; def agent(...)` tail.

Variants differ ONLY in `_preempt_gate`.  Nothing else is touched, so any
difference between them is attributable to the gate.

Usage: .venv/Scripts/python scripts/make_v32.py
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MAIN = os.path.join(ROOT, "main.py")
BLOCK = os.path.join(ROOT, "tmp_ab", "v32_block.py")
OUT = os.path.join(ROOT, "experiments", "v32")

MAIN_GATE = '''def _preempt_gate(obs, step):
    """v32 main: boatlee's clone-distance gate, verbatim threshold."""
    return _clone_distance(obs) <= _PREEMPT_MAX_CLONE_DISTANCE
'''

GATES = {
    # the artifact the task asks for: boatlee's gate, as ported
    "preempt_repay.py": MAIN_GATE,

    # control: gate forced always open.  Step 1 measured the clone distance to be
    # identically 0 against every member of our family, so this should be
    # behaviourally IDENTICAL to preempt_repay.py on the whole benchmark panel.
    # If it is, the gate is a proven no-op here (and the ablation is clean).
    "abl_ungated.py": '''def _preempt_gate(obs, step):
    """ablation: gate forced always open (no clone detection at all)."""
    return True
''',

    # v31's gate: |our money - rival money| < $0.5 at step 1, latched.  The only
    # gate measured in this repo that actually separates the public panel
    # (0/240) from the near-clone panel (120/160).
    "g1_gated.py": '''_G1_EPS = 0.5


def _preempt_gate(obs, step):
    """v31's G1 gate: turn-0 cash round trip identical to ours, latched."""
    seat = _pt_seat(obs)
    latched = _G1_STATE[seat]
    if latched is not None:
        return latched
    if int(step or 0) < 1:
        return False
    try:
        farms = list(_get(obs, "farms", []) or [])
        mine = float(_get(farms[seat], "money", 0) or 0)
        theirs = float(_get(farms[1 - seat], "money", 0) or 0)
        _G1_STATE[seat] = abs(mine - theirs) < _G1_EPS
    except Exception:
        _G1_STATE[seat] = False
    return _G1_STATE[seat]
''',
}


def main():
    main_src = open(MAIN, encoding="utf-8").read()
    block = open(BLOCK, encoding="utf-8").read()
    lines = block.split("\n")
    gi = [i for i, L in enumerate(lines) if L.startswith("def _preempt_gate(obs, step):")]
    si = [i for i, L in enumerate(lines) if L.startswith("# --- projected shed")]
    assert len(gi) == 1, "gate anchor must be unique"
    assert len(si) == 1, "projected-shed marker must be unique"
    head = "\n".join(lines[:gi[0]]) + "\n"
    rest = "\n".join(lines[si[0]:])

    os.makedirs(OUT, exist_ok=True)
    variants = dict(GATES)
    # both ablations use the main (clone-distance) gate; only repayment differs
    variants["abl_norepay.py"] = GATES["preempt_repay.py"]
    variants["abl_norepay_multi.py"] = GATES["preempt_repay.py"]

    REPAY_HEAD = ("def _repay_shift(obs, action, step):\n"
                  "    if not _PREEMPT_ENABLED:\n"
                  "        return action")

    # abl_norepay.py: repayment short-circuits, so `state["due"]` is never
    # cleared -- preemption fires exactly ONCE per game and is then blocked
    # forever by its own `if state.get("due")` guard.  That is a legitimate
    # "one-shot shift" variant but NOT the give-back ablation.
    DEGENERATE = "def _repay_shift(obs, action, step):\n    if True:\n        return action"

    # abl_norepay_multi.py: the correct give-back ablation.  The obligation is
    # cleared every turn (so preemption keeps firing at full rate) but the sale
    # it owed is NOT cancelled -- the shifted quantity simply stays sold.
    MULTI = (
        "def _repay_shift(obs, action, step):\n"
        "    # NO-REPAY ABLATION: clear the obligation so preemption keeps firing,\n"
        "    # but do NOT cancel the sale it owed.  Total sold therefore rises.\n"
        "    state = _pt_shift_state(obs, step)\n"
        "    if int(state.get(\"due_step\", -1)) == step:\n"
        "        due = dict(state.get(\"due\") or {})\n"
        "        _PREEMPT_REPORT[\"repay_turns\"] += 1\n"
        "        _PREEMPT_REPORT[\"repay_offered\"] += sum(due.values())\n"
        "        _PREEMPT_REPORT[\"repay_unmatched\"] += sum(due.values())\n"
        "        state[\"due_step\"], state[\"due\"] = -1, {}\n"
        "    return action")

    for name, gate in variants.items():
        text = main_src + head + gate + rest
        if name == "abl_norepay.py":
            text = text.replace(REPAY_HEAD, DEGENERATE, 1)
            assert DEGENERATE in text, "repay anchor not found"
        elif name == "abl_norepay_multi.py":
            text = text.replace(REPAY_HEAD, MULTI, 1)
            assert MULTI in text, "repay anchor not found"
        path = os.path.join(OUT, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        assert text.startswith(main_src), name + ": not a pure append"
        print("wrote", os.path.relpath(path, ROOT), len(text.split("\n")), "lines")


if __name__ == "__main__":
    sys.exit(main())
