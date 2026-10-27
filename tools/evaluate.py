"""Score every predicted diagram against its answer key and summarise by layer.

Matches files by name: answers/<name>.json  <->  predicted/<name>.json

Usage:
    python3 evaluate.py ../synthetic/answers ../predicted
    python3 evaluate.py ../synthetic/answers ../predicted -o ../results.csv
"""
import argparse
import csv
import re
from pathlib import Path
from statistics import mean

from compare import score
from lexicon import load

LAYERS = ["workflow.nodes", "workflow.edges", "workflow.ai_nodes", "routing.state_paths",
          "routing.unexamined_agreement", "argument.breakdowns", "argument.labor"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("answers")
    ap.add_argument("predicted")
    ap.add_argument("-o", "--out", default=None, help="optional CSV of per-note scores")
    args = ap.parse_args()

    rows = []
    for a in sorted(Path(args.answers).glob("*.json")):
        p = Path(args.predicted) / a.name
        if not p.exists():
            print(f"no prediction for {a.name} (run extract.py on its note)")
            continue
        s = score(load(a), load(p))
        trap = (re.search(r"_(none|agreement_looks_checked|implicit_doubt|unresolved_flag)_v\d+$", a.stem)
                or [None, "n/a"])[1]
        rows.append({"note": a.stem, "trap": trap, **{k: s[k]["f1"] for k in LAYERS}})
    if not rows:
        print("nothing to score")
        return 1

    print(f"\nScored {len(rows)} notes. Mean F1 by layer (1.00 = matches the answer key):\n")
    for k in LAYERS:
        print(f"  {k:32s} {mean(r[k] for r in rows):.2f}")
    traps = sorted({r["trap"] for r in rows})
    if len(traps) > 1:
        print("\nBy trap (routing.state_paths / routing.unexamined_agreement):")
        for t in traps:
            sub = [r for r in rows if r["trap"] == t]
            print(f"  {t:28s} n={len(sub):<3d} {mean(r['routing.state_paths'] for r in sub):.2f} / "
                  f"{mean(r['routing.unexamined_agreement'] for r in sub):.2f}")
    if args.out:
        with open(args.out, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        print(f"\nper-note scores written to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
