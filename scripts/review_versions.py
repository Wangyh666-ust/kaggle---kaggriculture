"""Build ONE review page covering several submitted versions, selectable in the UI.

Requirement this implements. The review page used to be hard-wired to a single
submission ref, so seeing another version meant re-running with a different
argument and opening a different file. What is wanted is a page with a version
selector: pick v41 and see v41's ladder games, switch to v44 and see its.

Where the version list comes from. results/submissions.md -- the log submit.py
writes on every submission, carrying the version name, the ref and the note.
Nothing is hard-coded.

Local data is reused, missing data is fetched. Two levels of cache:
  * tmp_replays/ref-<ref>.json  records which episodes belong to a ref, so
    "have we already scanned this version" is answerable;
  * tmp_replays/ep-<eid>-summary.json holds the extracted series per episode, so
    an episode seen under any ref is never downloaded twice.
A version whose refs are all indexed needs no network at all.

The page cannot fetch by itself. The browser has no Kaggle CLI and no token, so
anything missing is fetched HERE, at build time; the page only switches between
what has been prepared. Versions in the log that were never scanned are listed
in the selector and marked as such rather than silently absent.

Usage:
  .venv/Scripts/python scripts/review_versions.py                # 最近 4 个版本
  .venv/Scripts/python scripts/review_versions.py --versions v41,v44 --scan 24
  .venv/Scripts/python scripts/review_versions.py --all-versions
"""
import argparse
import collections
import datetime
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import field_ledger as FL  # noqa: E402
import ledger_app as APP  # noqa: E402
import review_losses as RV  # noqa: E402

CACHE = RV.CACHE
LOG = os.path.join(ROOT, "results", "submissions.md")


def submissions():
    """Every submission, newest first, from the API -- the local log is a fallback.

    The API is the source of truth: it carries every ref, its date, its public
    score, and the message, whose leading token is the version name ("v37: ...").
    The log CANNOT be the source: it only started recording refs today, so the
    rows for v34..v38 carry no ref and would silently drop out of the selector.
    """
    rows = []
    try:
        for s in RV.json_from(RV.kaggle("competitions", "submissions", "kaggriculture",
                                        "--format", "json")):
            desc = (s.get("description") or "").strip()
            m = re.match(r"(v[0-9]+)", desc)
            rows.append({"version": m.group(1) if m else "?",
                         "ref": str(s["ref"]), "time": (s.get("date") or "")[:16],
                         "score": s.get("publicScore") or "", "note": desc})
    except Exception:
        rows = []
    if rows:
        return rows
    try:
        log = open(LOG, encoding="utf-8").read().split("\n")
    except OSError:
        return []
    for ln in log:
        if not ln.startswith("|") or "submitted" not in ln:
            continue
        cells = [c.strip() for c in ln.strip("|").split("|")]
        if len(cells) < 6:
            continue
        m = re.search(r"ref\s+([0-9]+)", cells[5])
        if not m:
            continue
        rows.append({"version": cells[1], "ref": m.group(1), "time": cells[0],
                     "score": "", "note": cells[5]})
    rows.reverse()
    return rows



def ref_index_path(ref):
    return os.path.join(CACHE, f"ref-{ref}.json")


def read_index(ref):
    try:
        return json.load(open(ref_index_path(ref), encoding="utf-8"))
    except (OSError, ValueError):
        return None


