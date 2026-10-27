"""Reachability: can a claim travel from where it starts to where it closes without
passing through an independent check?

Lens: distributed cognition and epistemic trust. A claim that can reach sign-off by
a route with no independent check is closed on trust alone; whether that route was
the one taken, and how often, is the routing question.

Rules
- A claim starts at its steps that no other step of the claim leads to.
- It ends at its steps marked as closing the claim; if none is marked and the claim
  is closed, at its steps that lead to no other step of the claim.
- Independent checks are the activities listed under "check_activities" in the
  setting's vocabulary (domains/<name>.json). Edit that list to change the lens.
- The search uses every link in the map, so a route through steps outside the
  claim still counts.
"""
from collections import deque

NAME = "reachability"
LABEL = "Can a claim reach closure without an independent check?"
SCOPE = "map"
VERSION = "1.0"
LENS = "Distributed cognition; epistemic trust as routing"


def _unchecked_path(starts, ends, nxt, is_check):
    """Shortest route from any start to any end that avoids check steps, or None."""
    q = deque([[s] for s in starts if not is_check(s)])
    seen = set(p[0] for p in q)
    while q:
        path = q.popleft()
        if path[-1] in ends:
            return path
        for t in nxt.get(path[-1], []):
            if t not in seen and not is_check(t):
                seen.add(t)
                q.append(path + [t])
    return None


def _reachable(start, nxt):
    seen, q = set(), deque([start])
    while q:
        for t in nxt.get(q.popleft(), []):
            if t not in seen:
                seen.add(t)
                q.append(t)
    return seen


def run(m, vocab):
    checks = set(vocab.get("check_activities", []))
    nodes = {n["id"]: n for n in m["nodes"]}
    nxt = {}
    for e in m["edges"]:
        nxt.setdefault(e["from"], []).append(e["to"])
    is_check = lambda i: nodes.get(i, {}).get("activity") in checks

    rows, marks = [], []
    for i in nodes:
        if is_check(i):
            marks.append({"on": "node", "id": i, "tag": "check", "level": "info"})
    for c in m["routing"]:
        mine = [i for i in c.get("nodes", []) if i in nodes]
        inside = set(mine)
        ends = [i for i in mine if nodes[i].get("closes_claim")]
        if not ends and c.get("closed"):
            ends = [i for i in mine if not any(e["from"] == i and e["to"] in inside for e in m["edges"])]
        # a claim starts at its earliest steps: those no other step of the claim can reach
        reach = {i: _reachable(i, nxt) for i in mine}
        starts = [i for i in mine if i not in ends and not any(i in reach[j] for j in mine if j != i)]
        starts = starts or [i for i in mine if i not in ends][:1]
        on_claim = [i for i in mine if is_check(i)]
        if not c.get("closed") or not ends:
            verdict, path = "left open", None
        else:
            path = _unchecked_path(starts, set(ends), nxt, is_check)
            verdict = "can close unchecked" if path else "every route passes a check"
        note = ""
        if c.get("unexamined_agreement") and verdict == "every route passes a check":
            note = "coded as unexamined agreement, but every route passes a check: review the coding"
        if (not c.get("unexamined_agreement") and c.get("claim_source") in ("ai", "hybrid")
                and verdict == "can close unchecked" and not on_claim):
            note = "closes with no check on its steps but is not coded as unexamined agreement: review the coding"
        rows.append({"claim": c["claim"], "claim_id": c["claim_id"], "verdict": verdict,
                     "checks_on_claim": [nodes[i]["activity"] for i in on_claim],
                     "unchecked_route": [nodes[i]["activity"] for i in path] if path else [], "note": note})
        if path:
            marks.append({"on": "claim", "id": c["claim_id"], "tag": "can close unchecked", "level": "warn"})
            for a, b in zip(path, path[1:]):
                marks.append({"on": "edge", "from": a, "to": b, "tag": "", "level": "warn"})
    closed = [r for r in rows if r["verdict"] != "left open"]
    return {
        "summary": {"claims": len(rows), "closed": len(closed),
                    "can_close_unchecked": sum(r["verdict"] == "can close unchecked" for r in rows),
                    "every_route_checked": sum(r["verdict"] == "every route passes a check" for r in rows),
                    "coding_to_review": sum(bool(r["note"]) for r in rows)},
        "rows": rows, "marks": marks}
