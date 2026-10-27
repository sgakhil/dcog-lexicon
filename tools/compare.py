"""Compare a predicted diagram (e.g., LLM output) with a reference (gold or seeded).

Scores each layer separately, because we expect the workflow layer to be easy
and the claims and argument layers to be where agreement and accuracy diverge.
The argument layer belongs to the argumentation lens and is scored only when the
reference map codes it.

Nodes are matched by (canonical activity, lane); edges by matched endpoints
and type; claims by their sequence of states; argument breakdowns by
(element, status) and labor.

Usage: python tools/compare.py reference.json predicted.json [--json]
"""
import argparse
import json
from collections import Counter

from lexicon import canonical_activity, domain_of, load


def f1(ref, pred):
    ref, pred = Counter(ref), Counter(pred)
    tp = sum((ref & pred).values())
    p = tp / sum(pred.values()) if pred else 0.0
    r = tp / sum(ref.values()) if ref else 0.0
    f = 2 * p * r / (p + r) if p + r else (1.0 if not ref and not pred else 0.0)
    return {"precision": round(p, 3), "recall": round(r, 3), "f1": round(f, 3),
            "missing": sorted(map(str, (ref - pred).elements())),
            "extra": sorted(map(str, (pred - ref).elements()))}


def node_key(n, dom="radiology"):
    return (canonical_activity(n["activity"], dom) or n["activity"], n["lane"])


def score(ref, pred):
    rkeys = {n["id"]: node_key(n, domain_of(ref)) for n in ref["nodes"]}
    pkeys = {n["id"]: node_key(n, domain_of(ref)) for n in pred["nodes"]}
    out = {
        "workflow.nodes": f1(rkeys.values(), pkeys.values()),
        "workflow.edges": f1(
            [(rkeys[e["from"]], rkeys[e["to"]], e["type"]) for e in ref["edges"]],
            [(pkeys[e["from"]], pkeys[e["to"]], e["type"]) for e in pred["edges"]]),
        "workflow.ai_nodes": f1([k for i, k in rkeys.items() if next(n for n in ref["nodes"] if n["id"] == i).get("is_ai")],
                                [k for i, k in pkeys.items() if next(n for n in pred["nodes"] if n["id"] == i).get("is_ai")]),
        "routing.state_paths": f1([tuple(c["states"]) for c in ref["routing"]],
                                  [tuple(c["states"]) for c in pred["routing"]]),
        "routing.unexamined_agreement": f1(
            [c["claim_source"] for c in ref["routing"] if c.get("unexamined_agreement")],
            [c["claim_source"] for c in pred["routing"] if c.get("unexamined_agreement")]),
    }
    if "argument" in ref:   # argumentation lens: scored only when the reference codes it
        out["argument.breakdowns"] = f1([(b["element"], b["status"]) for b in ref.get("argument", [])],
                                        [(b["element"], b["status"]) for b in pred.get("argument", [])])
        out["argument.labor"] = f1([l for b in ref.get("argument", []) for l in b["labor"]],
                                   [l for b in pred.get("argument", []) for l in b["labor"]])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reference")
    ap.add_argument("predicted")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    s = score(load(args.reference), load(args.predicted))
    if args.json:
        print(json.dumps(s, indent=2))
        return
    for layer, m in s.items():
        print(f"{layer:32s} F1={m['f1']:.2f}  P={m['precision']:.2f}  R={m['recall']:.2f}")
        for k in ("missing", "extra"):
            if m[k]:
                print(f"{'':34s}{k}: {m[k]}")


if __name__ == "__main__":
    main()