def ensure(ref, version, scan, n_episodes_total=None):
    """Return the list of cached games for a ref, fetching whatever is missing."""
    idx = read_index(ref)
    if idx and idx.get("episodes"):
        games = []
        for eid in idx["episodes"]:
            p = RV.summary_path(eid)
            if os.path.exists(p):
                g = json.load(open(p, encoding="utf-8"))
                g["steps"] = FL.denormalise(g["steps"])
                games.append(g)
        if games:
            print(f"  {version} ref {ref}: 复用本地 {len(games)} 局（{idx.get('scanned_at','?')} 抓的）")
            return games
        print(f"  {version} ref {ref}: 索引在但摘要缺失，重新抓")

    ids, total = RV.episode_ids(ref, scan)
    print(f"  {version} ref {ref}: 本地无数据 → 抓取最近 {len(ids)} 局"
          f"（该 ref 共 {total} 局）")
    games = []
    for n, eid in enumerate(ids, 1):
        sp = RV.summary_path(eid)
        if os.path.exists(sp):
            g = json.load(open(sp, encoding="utf-8"))
            g["steps"] = FL.denormalise(g["steps"])
            games.append(g)
            continue
        p = RV.fetch_replay(eid)
        if not p:
            print(f"    [{n}/{len(ids)}] {eid} 抓取失败")
            continue
        games.append(RV.load_replay(p, eid))
    if games:
        os.makedirs(CACHE, exist_ok=True)
        json.dump({"ref": ref, "version": version,
                   "scanned_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                   "episodes": [g["episode"] for g in games]},
                  open(ref_index_path(ref), "w", encoding="utf-8"))
    return games


def version_payload(entry, games, team):
    """Compact one version's games, normalising our seat to 0 in every game."""
    rows = []
    for g in games:
        seats = [i for i, t in enumerate(g["teams"]) if t == team]
        seat = 0 if len(seats) == 2 else (seats[0] if seats else 0)
        mine, theirs = g["rewards"][seat], g["rewards"][1 - seat]
        g["margin"] = mine - theirs
        g["opp_name"] = g["teams"][1 - seat]
        if seat == 1:
            g["steps"] = RV.swap_seats(g["steps"])
            g["rewards"] = [theirs, mine]
        rows.append(RV.compact(g, True, entry["ref"]))
    rows.sort(key=lambda r: r["margin"])
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--versions", default="", help="逗号分隔；默认取最近 N 个")
    ap.add_argument("--recent", type=int, default=4, help="默认纳入最近几个版本")
    ap.add_argument("--all-versions", action="store_true")
    ap.add_argument("--scan", type=int, default=24, help="每个 ref 抓多少局")
    ap.add_argument("--team", default=None)
    ap.add_argument("--out", default="results/ledger/ladder_review.html")
    args = ap.parse_args()

    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass

    subs = submissions()
    if not subs:
        sys.exit("results/submissions.md 里没有可用的提交记录")

    by_version = collections.OrderedDict()
    for s in subs:                      # newest first
        by_version.setdefault(s["version"], []).append(s)
    order = list(by_version)

    want = order
    if args.versions:
        want = [v.strip() for v in args.versions.split(",") if v.strip()]
    elif not args.all_versions:
        want = order[:args.recent]

    print(f"提交记录共 {len(subs)} 次、{len(order)} 个版本：{'、'.join(order)}")
    print(f"本次纳入：{'、'.join(want)}\n")

    team = args.team
    versions, index = [], []
    for ver in want:
        refs = by_version.get(ver, [])
        if not refs:
            continue
        print(f"{ver}（{len(refs)} 次提交）")
        games, subs_meta = [], []
        for s in refs:
            got = ensure(s["ref"], ver, args.scan)
            games.extend(got)
            subs_meta.append({"ref": s["ref"], "time": s["time"],
                              "n": len(got), "score": s.get("score") or ""})
            if not team:
                counts = collections.Counter(t for g in got for t in g["teams"])
                if counts:
                    cand = counts.most_common(1)[0][0]
                    # our name is the one that also appears elsewhere; take the
                    # most common across everything seen so far
                    team = team or None
        if not games:
            print(f"  {ver}: 无数据，跳过\n")
            continue
        counts = collections.Counter(t for g in games for t in g["teams"])
        # ours appears once per game; an opponent appearing in every game of
        # several refs is impossible, so the most common name is ours
        team = team or counts.most_common(1)[0][0]
        games = [g for g in games if team in g["teams"]]
        versions.append({"name": ver, "subs": subs_meta,
                         "games": version_payload(by_version[ver][0], games, team)})
        print()
        index.extend(by_version[ver])

    if not versions:
        sys.exit("没有拿到任何版本的数据")

    print(f"我们的队名：{team}")
    for v in versions:
        g = v["games"]
        w = sum(1 for x in g if x["margin"] > 0)
        print(f"  {v['name']}: {len(g)} 局  {w} 胜 / {len(g)-w} 负"
              f"  ref {'、'.join(s['ref'] for s in v['subs'])}")
    print(f"  （未纳入的版本：{'、'.join(v for v in order if v not in want)}）")

    # Every submitted version goes in the selector; ones with no local data are
    # listed as such rather than silently missing, so the absence is legible.
    have = {v["name"] for v in versions}
    allv = [{"name": v, "have": v in have,
             "subs": [{"ref": s["ref"], "time": s["time"]} for s in by_version[v]]}
            for v in order]

    out = args.out if os.path.isabs(args.out) else os.path.join(ROOT, args.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    html = APP.render_versions(versions, allv, [f"我们（{team}）", "对手"])
    open(out, "w", encoding="utf-8").write(html)
    print(f"已写入 {out}  ({os.path.getsize(out):,} bytes) —— 含 {len(versions)} 个版本")


if __name__ == "__main__":
    main()
