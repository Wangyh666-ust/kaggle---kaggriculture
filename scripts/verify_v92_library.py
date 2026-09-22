"""Verify a recorded v9/2 PREDICT library against the agent's own decoder.

Checks, in order:

  1. structural — every one of the 64 shop pairs decodes through
     `_v92_p_pair` of the CANDIDATE file (versions/main_v25_ownlib.py) into
     `[(-1, {(tick, item): units})]` with sane ticks / items / quantities,
     and equals the library the recorder independently decoded.
  2. drop-in — the SAME new blob pasted into main.py (monkey-patched
     `_V92_P_BLOB` / `_V92_P_INDEX`, caches cleared) decodes to the identical
     streams, i.e. the stock decoder reads the new library unchanged.
  3. offline leave-one-out quality — replay each episode's observed rival
     ticks, run the real `_v92_p_forecast` every few turns on the library
     WITHOUT that episode's own stream, and measure how often the single
     top-scoring stream correctly predicts a >=4-unit dump of
     MILK / WOOL / STRAWBERRY in the next two turns.  Old library vs new.

Usage:
  .venv/Scripts/python scripts/verify_v92_library.py
  .venv/Scripts/python scripts/verify_v92_library.py --candidate versions/main_v25_ownlib.py
"""
import argparse
import collections
import glob
import importlib.util
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import record_v92_library as rec  # noqa: E402

PAIR_NAMES = rec.PAIR_NAMES
ITEMS = rec.ITEMS
USE = ("MILK", "WOOL", "STRAWBERRY")
K = 4


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def all_pairs():
    return [(a, b) for a in PAIR_NAMES for b in PAIR_NAMES]


# ---------------------------------------------------------------------------
# 1 + 2: decoding
# ---------------------------------------------------------------------------
def check_structure(mod, label):
    streams = events = 0
    bad = []
    per_pair = {}
    for a, b in all_pairs():
        got = mod._v92_p_pair((a, b))
        n_ev = 0
        for ep, ev in got:
            if ep != -1 or not isinstance(ev, dict):
                bad.append(f"{a}|{b}: stream is not (-1, dict)")
                continue
            for (tick, item), units in ev.items():
                n_ev += 1
                if not (0 <= tick < 720) or not (0 <= item <= 4) or not (1 <= units <= 255):
                    bad.append(f"{a}|{b}: bad event {(tick, item, units)}")
                    break
        streams += len(got)
        events += n_ev
        per_pair[(a, b)] = (len(got), n_ev)
    print(f"  [{label}] {streams} streams / {events} events over 64 pairs, "
          f"{len(bad)} malformed")
    return per_pair, streams, events, bad


def check_dropin(cand_blob, cand_index, cand_per_pair):
    """Paste the new blob into the stock main.py and decode again."""
    import zlib
    import base64
    main = load_module(os.path.join(ROOT, "main.py"), "main_stock_v92verify")
    main._V92_P_BLOB = cand_blob
    main._V92_P_INDEX = cand_index
    main._V92_P_LIB = None
    main._V92_P_RAW = None
    per_pair, streams, events, bad = check_structure(main, "main.py + new blob")
    assert per_pair == cand_per_pair, "patched main.py decoded a different library"
    raw = zlib.decompress(base64.b85decode(main._V92_P_BLOB))
    for a, b in all_pairs():
        ref = rec.decode_pair(raw, cand_index, a, b)
        got = main._v92_p_pair((a, b))
        assert ref == got, f"independent decoder disagrees on {a}|{b}"
    print("  [main.py + new blob] identical to candidate, independent decoder agrees")
    return streams, events


# ---------------------------------------------------------------------------
# 3: offline leave-one-out prediction quality
# ---------------------------------------------------------------------------
def score_events(cands, seen, step):
    """The scoring loop of _v92_p_forecast (kept in sync with main.py).

    `cands` is a list of (key, event_dict); returns them sorted best-first.
    """
    lo = step - 240
    recent = [(tt, i) for (tt, i) in seen if tt >= lo]
    scored = []
    for key, ev in cands:
        m = f = 0
        for (tt, i) in ev:
            if lo <= tt < step - 1:
                if (tt, i) in seen or (tt - 1, i) in seen or (tt + 1, i) in seen:
                    m += 1
                else:
                    f += 1
        miss = sum(1 for (tt, i) in recent
                   if (tt, i) not in ev and (tt - 1, i) not in ev and (tt + 1, i) not in ev)
        scored.append((m - 0.5 * f - 0.5 * miss, key))
    scored.sort(key=lambda x: -x[0])
    return scored


