"""Build, hash-log and (optionally) submit main.py — one auditable path.

Why this exists
---------------
We have two submissions of byte-identical code that scored 2452.2 and 1763.7
(688 apart), while the #1 team's two submissions of their code sit 87 apart.
That is the signature of "the wrong file went up", not of rating noise — and
`tar -czf submission.tar.gz main.py && kaggle ... submit` leaves no record of
*which* main.py that tarball held. From now on every submission is logged with
its hash, so the question is answerable after the fact.

Default behaviour is DRY RUN: it builds the tarball, prints the hash, appends a
row to results/submissions.md with status "built", and stops. Pass --submit to
actually send it (this consumes a daily submission slot and starts a fresh
rating run).

Usage:
  .venv/Scripts/python scripts/submit.py --version v26 --note "herd mix: cows 6->10"
  .venv/Scripts/python scripts/submit.py --version v26 --note "…" --submit
"""
import argparse
import hashlib
import os
import subprocess
import sys
import tarfile
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PY = os.path.join(ROOT, ".venv", "Scripts", "python.exe")
LOG = os.path.join(ROOT, "results", "submissions.md")


def say(text):
    """Print text that may not survive the console's encoding.

    This shell's stdout is GBK; Kaggle's CLI output carries U+FFFD. Printing it
    raw raises UnicodeEncodeError, and because the print sits after the submit
    call, a *successful* submission looks like a crash and never reaches the log.
    """
    out = sys.stdout
    try:
        out.write(text + "\n")
    except UnicodeEncodeError:
        enc = getattr(out, "encoding", None) or "utf-8"
        out.write(text.encode(enc, errors="replace").decode(enc, errors="replace") + "\n")
    out.flush()


def latest_ref(py):
    """Most recent submission ref, so the log records what actually went up."""
    import json
    r = subprocess.run([py, "-m", "kaggle", "competitions", "submissions", "kaggriculture",
                        "--format", "json"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        return str(json.loads(r.stdout)[0]["ref"])
    except Exception:
        return ""


def sha256_file(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read().replace(b"\r\n", b"\n")).hexdigest()


def entry_point(main_py):
    """Confirm Kaggle's 'last callable in the namespace' rule resolves to agent.

    Kaggle picks `[v for v in namespace.values() if callable(v)][-1]` — the last
    callable *object*, not the one named `agent`. Several upstream builds alias
    the entry point (`_final_sell_block_reorder_entrypoint = agent`), so compare
    object identity, not the name. A name check rejects perfectly good files.
    """
    sys.path.insert(0, ROOT)
    import importlib.util
    spec = importlib.util.spec_from_file_location("_submit_check", main_py)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    cbs = [v for k, v in vars(mod).items() if callable(v) and not k.startswith("__")]
    if not cbs:
        return None, False
    return getattr(cbs[-1], "__name__", "<callable>"), (cbs[-1] is getattr(mod, "agent", None))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True, help="e.g. v26")
    ap.add_argument("--note", default="", help="what changed / why")
    ap.add_argument("--source", default="main.py")
    ap.add_argument("--submit", action="store_true", help="actually submit (consumes a slot)")
    ap.add_argument("--message", default="")
    args = ap.parse_args()

    src = os.path.join(ROOT, args.source)
    if not os.path.exists(src):
        print(f"missing {args.source}")
        return 1

    digest = sha256_file(src)
    lines = sum(1 for _ in open(src, encoding="utf-8", errors="replace"))
    last_name, is_agent = entry_point(src)
    if not is_agent:
        print(f"REFUSING TO BUILD: the last callable in the namespace is {last_name!r}, "
              f"which is NOT the `agent` object.\n"
              f"Kaggle resolves the entry point as the last callable; this file would not run.")
        return 2

    tarball = os.path.join(ROOT, "submission.tar.gz")
    with tarfile.open(tarball, "w:gz") as tf:
        tf.add(src, arcname="main.py")

    print(f"source    : {args.source}  ({lines} lines)")
    print(f"sha256    : {digest}")
    print(f"entrypoint: agent (last callable — Kaggle rule satisfied)")
    print(f"tarball   : submission.tar.gz ({os.path.getsize(tarball):,} bytes)")

    status = "built"
    ref = ""
    if args.submit:
        msg = args.message or f"{args.version}: {args.note} [sha256 {digest[:16]}]"
        r = subprocess.run([PY, "-m", "kaggle", "competitions", "submit", "kaggriculture",
                            "-f", tarball, "-m", msg],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        out = (r.stdout or "") + (r.stderr or "")
        # The console here is GBK. Kaggle's output contains U+FFFD (from our own
        # errors="replace" decode), which GBK cannot encode -- printing it raw
        # raises UnicodeEncodeError *after* the submission has already gone
        # through, so the run looks failed when it succeeded. Never print this
        # text unsanitised.
        say(out.strip()[-1500:])
        ok = "Successfully" in out or r.returncode == 0
        status = "submitted" if ok else "FAILED"
        if ok:
            ref = latest_ref(PY)

    with open(LOG, "a", encoding="utf-8") as fh:
        if not os.path.exists(LOG) or os.path.getsize(LOG) == 0:
            fh.write("# 提交记录（scripts/submit.py 自动追加）\n\n"
                     "| 时间 | 版本 | 状态 | sha256(前16位) | 行数 | 说明 |\n"
                     "|---|---|---|---|---|---|\n")
        ref_note = f"ref {ref} | " if ref else ""
        fh.write(f"| {time.strftime('%Y-%m-%d %H:%M')} | {args.version} | {status} | "
                 f"`{digest[:16]}` | {lines} | {ref_note}{args.note} |\n")
    print(f"logged -> results/submissions.md  (status: {status})")
    if not args.submit:
        print("\ndry run — nothing sent. Re-run with --submit to send.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
