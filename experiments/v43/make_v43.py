"""Build v43 = v41 with the minimal wheat opening, matching the ladder family.

Why this single constant. Fingerprinting 14 recent ladder replays
(scripts/opponent_fingerprint.py) split the opponents into four opening
signatures, none of them ours. The family we lose to -- 10 of 14 games, we win 3
of them -- opens with `[BUY_PRODUCT WHEAT 5, BUY_SEED WHEAT 1]` and then
`[HIRE x5, COW 2, SHEEP 2]`. Our own opening is `[BUY WHEAT 10, SELL WHEAT 5,
BUY_SEED WHEAT 1]` and the same `[HIRE x5, COW 2, SHEEP 2]`.

So the two agents are identical in this fingerprint except for the wheat order:
they buy 5 and stop (net +5 wheat, -$65); we buy 10 and sell 5 (net +5 wheat,
-$95). Same wheat position, one fewer order, $30 cheaper.

This is the same change nathanjacob argued for in "Beyond V43" (his C9 opening)
and that we partly dismissed: we disproved his *timing* story -- C15 does hire on
the same turn, and the whole opening is worth ~$26 locally -- but a $26 local
effect is exactly the size that decides these ladder games, where the median
loss is a few hundred dollars. This tests the variant itself rather than his
explanation for it.

Usage:
  .venv/Scripts/python experiments/v43/make_v43.py
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
HOST = os.path.join(ROOT, "experiments", "v41", "cxd.py")
OUT = os.path.join(ROOT, "experiments", "v43", "minopen.py")

OLD = 'V9_OPENING_STEP0 = (("BUY_PRODUCT", "WHEAT", 10), ("SELL", "WHEAT", 5))'
NEW = 'V9_OPENING_STEP0 = (("BUY_PRODUCT", "WHEAT", 5),)   # v43: match the ladder family'


def main():
    src = open(HOST, encoding="utf-8").read()
    if OLD not in src:
        sys.exit("opening constant not found -- host changed?")
    body = src.replace(OLD, NEW, 1)
    open(OUT, "w", encoding="utf-8").write(body)
    print(f"host  : {os.path.relpath(HOST, ROOT)}")
    print(f"wrote : {os.path.relpath(OUT, ROOT)}  ({len(body):,} B)")
    assert NEW in body and OLD not in body

    env = {}
    exec(compile(body, OUT, "exec"), env)  # noqa: S102 - our own generated file
    entry = [v for v in env.values() if callable(v)][-1]
    ok = entry is env["agent"]
    print(f"entry : {entry.__name__}  last-callable-is-agent: {ok}")
    if not ok:
        sys.exit("entry point check failed")


if __name__ == "__main__":
    main()