def eval_library(per_stream, episodes, stride, label, held_out=False):
    """per_stream: {(a,b): [(stream_key, {(t,i): q}), ...]}

    held_out=True drops each episode's own stream (leave-one-out) — this is the
    only honest way to test a library recorded FROM that episode.
    """
    fires = hits = misses_fire = 0   # fires = predictions made, hits = GT>=4 followed
    opportunities = 0                # turns where GT dump existed in the next 2 turns
    missing_gt = 0                   # GT dumps not preceded by a fire (recall losses)
    top_scores = []
    for ep in episodes:
        seen = {(t, i): q for (t, i, q) in ep["events"]}
        cands = [(key, ev) for key, ev in per_stream.get(tuple(ep["pair"]), [])
                 if not (held_out and key == ep["id"])]
        if not cands:
            continue
        future = collections.defaultdict(int)
        for (t, i, q) in ep["events"]:
            future[(t, i)] += q
        for step in range(150, 719, stride):
            stage = {k: v for k, v in seen.items() if k[0] < step}
            if not stage:
                continue
            ranked = score_events(cands, stage, step)
            if not ranked:
                continue
            top_scores.append(ranked[0][0])
            ev = dict(cands)[ranked[0][1]]
            votes = {item: ev.get((step + 1, ITEMS.index(item)), 0)
                            + ev.get((step + 2, ITEMS.index(item)), 0) >= K
                     for item in USE}
            gt = {item: future.get((step + 1, ITEMS.index(item)), 0)
                        + future.get((step + 2, ITEMS.index(item)), 0) >= K
                  for item in USE}
            fired = [item for item in USE if votes[item]]
            real = [item for item in USE if gt[item]]
            opportunities += len(real)
            for item in fired:
                fires += 1
                if gt[item]:
                    hits += 1
                else:
                    misses_fire += 1
            for item in real:
                if item not in fired:
                    missing_gt += 1
    prec = hits / fires if fires else float("nan")
    rec_ = hits / opportunities if opportunities else float("nan")
    print(f"  [{label}] samplings {len(top_scores)}  fires {fires}  hit {hits} "
          f"(precision {prec:.1%})  missed GT dumps {missing_gt}/{opportunities} "
          f"(recall {rec_:.1%})  mean top score "
          f"{sum(top_scores) / len(top_scores) if top_scores else 0:.1f}")
    return dict(samplings=len(top_scores), fires=fires, hits=hits,
                false_fires=misses_fire, opportunities=opportunities,
                missed=missing_gt,
                precision=(prec if fires else None), recall=(rec_ if opportunities else None),
                mean_top_score=(sum(top_scores) / len(top_scores)) if top_scores else None)


def library_from_dir(path):
    """Independent decoder of the blob currently embedded in a py file."""
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    import base64
    import re
    import zlib
    blob = re.search(r"^_V92_P_BLOB = '(.*)'", src, re.M).group(1)
    index = eval(re.search(r"^_V92_P_INDEX = (\[.*?\])", src, re.M).group(1))
    raw = zlib.decompress(base64.b85decode(blob))
    out = {}
    for a in PAIR_NAMES:
        for b in PAIR_NAMES:
            out[(a, b)] = rec.decode_pair(raw, index, a, b)
    return out


