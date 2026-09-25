"""Identify which known agent lineage an unknown main.py belongs to.

Question it answers: when a public notebook hands us an agent, is it a
*new* strategy or a mutation of one we already have? A sha256 match is a
clone; a high structural similarity means "diff this against that base".

Method: strip comments/docstrings/blank lines, then (a) exact sha256 of the
raw bytes, (b) sha256 of the normalised body, (c) difflib ratio against every
candidate. Also prints marker-presence for a list of lineage fingerprints.

Usage:
  .venv/Scripts/python scripts/lineage_id.py tmp_v39/tetsutani/<file>.py
"""
import difflib
import glob
import hashlib
import io
import os
import re
import sys
import tokenize

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

MARKERS = [
    # our own / v9 lineage
    "_R108_SHOP_ROUTES", "_V92_TABLE", "V9_OPENING_STEP0", "_R42_OPENING",
    "_v219_qualifies", "make_agent", "_IMPL", "chassis",
    # Ahmed lineage (V40..V56)
    "_PIPE3", "_R42_", "V55", "V56", "_SR_",
    # notebook-specific
    "cha20", "cha22", "ig_agent", "_ig_close_queue", "FARMERS_MARKET",
]


def norm(path_or_bytes):
    b = open(path_or_bytes, "rb").read() if isinstance(path_or_bytes, str) else path_or_bytes
    try:
        toks = list(tokenize.tokenize(io.BytesIO(b).readline))
    except Exception:
        return re.sub(r"\s+", " ", b.decode("utf-8", "replace"))
    out = []
    for t in toks:
        if t.type in (tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE, tokenize.INDENT,
                      tokenize.DEDENT, tokenize.ENCODING, tokenize.ENDMARKER):
            continue
        out.append(t.string)
    return " ".join(out)


def candidates():
    out = []
    for pat in ("opponents/*/main.py", "experiments/*/main.py", "experiments/*/*.py",
                "main.py", "kernels/*/*.ipynb"):
        for p in glob.glob(os.path.join(ROOT, pat)):
            out.append(p)
    return sorted(set(out))


def main():
    target = sys.argv[1]
    tb = open(target, "rb").read()
    tn = norm(tb)
    print(f"target: {target}")
    print(f"  raw  sha256 {hashlib.sha256(tb).hexdigest()}")
    print(f"  norm sha256 {hashlib.sha256(tn.encode()).hexdigest()}")
    print(f"  bytes {len(tb):,}  norm tokens {len(tn):,}")
    for m in MARKERS:
        c = tb.count(m.encode())
        if c:
            print(f"    marker {m:22s} x{c}")

    scored = []
    for p in candidates():
        try:
            cb = open(p, "rb").read()
        except Exception:
            continue
        if len(cb) < 20000:      # skip tiny experiment shims
            continue
        cn = norm(cb)
        # Downsample before SequenceMatcher. Two traps here, both hit in practice:
        #   * quick_ratio() is a CHARACTER-multiset bound: on long Python files it
        #     saturates near 1.0 and ranks everything as a near-clone.
        #   * ratio() on the full 500k-token sequences is quadratic and never
        #     returns. On every 100th token it is instant and still order-sensitive.
        r = difflib.SequenceMatcher(None, tn.split()[::100], cn.split()[::100]).ratio()
        scored.append((r, p, hashlib.sha256(cb).hexdigest()[:16], len(cb)))
    scored.sort(reverse=True)
    print("\n  closest known agents (order-sensitive ratio, sampled every 100th token):")
    for r, p, h, n in scored[:8]:
        rel = os.path.relpath(p, ROOT)
        tag = "  <== IDENTICAL" if r > 0.999 else ""
        print(f"    {r:.4f}  {h}  {n:>8,}B  {rel}{tag}")


if __name__ == "__main__":
    main()
