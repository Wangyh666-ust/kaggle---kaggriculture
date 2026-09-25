"""Build v41 = v40 + tetsutani's F4 layer (`_CXD`, exact best-response ordering).

Why. The 12-rung prefix ablation of tetsutani's stack put `_CXD` second among
single layers (-16pp win rate), behind `_MPX` (-26pp) which v40 already carries.
`_CXD` is a mechanism we have never tested: it enumerates the orderings of the
planned SELL orders across the market slots and keeps the one that maximises the
worst-case factor margin, scored with the host's own `_v44y_factor_margin`.

Portability was checked before building, not assumed:
  * `_v44y_params` and `_v44y_factor_margin` exist in main.py and are
    BYTE-IDENTICAL to the donor's (asserted below).
  * `projected_shed` / `FarmView` are identical in the 1229-1242 region.
  * `_cxd_*` / `_CXD_*` names do not exist in main.py (no collision).
The layer body is copied verbatim; only the three parent/entry bindings change,
because they name the donor's stack rather than ours.

Usage:
  .venv/Scripts/python experiments/v41/make_v41.py
"""
import ast
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
HOST = os.path.join(ROOT, "experiments", "v40", "mpx.py")
DONOR = os.path.join(ROOT, "opponents", "tetsutani_cha22", "main.py")
OUT = os.path.join(ROOT, "experiments", "v41", "cxd.py")

# F4 block: header comment through the donor's own entry rebinding. Both
# `cha20_entry_agent = cxd_agent` and `kaggle_agent = cha20_entry_agent` are
# dropped: they name the donor's stack, and leaving the second in place would
# make `kaggle_agent` the last callable, breaking Kaggle's resolution to `agent`.
BLOCK_RE = re.compile(
    r"(# ==== F4: Layer D .*?)\n"
    r"cha20_entry_agent = cxd_agent\n"
    r"kaggle_agent = cha20_entry_agent\n", re.S)

# Our stack's entry before this layer; the layer must wrap it.
HOST_BINDING = ("_CXD_HOST = cha20_entry_agent", "_CXD_HOST = agent")

TAIL = "\n\nagent = cxd_agent   # v41: keep `agent` as the last callable\n"


def assert_identical_deps():
    """The two scoring functions this layer calls must match the donor's exactly."""
    def seg(path, name):
        src = open(path, encoding="utf-8").read()
        for node in ast.parse(src).body:
            if isinstance(node, ast.FunctionDef) and node.name == name:
                return ast.get_source_segment(src, node).strip()
        return None
    for name in ("_v44y_params", "_v44y_factor_margin"):
        a = seg(os.path.join(ROOT, "main.py"), name)
        b = seg(DONOR, name)
        if a is None:
            sys.exit(f"{name} missing from main.py -- cannot port _CXD")
        if a != b:
            sys.exit(f"{name} differs from the donor's; _CXD's scoring would not match")
        print(f"  dep {name:22s} byte-identical to donor  ({len(a):,} chars)")


def main():
    print("pre-flight:")
    assert_identical_deps()
    host = open(HOST, encoding="utf-8").read()
    donor = open(DONOR, encoding="utf-8").read()

    for clash in ("_cxd_it", "_CXD_", "_cxd_"):
        if clash in host:
            sys.exit(f"host already contains {clash!r}; pick new names")

    m = BLOCK_RE.search(donor)
    if not m:
        sys.exit("F4 block not found in donor -- donor layout changed?")
    block = m.group(1)
    if HOST_BINDING[0] not in block:
        sys.exit("F4 block does not contain the expected host binding")
    block = block.replace(*HOST_BINDING)

    body = host.rstrip("\n") + "\n\n\n" + block.strip("\n") + TAIL
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8").write(body)

    print(f"\nhost   : {os.path.relpath(HOST, ROOT)}  ({len(host):,} B)")
    print(f"donor  : {os.path.relpath(DONOR, ROOT)}  F4 block {len(block):,} B")
    print(f"wrote  : {os.path.relpath(OUT, ROOT)}  ({len(body):,} B)")
    for marker in ("_CXD_FIXED", "_cxd_candidates", "_cxd_reorder", "def cxd_agent",
                   "_CXD_HOST = agent", "_MPX_ITEMS"):
        print(f"  marker {marker:22s} x{body.count(marker)}")

    env = {}
    exec(compile(body, OUT, "exec"), env)  # noqa: S102 - our own generated file
    entry = [v for v in env.values() if callable(v)][-1]
    ok = entry is env["agent"] and entry.__name__ == "cxd_agent"
    print(f"entry  : {entry.__name__}  last-callable-is-agent: {ok}")
    if not ok:
        sys.exit("entry point check failed")


if __name__ == "__main__":
    main()