def episodes_with_events(dirs, our_name, limit=None):
    """Everything the offline check needs, per episode."""
    rows = []
    for d in dirs:
        for path in sorted(glob.glob(os.path.join(ROOT, d, "*.json"))):
            try:
                eid, opponent, pair, events, _ = rec.record_episode(path, our_name)
            except Exception:
                continue
            if pair is None or not events:
                continue
            rows.append(dict(id=eid, pair=list(pair), events=events, opponent=opponent))
    if limit and len(rows) > limit:
        rows = rows[::max(1, len(rows) // limit)][:limit]
    return rows


def as_streams(rows):
    """rows -> {(a,b): [(episode_id, {(tick, item): qty}), ...]}"""
    out = collections.defaultdict(list)
    for row in rows:
        ev = {(t, i): q for (t, i, q) in row["events"]}
        out[tuple(row["pair"])].append((row["id"], ev))
    return out


def forecast_fidelity(mod, streams, rows):
    """Call the SHIPPED _v92_p_forecast and confirm it agrees with score_events."""
    checked = 0
    for row in rows:
        seen = {(t, i): q for (t, i, q) in row["events"]}
        for step in (300, 450, 600):
            stage = {"obs": {k: v for k, v in seen.items() if k[0] < step}}
            if not stage:
                continue
            obs = {"step": step, "town": {"unlocked_shops": list(row["pair"])}}
            try:
                got = mod._v92_p_forecast(obs, stage)
            except Exception as exc:
                raise AssertionError(f"_v92_p_forecast raised: {exc!r}")
            assert isinstance(got, list) and all(isinstance(e, dict) for e in got)
            if not got:
                continue
            # rank the module's own candidate list: same order as the decoder
            # produced, so a tie can only break the same way it does in main.py
            cands = [(i, ev) for i, (_, ev) in enumerate(mod._v92_p_pair(tuple(row["pair"])))]
            ranked = score_events(cands, stage["obs"], step)
            assert ranked, "score_events empty but forecast returned a stream"
            assert got[0] == dict(cands)[ranked[0][1]], (
                f"shipped forecast != re-implemented scorer at step {step}")
            checked += 1
    return checked


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", default="versions/main_v25_ownlib.py")
    ap.add_argument("--blob-module", default="results/v92_ownlib_blob.py")
    ap.add_argument("--out", default="results/v92_verify.json")
    ap.add_argument("--dirs", nargs="*", default=["replays_v21", "replays_v23", "replays_v24"])
    ap.add_argument("--our-name", default=rec.OUR_NAME)
    ap.add_argument("--eval-episodes", type=int, default=120)
    ap.add_argument("--eval-stride", type=int, default=8)
    ap.add_argument("--skip-eval", action="store_true")
    args = ap.parse_args()

    cand_path = os.path.join(ROOT, args.candidate)
    print(f"candidate: {args.candidate}")
    cand = load_module(cand_path, "cand_v92verify")
    cand_per_pair, cand_streams, cand_events, bad = check_structure(cand, "candidate")
    assert not bad, bad[:5]
    streams, events = check_dropin(cand._V92_P_BLOB, cand._V92_P_INDEX, cand_per_pair)
    assert (streams, events) == (cand_streams, cand_events)

    report = dict(candidate=args.candidate, streams=streams, events=events,
                  pairs_covered=sum(1 for v in cand_per_pair.values() if v[0]),
                  per_pair={f"{a}|{b}": dict(streams=cand_per_pair[(a, b)][0],
                                             events=cand_per_pair[(a, b)][1])
                            for a, b in all_pairs()})
    if args.skip_eval:
        with open(os.path.join(ROOT, args.out), "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=1)
        print("saved ->", args.out)
        return

    all_rows = episodes_with_events(args.dirs, args.our_name)
    new_streams = as_streams(all_rows)
    sample = all_rows[::max(1, len(all_rows) // args.eval_episodes)][:args.eval_episodes]
    print(f"offline check: {len(sample)}/{len(all_rows)} episodes sampled, stride "
          f"{args.eval_stride}, leave-one-out for the new library")
    n_fid = forecast_fidelity(cand, new_streams, sample[:8])
    print(f"  [candidate] shipped _v92_p_forecast agrees with the re-implemented "
          f"scorer on {n_fid} samplings")

    report["new"] = eval_library(new_streams, sample, args.eval_stride,
                                 "new (our library, leave-one-out)", held_out=True)
    old_streams = {}
    for (a, b), got in library_from_dir(os.path.join(ROOT, "main.py")).items():
        old_streams[(a, b)] = [(f"old{i}", ev) for i, (_, ev) in enumerate(got)]
    report["old"] = eval_library(old_streams, sample, args.eval_stride,
                                 "old (online library)")

    with open(os.path.join(ROOT, args.out), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)
    print("saved ->", args.out)


if __name__ == "__main__":
    main()
