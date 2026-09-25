"""Extract the embedded submission archive from a kernel notebook.

Many public notebooks embed their submission as a base85/base64 blob (often
gzip'd, sometimes a whole tar.gz). This pulls the newest literal that decodes
into something containing a `main.py`, writes it to tmp_<x>/, and prints the
sha256 plus which known lineage it matches.

Usage:
  .venv/Scripts/python scripts/extract_embedded.py kernels/<dir>/<file>.ipynb --out tmp_v39/name
"""
import argparse
import ast
import base64
import glob
import hashlib
import io
import json
import os
import re
import sys
import tarfile
import gzip
import zlib

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def candidate_literals(src):
    """Yield (name, decoder_label, decoded_bytes) for every large string literal.

    Walks the AST rather than regexing the text: authors write the payload as a
    single string, as a parenthesised tuple of chunks, or as `+`-joined pieces,
    and `ast.literal_eval` handles all three where a regex only handles one.
    """
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            name = getattr(target, "id", None)
            if not name:
                continue
            value = node.value
            # A dict of payloads: PAYLOADS = {'main.py': '<b85>', ...}. Several
            # authors ship the whole release this way, and the AST walk above
            # only looked at scalar assignments, so it found nothing.
            if isinstance(value, ast.Dict):
                for k, v in zip(value.keys, value.values):
                    try:
                        name_k = ast.literal_eval(k)
                    except Exception:
                        name_k = None
                    if isinstance(name_k, str) and name_k.endswith(".py"):
                        try:
                            inner = ast.literal_eval(v)
                        except Exception:
                            continue
                        if isinstance(inner, str) and len(inner) > 4000:
                            for dec, lab in ((base64.b85decode, "b85"),
                                             (base64.b64decode, "b64")):
                                try:
                                    yield name_k, lab, dec(inner)
                                    break
                                except Exception:
                                    continue
                continue
            # Authors often wrap the payload: base64.b64decode('...') or
            # gzip.decompress(base64.b64decode('...')). Peel the wrappers and
            # keep the outermost decoder name so we know how to read the text.
            hint = ""
            while isinstance(value, ast.Call) and value.args:
                fn = value.func
                attr = getattr(fn, "attr", "") or getattr(fn, "id", "")
                if not hint and attr in ("b64decode", "b85decode", "decompress"):
                    hint = attr
                value = value.args[0]
            try:
                val = ast.literal_eval(value)
            except Exception:
                continue
            if hint == "decompress" and isinstance(val, bytes):
                try:
                    val = gzip.decompress(val)
                except Exception:
                    continue
            if isinstance(val, (tuple, list)):
                # Chunked payloads are either all str or all bytes; keep the type.
                if val and isinstance(val[0], bytes):
                    val = b"".join(val)
                else:
                    val = "".join(str(v) for v in val)
            if isinstance(val, bytes):
                # Some authors write the payload as bytes literals, either a
                # ready-made gzip/tar blob or the base64 text of one.
                if len(val) < 4000:
                    continue
                if val[:2] == b"\x1f\x8b":
                    yield name, "bytes", val
                    continue
                try:
                    val = val.decode("ascii")
                except Exception:
                    continue
            if not isinstance(val, str) or len(val) < 4000:
                continue
            order = ([(base64.b64decode, "b64")] if hint == "b64decode" else
                     [(base64.b85decode, "b85")] if hint == "b85decode" else
                     [(base64.b85decode, "b85"), (base64.b64decode, "b64")])
            for decoder, label in order:
                try:
                    raw = decoder(val)
                except Exception:
                    continue
                yield name, label, raw


def unwrap(raw):
    """Return (main_py_bytes, description) or None."""
    blob, outer = raw, ""
    for _ in range(2):
        if blob[:2] == b"\x1f\x8b":
            try:
                blob = gzip.decompress(blob)
                outer += "gzip+"
            except Exception:
                break
        else:
            break
    # Some authors use zlib.decompress instead of gzip. zlib streams start
    # 0x78; a bare "def " test would never see the source through them.
    if blob[:1] == b"\x78" and blob[1:2] in (b"\x01", b"\x9c", b"\xda", b"\x5e"):
        try:
            blob = zlib.decompress(blob)
            outer += "zlib+"
        except Exception:
            pass
    if blob[257:262] == b"ustar" or blob[:263].find(b"ustar") > 0:
        for mode in ("r:", "r:gz"):
            try:
                with tarfile.open(fileobj=io.BytesIO(blob), mode=mode) as tf:
                    names = tf.getnames()
                    for n in names:
                        if n.endswith("main.py"):
                            return tf.extractfile(n).read(), f"{outer}tar({','.join(names)})"
            except Exception:
                continue
        return None
    # A gzip of a bare .py is the most common shape. Requiring "def " is too
    # strict: a fully minified module can be nothing but assignments and
    # lambdas (fieldcraft's mirror_plan.py is 502KB of exactly that, and it was
    # silently skipped). Accept anything that decodes to mostly printable text.
    if b"def " in blob[:400000] or blob[:1] == b"#!":
        return blob, outer or "raw"
    sample = blob[:200000]
    if sample and sum(32 <= c < 127 or c in (9, 10, 13) for c in sample) / len(sample) > 0.92:
        return blob, (outer or "") + "text"
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("notebook")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    path = args.notebook
    if os.path.isdir(path):
        path = glob.glob(os.path.join(path, "*.ipynb"))[0]
    nb = json.load(open(path, encoding="utf-8"))
    os.makedirs(args.out, exist_ok=True)

    hits = 0
    for ci, cell in enumerate(nb["cells"]):
        if cell["cell_type"] != "code":
            continue
        src = "".join(cell["source"])

        # Some authors skip the blob entirely and write the source with an IPython
        # magic: `%%writefile main.py`. The cell body IS the file, so the AST scan
        # below would find nothing (yhay81/shop-router-0909 is written this way).
        m = re.match(r"%%writefile\s+(\S+)\s*\n", src)
        if m and m.group(1).endswith(".py"):
            body = src[m.end():].encode("utf-8")
            sha = hashlib.sha256(body).hexdigest()
            name = os.path.basename(m.group(1))
            out = os.path.join(args.out, f"cell{ci}_writefile_{name.replace('.py', '')}"
                                        f"_{sha[:8]}.py")
            open(out, "wb").write(body)
            hits += 1
            print(f"cell {ci:2d}  %%writefile {name:14s} "
                  f"{len(body):>8,} bytes  lines={body.count(chr(10).encode()) + 1}  "
                  f"sha256={sha[:16]}")
            print(f"          -> {out}")
            continue
        for name, label, raw in candidate_literals(src):
            got = unwrap(raw)
            if not got:
                continue
            body, desc = got
            sha = hashlib.sha256(body).hexdigest()
            out = os.path.join(args.out, f"cell{ci}_{name}_{label}_{sha[:8]}.py")
            open(out, "wb").write(body)
            hits += 1
            # NB: count real newlines. Inside an f-string `b'\\n'` is the two
            # characters backslash+n, which silently undercounts every file.
            n_lines = body.count(b"\n") + 1
            print(f"cell {ci:2d}  {name:16s} {label}  {desc:22s} "
                  f"{len(body):>8,} bytes  lines={n_lines:,}  sha256={sha[:16]}")
            print(f"          -> {out}")
    if not hits:
        print("no embedded archive found", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
