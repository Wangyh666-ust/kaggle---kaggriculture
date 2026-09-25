"""Compare two agents by token content, separating "same code" from "same file".

Question it answers: when a public notebook's agent looks 99% like ours, is it
literally our bytes, our code re-ordered, or a genuinely different program that
shares a common ancestor?

Three numbers, cheapest first:
  * exact multiset equality of tokens  -- "is this the same code at all?"
  * token counts and the symmetric difference -- "what differs, if anything?"
  * sequence ratio on a DOWNSAMPLED token list -- "is it the same order?"

The downsample matters. `difflib.SequenceMatcher(...).ratio()` on two 500k-token
sequences with autojunk=False is quadratic and effectively never returns; on
every 200th token it is instant and answers the ordering question just as well.

Usage:
  .venv/Scripts/python scripts/token_compare.py A.py B.py [--stride 200]
"""
import argparse
import collections
import difflib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lineage_id import norm  # noqa: E402


def compare(pa, pb, stride, top=15):
    ta = norm(open(pa, "rb").read()).split()
    tb = norm(open(pb, "rb").read()).split()
    ca, cb = collections.Counter(ta), collections.Counter(tb)

    print(f"A: {os.path.basename(pa):44s} {len(ta):>9,} tokens")
    print(f"B: {os.path.basename(pb):44s} {len(tb):>9,} tokens")

    same_set = set(ca) == set(cb)
    print(f"\ntoken vocabulary identical : {same_set}"
          f"   (A only {len(set(ca) - set(cb)):,}, B only {len(set(cb) - set(ca)):,})")
    print(f"token multiset identical   : {ca == cb}")

    da, db = ca - cb, cb - ca
    print(f"A-only tokens {sum(da.values()):,} ({len(da):,} distinct) | "
          f"B-only {sum(db.values()):,} ({len(db):,} distinct)")
    if da:
        print("  A-only:", da.most_common(top))
    if db:
        print("  B-only:", db.most_common(top))

    sa, sb = ta[::stride], tb[::stride]
    print(f"\nsequence ratio on every {stride}th token ({len(sa):,} vs {len(sb):,}):")
    print(f"  ratio (order-sensitive) : "
          f"{difflib.SequenceMatcher(None, sa, sb).ratio():.4f}")
    print("  NB: difflib.quick_ratio is a CHARACTER-multiset bound. On two long")
    print("  Python files it saturates near 1.0 and means nothing -- do not quote it.")


def identifiers(path):
    """Distinct identifier-ish names, which is where the real difference lives."""
    import io
    import tokenize
    out = collections.Counter()
    with open(path, "rb") as fh:
        for tok in tokenize.tokenize(io.BytesIO(fh.read()).readline):
            if tok.type == tokenize.NAME:
                out[tok.string] += 1
    return out


def compare_ids(pa, pb, top=60):
    """What does each file define that the other does not? Layers live here."""
    import keyword
    ia, ib = identifiers(pa), identifiers(pb)
    # Keep names that look like this codebase's own: private/upper/dashed
    # identifiers, not locals like `o`, `i`, `action`.
    def own(counter):
        return {n for n in counter
                if len(n) > 4 and not keyword.iskeyword(n)
                and (n.startswith("_") or n.isupper()
                     or any(ch.isdigit() for ch in n) or "_" in n)}
    oa, ob = own(ia), own(ib)
    only_a = sorted(oa - ob)
    only_b = sorted(ob - oa)
    print(f"\n=== identifier diff (names unique to each side) ===")
    print(f"A defines {len(only_a)} names B lacks;  B defines {len(only_b)} names A lacks")
    print(f"\nA only ({len(only_a)}):")
    for n in only_a[:top]:
        print(f"    {n}  x{ia[n]}")
    print(f"\nB only ({len(only_b)}):")
    for n in only_b[:top]:
        print(f"    {n}  x{ib[n]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--stride", type=int, default=200,
                    help="downsample factor; 1 = full sequences (slow, can hang)")
    args = ap.parse_args()
    compare(args.a, args.b, max(1, args.stride))
    compare_ids(args.a, args.b)


if __name__ == "__main__":
    main()
