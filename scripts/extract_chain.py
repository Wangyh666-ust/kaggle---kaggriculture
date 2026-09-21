"""Extract the agent source embedded in the ahmedberatozer V49..V55 chain notebooks.

Two encodings appear on that chain:
  - V49/V50/V51: `SOURCE_BYTES = b''.join((...))`  literal byte chunks
  - V52/V53/V54/V55: `SOURCE_BLOB = ''.join((...))` base85, then zlib decompress
Every notebook pins `EXPECTED_MAIN_SHA256` and asserts it, so we simply execute
the payload cell with `WORKDIR` bound to the notebook's own folder: the cell's
own assertion verifies the bytes and writes main.py.

Usage: .venv/Scripts/python scripts/extract_chain.py [v49 v50 ...]
"""
import json
import os
import sys
from pathlib import Path

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
KERNELS = os.path.join(ROOT, "kernels")
NAMES = ["v49", "v50", "v51", "v52", "v53", "v54", "v55"]


def payload_cell(nb_path):
    with open(nb_path, encoding="utf-8") as fh:
        nb = json.load(fh)
    for c in nb["cells"]:
        src = "".join(c["source"])
        if "EXPECTED_MAIN_SHA256" in src and "SOURCE_" in src:
            return src
    raise RuntimeError(f"no payload cell in {nb_path}")


def markdown(nb_path):
    with open(nb_path, encoding="utf-8") as fh:
        nb = json.load(fh)
    return "\n\n".join("".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "markdown")


def manifest(short):
    for d in sorted(os.listdir(KERNELS)):
        if d.startswith("kaggriculture-" + short) and os.path.isdir(os.path.join(KERNELS, d)):
            for f in os.listdir(os.path.join(KERNELS, d)):
                if f.endswith(".ipynb"):
                    return os.path.join(KERNELS, d, f)
    raise RuntimeError(f"notebook folder for {short} not found under kernels/")


def extract(short):
    nb = manifest(short)
    workdir = os.path.dirname(nb)
    src = payload_cell(nb)
    g = {"__name__": "__main__", "WORKDIR": Path(workdir)}
    exec(compile(src, nb, "exec"), g)  # cell's own sha256 assert runs here
    data = g["SOURCE_BYTES"]
    out = os.path.join(workdir, "main.py")
    with open(out, "wb") as fh:
        fh.write(data)
    md = os.path.join(workdir, "NOTES.md")
    with open(md, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(markdown(nb))
    print(f"  {short}: {len(data):,} bytes -> {os.path.relpath(out, ROOT)}")


def main():
    wanted = sys.argv[1:] or NAMES
    for short in wanted:
        extract(short)


if __name__ == "__main__":
    main()
