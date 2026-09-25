"""Build v40 = v37 (main.py) + tetsutani's MODELPX layer (`_MPX`), verbatim.

Why this layer. A 12-rung prefix ablation of tetsutani's 1200-game stack
(`scripts/build_ladder.py`, results in `insights/local_findings.md` §8) put the
two largest single-layer contributions at `_MPX` (-26pp win rate) and `_CXD`
(-16pp); everything else was 0 to -8pp. `_MPX` is the cheapest to port: it is
self-contained, reads only public observation fields, and every helper it calls
(`_r37_market_price`, `projected_shed`, `FarmView`, `MAX_ORDERS`,
`_IMPL.chassis.routes`) already exists in main.py at the same line numbers.

What `_MPX` actually does -- and why it is NOT the RACE preemption we disproved
(B2): it recovers the rival's sale cadence from public inventory deltas, then
computes the engine's OWN price curve one step ahead
(`inv_next = inv + rival_avg + planned - town_draw`) and sells early ONLY when
the projected price is about to fall. Our RACE pulled planned sells forward
whenever the rival was dumping, with no price model. Same family, different
mechanism -- the ablation suggests the model is what carries it.

Byte-for-byte fidelity: the layer body is copied from
`opponents/tetsutani_cha22/main.py` lines 6977-7059 untouched. Only the two
parent bindings are rewritten, because they name the host stack's entry point.

Usage:
  .venv/Scripts/python experiments/v40/make_v40.py
"""
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
HOST = os.path.join(ROOT, "main.py")
DONOR = os.path.join(ROOT, "opponents", "tetsutani_cha22", "main.py")
OUT = os.path.join(ROOT, "experiments", "v40", "mpx.py")

# MODELPX block in the donor file: header comment through _mpx_apply's last
# line. `_MPX_PARENT = cha20_entry_agent` (line 7060) is deliberately excluded:
# it names the donor's entry, and we rebind it to ours below.
BLOCK_RE = re.compile(r"(# =+\n# MODELPX:.*?\n)(_MPX_PARENT = cha20_entry_agent\n)", re.S)

WRAPPER = '''

# ===========================================================================
# v40: bind MODELPX onto our own stack.
# `_MPX_PARENT = agent` is our entry point (the last callable before this
# block); the wrapper is the donor's, renamed so that binding `agent` to it
# keeps Kaggle's last-callable rule pointing at the full stack.
# ===========================================================================
_MPX_PARENT = agent


def _mpx_entry(observation, configuration=None):
    step = int(observation.get("step", 0))
    if step == 0:
        _MPX_REPORT.update(mpx_fires=0, mpx_units=0, mpx_errors=0)
    action = _MPX_PARENT(observation, configuration)
    try:
        return _mpx_apply(observation, action)
    except Exception:
        _MPX_REPORT["mpx_errors"] += 1
        return action


_mpx_entry.telemetry = _MPX_REPORT
agent = _mpx_entry
'''


def main():
    host = open(HOST, encoding="utf-8").read()
    donor = open(DONOR, encoding="utf-8").read()

    m = BLOCK_RE.search(donor)
    if not m:
        sys.exit("MODELPX block not found in donor -- donor file changed?")
    block = m.group(1)

    if "_MPX" in host:
        sys.exit("main.py already defines an _MPX symbol; pick new names")

    body = host.rstrip("\n") + "\n\n\n" + block.strip("\n") + "\n" + WRAPPER
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8").write(body)

    print(f"host   : {os.path.relpath(HOST, ROOT)}  ({len(host):,} B)")
    print(f"donor  : {os.path.relpath(DONOR, ROOT)}  MODELPX block {len(block):,} B")
    print(f"wrote  : {os.path.relpath(OUT, ROOT)}  ({len(body):,} B)")

    from kaggle_environments.agent import get_last_callable
    src = open(OUT, encoding="utf-8").read()
    env = {}
    exec(compile(src, OUT, "exec"), env)  # noqa: S102 - our own generated file
    entry = [v for v in env.values() if callable(v)][-1]
    ok = entry is env["agent"] and entry.__name__ == "_mpx_entry"
    print(f"entry  : {entry.__name__}  last-callable-is-agent: {ok}")
    for marker in ("_MPX_ITEMS", "_mpx_draw_units", "_mpx_apply", "_MPX_PARENT", "_mpx_entry"):
        print(f"  marker {marker:16s} x{src.count(marker)}")
    if not ok:
        sys.exit("entry point check failed")


if __name__ == "__main__":
    main()
