"""Export diagrams as a flat event log (CSV) for process-mining tools.

One row per activity, ordered by a breadth-first walk from the entry node(s)
along all edges. Each row carries the epistemic state(s) of the claims that
touch it, so logs can be mined for routing patterns as well as workflow.

Usage: python tools/export_eventlog.py gold/*.json -o eventlog.csv
"""
import argparse
import csv
from collections import deque

from lexicon import load


def order_nodes(d):
    nodes = {n["id"]: n for n in d["nodes"]}
    adj = {}
    for e in d["edges"]:
        adj.setdefault(e["from"], []).append(e)
    queue = deque(n["id"] for n in d["nodes"] if n.get("entry"))
    seen, order, via = set(), [], {}
    while queue:
        nid = queue.popleft()
        if nid in seen:
            continue
        seen.add(nid)
        order.append(nid)
        for e in adj.get(nid, []):
            if e["to"] not in seen:
                via.setdefault(e["to"], e["type"])
                queue.append(e["to"])
    # nodes unreachable from entry (e.g., institutional sources) go last
    order += [nid for nid in nodes if nid not in seen]
    return order, via


def rows(d):
    order, via = order_nodes(d)
    nodes = {n["id"]: n for n in d["nodes"]}
    states = {}
    for c in d["routing"]:
        for nid in c.get("nodes", []):
            states.setdefault(nid, []).append(f"{c['claim_id']}:{'>'.join(c['states'])}")
    for i, nid in enumerate(order):
        n = nodes[nid]
        yield {
            "case_id": d["id"], "seq": i, "activity": n["activity"], "node_id": nid,
            "lane": n["lane"], "level": n.get("level", 0), "system": n["system"], "is_ai": n.get("is_ai", False),
            "ai_model": n.get("ai_model", ""), "ai_output": n.get("ai_output", ""),
            "reached_via": via.get(nid, "entry" if n.get("entry") else "unreached"),
            "labor": "".join(n.get("labor", [])),
            "claim_states": "|".join(states.get(nid, [])),
            "closes_claim": n.get("closes_claim", False),
        }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("-o", "--out", default="eventlog.csv")
    args = ap.parse_args()
    all_rows = [r for f in args.files for r in rows(load(f))]
    with open(args.out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(all_rows[0]))
        w.writeheader()
        w.writerows(all_rows)
    print(f"wrote {len(all_rows)} events from {len(args.files)} diagrams to {args.out}")


if __name__ == "__main__":
    main()
