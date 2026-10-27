"""Run analysis layers on maps and print the results.

    python3 analyse.py --list
    python3 analyse.py ../gold/*.json ../predicted/*.json
    python3 analyse.py ../predicted/*.json --layer reachability -o ../analysis

Layers live in tools/layers/; see tools/layers/__init__.py for how to add one.
Results are written beside the maps' names in the output folder, never into the maps.
"""
import argparse
import json
from pathlib import Path

from layers import available, describe, run_map_layers
from lexicon import load


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("maps", nargs="*")
    ap.add_argument("--layer", nargs="*", default=None, help="layer names (default: all map layers)")
    ap.add_argument("--list", action="store_true", help="list the available layers")
    ap.add_argument("-o", "--outdir", default=None, help="write <map>.<layer>.json files here")
    args = ap.parse_args()
    if args.list or not args.maps:
        for d in describe():
            print(f"{d['name']:14s} {d['scope']:6s} v{d['version']}  {d['label']}\n{'':22s}lens: {d['lens']}")
        return 0
    unknown = set(args.layer or []) - set(available())
    if unknown:
        print(f"unknown layer(s): {', '.join(unknown)}; run with --list")
        return 1
    out = Path(args.outdir) if args.outdir else None
    if out:
        out.mkdir(parents=True, exist_ok=True)
    for p in args.maps:
        m = load(p)
        res = run_map_layers(m, args.layer)
        print(f"\n{Path(p).stem}  ({m.get('domain', 'radiology')})")
        for name, r in res.items():
            print(f"  [{name} v{r['version']}] " + ", ".join(f"{k}={v}" for k, v in r["summary"].items()))
            for row in r.get("rows", []):
                if "verdict" in row:
                    print(f"     - {row.get('claim', '')[:60]}: {row['verdict']}"
                          + (f"  via {' > '.join(row['unchecked_route'])}" if row.get("unchecked_route") else "")
                          + (f"\n       ! {row['note']}" if row.get("note") else ""))
                else:
                    print("     - " + ", ".join(f"{k}: {v}" for k, v in row.items()))
            if out:
                (out / f"{Path(p).stem}.{name}.json").write_text(json.dumps(r, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
