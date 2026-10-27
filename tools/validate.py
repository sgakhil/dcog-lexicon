"""Validate diagram files against the schema and controlled vocabulary.

Usage: python tools/validate.py gold/*.json
"""
import sys

from lexicon import load, notes, validate


def main(paths):
    failed = 0
    for p in paths:
        d = load(p)
        errs = validate(d)
        for n in ([] if errs else notes(d)):
            print(f"note {p}: {n}")
        if errs:
            failed += 1
            print(f"FAIL {p}")
            for e in errs:
                print(f"   - {e}")
        else:
            print(f"ok   {p}")
    print(f"\n{len(paths) - failed}/{len(paths)} valid")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
