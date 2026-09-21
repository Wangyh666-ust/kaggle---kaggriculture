"""Extract the agents embedded in the public reference notebooks into opponents/.

Each notebook hides its submission source in a different way (a %%writefile
cell, a gzip tar in base64, an lzma/zlib payload in base85, a base64 blob, or a
literal source string). This script replays those decodings and writes the
result under opponents/<short-name>/, which is git-ignored (local testing only).

Usage: .venv/Scripts/python scripts/extract_opponents.py
"""
import ast
import base64
import io
import json
import lzma
import os
import re
import sys
import tarfile
import zlib

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "opponents")


def cells(path):
    with open(path, encoding="utf-8") as fh:
        nb = json.load(fh)
    return ["".join(c["source"]) for c in nb["cells"]]


def cell(path, index):
    return cells(path)[index]


def write(short, name, data, mode="wb"):
    d = os.path.join(OUT, short)
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, name)
    if mode == "wb":
        with open(p, "wb") as fh:
            fh.write(data)
    else:
        with open(p, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(data)
    print(f"    wrote opponents/{short}/{name} ({len(data):,} chars)")


def b64(text, pattern):
    m = re.search(pattern, text, re.S)
    if not m:
        raise RuntimeError(f"pattern not found: {pattern}")
    return re.sub(r"\s+", "", m.group(1))


# ---------------------------------------------------------------- salem (V16-RC5)
def salem():
    src = cell(os.path.join(ROOT, "kernels/salem2900/kaggriculture-2900.ipynb"), 13)
    lines = src.split("\n")
    assert lines[0].startswith("%%writefile"), lines[0]
    body = "\n".join(lines[1:])
    write("salem", "main.py", body, "w")


# ------------------------------------------------- pilkwang (tar.gz inside base64)
def pilkwang():
    src = cell(os.path.join(ROOT, "kernels/pilkwang_kaggriculture-structured-economic-policy/"
                                  "kaggriculture-structured-economic-policy.ipynb"), 3)
    payload = base64.b64decode(
        b64(src, r"archive_bytes = base64\.b64decode\('([A-Za-z0-9+/=\s]+)'"))
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as tar:
        for member in tar.getmembers():
            write("pilkwang", member.name, tar.extractfile(member).read())


# --------------------------------------------- prvsiyan (lzma + base85 in one cell)
def prvsiyan():
    src = cell(os.path.join(ROOT, "kernels/prvsiyan_kaggriculture-frontier-the-soil-remembers-rain/"
                                  "kaggriculture-frontier-the-soil-remembers-rain.ipynb"), 3)
    source = lzma.decompress(base64.b85decode(b64(src, r"base64\.b85decode\('([^']+)'\)")))
    write("prvsiyan", "main.py", source)
    lic = re.search(r"LICENSE_TEXT\s*=\s*('.*?')\n", src, re.S)
    if lic:
        write("prvsiyan", "LICENSE.txt", ast.literal_eval(lic.group(1)), "w")


# ------------------------------------------------- reyhan (zlib + base85, cell 0)
def reyhan():
    src = cell(os.path.join(ROOT, "kernels/reyhanksatria_kaggriculture-dynamic-route-agent/"
                                  "kaggriculture-dynamic-route-agent.ipynb"), 0)
    raw = zlib.decompress(base64.b85decode(b64(src, r'agent_b85\s*=\s*"([^"]+)"')))
    write("reyhan", "main.py", raw)


# --------------------------------------------------- guru (base64 + zlib _PAYLOAD)
def guru():
    src = cell(os.path.join(ROOT, "kernels/guruprasaathas111_kaggriculture-master-engine-v3/"
                                  "kaggriculture-master-engine-v3.ipynb"), 5)
    payload = base64.b64decode(b64(src, r"_PAYLOAD\s*=\s*'([A-Za-z0-9+/=\s]+)'"))
    source = zlib.decompress(payload).replace(b"\r\n", b"\n")
    import hashlib
    expected = "9d63494603f88219857a3101d7dc19cc750ded04e5886732ee428580326967d9"
    got = hashlib.sha256(source).hexdigest()
    assert got == expected, f"guru SHA-256 mismatch: {got}"
    print(f"    guru SHA-256 verified ({got[:12]}...)")
    write("guru", "main.py", source)


# ------------------------------------- tetsutani (literal source string in a dict)
def tetsutani():
    src = cell(os.path.join(ROOT, "kernels/tetsutani_adaptive-farming-strategy-for-kaggriculture/"
                                  "adaptive-farming-strategy-for-kaggriculture.ipynb"), 3)
    idx = src.index("TOP_AGENT_FILES = ")
    tree = ast.parse(src[idx:])
    node = tree.body[0]
    assert isinstance(node, ast.Assign) and node.targets[0].id == "TOP_AGENT_FILES"
    files = ast.literal_eval(node.value)
    for name, text in files.items():
        write("tetsutani", name, text, "w")


EXTRACTORS = {
    "salem": salem,
    "pilkwang": pilkwang,
    "prvsiyan": prvsiyan,
    "reyhan": reyhan,
    "guru": guru,
    "tetsutani": tetsutani,
}


def main():
    wanted = sys.argv[1:] or list(EXTRACTORS)
    for name in wanted:
        print(f"  {name}:")
        EXTRACTORS[name]()


if __name__ == "__main__":
    main()
