"""Build v44 = v41 with `_ADV_LOOK` 4 -> 6.

Why this constant, and why it needs a test rather than trust.

For it (three independent public sources, from a forum sweep):
  * alperen5252525 "First in Line" (59 votes) keeps the whole V48 core and changes
    essentially one thing: `_ADV_LOOK` 3 -> 8. Evidence there is unusually
    careful for this competition -- 324 games on 3 dev seeds x 6 opponents x both
    seats to screen, then 432 games on 12 previously UNUSED seeds to confirm:
    136W-8L, mean margin +7,608, worst margin -171 versus the unmodified public
    V48's 115W-7L-22T, worst margin -1,196. A worst-case margin moving from
    -1,196 to -171 is exactly the few-hundred-dollar band our ladder games sit in.
  * ghazarosghazaros "Lookahead Edits" reports single-submission live results:
    `_ADV_LOOK=6` gave 2644.2, his account's best; 9 and 10 reverse; and stacking
    a second leftover layer on the same tape reverses live.
  * The cha22 notebook (which is byte-identical to our opponents/tetsutani_cha22)
    concludes from 11k ladder replays that "the edge is the same-turn sale race:
    the most robust winner-loser difference is realised unit price, +8-10%".

Against it: our own B2 ablation. In v32 we measured that damage scales with the
sale-advance look-ahead (3-4 turns -> -24/320, 1 turn -> -7/320), i.e. LONGER was
worse. That was a different layer with a repay mechanism, but it is the same
mechanism family, so the two bodies of evidence genuinely conflict. A conflict
with real evidence on both sides is exactly what an A/B is for.

The host comment at main.py:6907 reads `_ADV_LOOK=4` with "3 -> 4", so we are
already on the same axis the public sources are moving along.

Usage:
  .venv/Scripts/python experiments/v44/make_v44.py
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
HOST = os.path.join(ROOT, "experiments", "v41", "cxd.py")
OUT = os.path.join(ROOT, "experiments", "v44", "adv6.py")

OLD = "_ADV_LOOK=4"
NEW = "_ADV_LOOK=6   # v44: 4 -> 6 (see make_v44.py for the conflicting evidence)"


def main():
    src = open(HOST, encoding="utf-8").read()
    if OLD not in src:
        sys.exit(f"{OLD!r} not found in the host -- constant renamed?")
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
    print(f"host  _ADV_LOOK = {env.get('_ADV_LOOK')}")
    if not ok or env.get("_ADV_LOOK") != 6:
        sys.exit("check failed")


if __name__ == "__main__":
    main()
