"""Labor by screen: where does argumentation labor happen, and does it
follow the AI?

Lens: argumentation (Toulmin) with argumentation labor. Requires the argumentation coding
lens, because it reads the labor codes coded on each step.

Rules
- Counts the labor codes (R, C, A, I) on each step, by screen lane and by the lane's
  role (queue, work, record) in the setting's vocabulary.
- A step counts as "after an AI step" if some AI step leads to it through the map's
  links; the share of labor after AI shows how much argumentation labor the AI sets off.
"""
from collections import Counter, deque

NAME = "labor_by_screen"
LABEL = "Where is argumentation labor done, and does it follow the AI?"
SCOPE = "map"
VERSION = "1.0"
LENS = "Argumentation labor (Toulmin)"
REQUIRES = ["argumentation"]


def _after_ai(m):
    nxt = {}
    for e in m["edges"]:
        nxt.setdefault(e["from"], []).append(e["to"])
    seen, q = set(), deque(n["id"] for n in m["nodes"] if n.get("is_ai"))
    while q:
        for t in nxt.get(q.popleft(), []):
            if t not in seen:
                seen.add(t)
                q.append(t)
    return seen


def run(m, vocab):
    lanes, after = vocab["lanes"], _after_ai(m)
    names = {k: v.split(":")[0] for k, v in vocab["labor"].items()}
    by_lane, by_role, marks, total, post = {}, Counter(), [], 0, 0
    for n in m["nodes"]:
        codes = n.get("labor", [])
        if not codes:
            continue
        lane = lanes.get(n["lane"], {})
        by_lane.setdefault(n["lane"], Counter()).update(codes)
        by_role[lane.get("role", "?")] += len(codes)
        total += len(codes)
        post += len(codes) if n["id"] in after else 0
        marks.append({"on": "node", "id": n["id"], "tag": "+".join(codes), "level": "info"})
    rows = [{"screen": f"{lanes[k]['title']} ({k})" if k in lanes else k, "role": lanes.get(k, {}).get("role", ""),
             **{names[c]: by_lane.get(k, Counter())[c] for c in names}} for k in lanes if k in by_lane]
    if not total:
        return {"summary": {"labor_codes": 0, "note": "no labor coded on any step"}, "rows": [], "marks": []}
    return {"summary": {"labor_codes": total,
                        **{f"in_{r}_screens": c for r, c in sorted(by_role.items())},
                        "share_after_an_AI_step": f"{round(100 * post / total)}%"},
            "rows": rows, "marks": marks}
