"""Build v42 = v41 + tetsutani's BUYDIP layer (`_BD`).

Layer choice, and why not the others. After `_MPX` (v40) and `_CXD` (v41), the
remaining non-zero rungs of the 12-level ladder were the early lead-sell group
(-8pp each). Reading them first changed the plan:

  * `_DP` DAWNPX and `_MP` are THE SAME FUNCTION with a different hour window
    (`{0,1,2}` vs `{10,11,12,13}`) and the same tape look-ahead. They are
    duplicates of one idea, and the ladder agrees: DP measured 0, MP -8pp.
  * Both also read `_FX_STATE[...]["quotes"]`, so they are not standalone -- they
    need `_FX` running to have a quote history, and without it their
    "skip if below the recent average" test silently does nothing.
  * `_MPX`, already in v40, is the most principled member of that family (it uses
    the engine's own price curve). Stacking cruder duplicates on top is likely
    redundant, so we skip them.

`_BD` is the one remaining layer that (a) measured non-zero, (b) is a DIFFERENT
mechanism -- avoid buying wheat high, rather than selling early -- and (c) has no
dependency on host internals at all: it reads only `observation["step"]`,
`observation["player"]`, `observation["market"]["prices"]`, and the action.

Usage:
  .venv/Scripts/python experiments/v42/make_v42.py
"""
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
HOST = os.path.join(ROOT, "experiments", "v41", "cxd.py")
DONOR = os.path.join(ROOT, "opponents", "tetsutani_cha22", "main.py")
OUT = os.path.join(ROOT, "experiments", "v42", "buydip.py")

# Everything from the BUYDIP banner up to (not including) the donor's binding
# of `_BD_PARENT`, which names the donor's stack.
BLOCK_RE = re.compile(
    r"(# =+\n# BUYDIP: .*?\n_BD_PARENT = cha20_entry_agent\n)", re.S)

WRAPPER = '''

# ===========================================================================
# v42: bind BUYDIP onto our stack. The wrapper is the donor's, renamed so that
# binding `agent` to it keeps Kaggle's last-callable rule on the full stack.
# ===========================================================================
_BD_PARENT = agent


def _bd_entry(observation, configuration=None):
    if int(observation.get("step", 0)) == 0:
        _BD_REPORT.update(bd_split=0, bd_pending_units=0, bd_released=0, bd_errors=0)
        _BD_STATE.clear()
    action = _BD_PARENT(observation, configuration)
    try:
        return _bd_apply(observation, action)
    except Exception:
        _BD_REPORT["bd_errors"] += 1
        return action


_bd_entry.telemetry = _BD_REPORT
agent = _bd_entry
'''


def main():
    host = open(HOST, encoding="utf-8").read()
    donor = open(DONOR, encoding="utf-8").read()

    if "_BD_" in host or "_bd_" in host:
        sys.exit("host already defines a _BD symbol; pick new names")
    m = BLOCK_RE.search(donor)
    if not m:
        sys.exit("BUYDIP block not found in donor -- donor layout changed?")
    block = m.group(1).replace("_BD_PARENT = cha20_entry_agent", "_BD_PARENT = agent")

    body = host.rstrip("\n") + "\n\n\n" + block.strip("\n") + "\n" + WRAPPER
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8").write(body)

    print(f"host   : {os.path.relpath(HOST, ROOT)}  ({len(host):,} B)")
    print(f"donor  : {os.path.relpath(DONOR, ROOT)}  BUYDIP block {len(block):,} B")
    print(f"wrote  : {os.path.relpath(OUT, ROOT)}  ({len(body):,} B)")
    for marker in ("_BD_ITEM", "_bd_apply", "_BD_CAP", "_bd_entry",
                   "_MPX_ITEMS", "def cxd_agent", "_BD_PARENT = agent"):
        print(f"  marker {marker:20s} x{body.count(marker)}")
    # `_bd_apply` touches nothing but the public observation and the action.
    print("  dependency check: _bd_apply references only "
          f"{sorted({n for n in ('_IMPL', 'projected_shed', 'FarmView', '_BD_STATE') if n in block})}")

    env = {}
    exec(compile(body, OUT, "exec"), env)  # noqa: S102 - our own generated file
    entry = [v for v in env.values() if callable(v)][-1]
    ok = entry is env["agent"] and entry.__name__ == "_bd_entry"
    print(f"entry  : {entry.__name__}  last-callable-is-agent: {ok}")
    if not ok:
        sys.exit("entry point check failed")


if __name__ == "__main__":
    main()
