"""Build a ladder of entry points up a stacked agent, for layer attribution.

A "layer-stacked" agent applies its layers in sequence, each one wrapping the
previous function. The wrapper saves its parent before redefining, so every
intermediate stage survives as a module-level name (`_FX_PARENT`, `_MP_ENTRY`,
...). Kaggle's loader takes the LAST callable in the namespace, so appending
`_ABLATION_ENTRY = <stage>` to a copy of the source forces that stage to be the
entry. That turns "which layer carries the edge?" into a measurable curve
without touching a line of the agent's code.

Usage:
  .venv/Scripts/python scripts/build_ladder.py opponents/tetsutani_cha22/main.py \
      --outdir opponents_ladder --stages _FX_PARENT,_FX_ENTRY,ig_agent
  .venv/Scripts/python scripts/build_ladder.py <src> --outdir d --auto
"""
import argparse
import importlib.util
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def stage_names(src):
    """Wrapper names in file order: each `_X_PARENT = <prev>` marks a rung."""
    names = []
    for m in re.finditer(r"^(_[A-Z0-9]+_(?:PARENT|HOST|ENTRY))\s*=", src, re.M):
        if m.group(1) not in names:
            names.append(m.group(1))
    return names


def build(src_path, outdir, stages):
    src = open(src_path, encoding="utf-8").read()
    base = os.path.splitext(os.path.basename(src_path))[0]
    made = []
    for i, name in enumerate(stages):
        d = os.path.join(ROOT, outdir, f"{i:02d}_{name.replace('_', '').lower()}")
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, "main.py")
        # The appended binding is the newest name in the namespace, so
        # get_last_callable() -- which walks insertion order -- selects it.
        open(path, "w", encoding="utf-8").write(
            src + f"\n\n# ==== ablation: freeze the entry point at {name} ====\n"
                  f"_ABLATION_ENTRY = {name}\n")
        made.append((d, name))
    return made, base


def verify(paths):
    """Confirm the loader picks the stage we asked for.

    Compare object IDENTITY, not __name__: every cha20 rung is a distinct
    function that happens to share the name `cha20_entry_agent`, so a
    name comparison reports a false mismatch on the whole ladder.
    """
    ok = True
    for d, name in paths:
        p = os.path.join(d, "main.py")
        src = open(p, encoding="utf-8").read()
        env = {}
        try:
            # One exec only: get_last_callable() builds its own namespace, so
            # comparing across two execs would compare distinct function objects
            # and fail for every rung, including the correct ones.
            exec(compile(src, p, "exec"), env)  # noqa: S102 - our own generated file
            last = [v for v in env.values() if callable(v)][-1]
        except Exception as exc:  # noqa: BLE001
            print(f"  {os.path.relpath(d, ROOT):34s} LOAD FAIL {exc}")
            ok = False
            continue
        same = last is env.get(name)
        if not same:
            ok = False
        print(f"  {os.path.relpath(d, ROOT):34s} entry={getattr(last, '__name__', '?'):20s}"
              f" is {name}: {'OK' if same else 'MISMATCH'}")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--stages", default="")
    ap.add_argument("--auto", action="store_true",
                    help="use every wrapper name found in the file, in order")
    ap.add_argument("--every", type=int, default=1,
                    help="with --auto, keep only every Nth rung (thins a long ladder)")
    args = ap.parse_args()

    src_path = args.source if os.path.isabs(args.source) else os.path.join(ROOT, args.source)
    src = open(src_path, encoding="utf-8").read()

    if args.auto:
        found = stage_names(src)
        stages = found[::max(1, args.every)]
        if found and found[-1] not in stages:
            stages.append(found[-1])
    else:
        stages = [s.strip() for s in args.stages.split(",") if s.strip()]

    print(f"source: {os.path.relpath(src_path, ROOT)}")
    print(f"stages ({len(stages)}): {', '.join(stages)}\n")
    made, base = build(src_path, args.outdir, stages)
    verify(made)
    print(f"\nwrote {len(made)} variants under {args.outdir}/")
    print("run:  .venv/Scripts/python scripts/tournament.py --candidate main.py "
          f"--opponents {args.outdir}/*/main.py --seeds 1000-1049 --seats 01 --loader kaggle")


if __name__ == "__main__":
    main()
