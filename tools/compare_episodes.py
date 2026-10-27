"""Compare two episodes: how do two maps differ? (No score: this is not draft checking.)

Same setting  - steps only in one map, claim paths, AI position, escalation levels,
                hand-offs between people and AI, and the analysis layers side by side.
Across settings - step names differ, so the comparison uses what the settings share:
                argumentation labor (argumentation lens) by screen role and kind.

    python3 compare_episodes.py ../gold/vignette2_decision_support.json ../gold/vignette3_second_opinion.json
    python3 compare_episodes.py ../examples/legal_episode_synthetic.json ../examples/dev_episode_illustrative.json
"""
import argparse
import json
from collections import Counter

from layers import run_map_layers
from lexicon import domain, domain_of, lenses_of, load, vocab

STATE = {"provisional_acceptance": "accept", "validation": "validate", "consultation": "consult", "deferral": "defer"}


def _key(n):
    return (n["activity"], n["lane"])


def _handoffs(m):
    ai = {n["id"]: bool(n.get("is_ai")) for n in m["nodes"]}
    return sum(1 for e in m["edges"] if e["from"] in ai and e["to"] in ai and ai[e["from"]] != ai[e["to"]])


def _claims(m):
    return [{"claim": c["claim"], "path": " → ".join(STATE.get(s, s) for s in c["states"]),
             "closed": c.get("closed", False), "unexamined": bool(c.get("unexamined_agreement"))} for c in m["routing"]]


def _labor(m):
    """Labor codes by screen role and kind, plus the share after an AI step (from the labor_by_screen layer)."""
    if "argumentation" not in lenses_of(m):
        return None
    lanes = vocab(domain_of(m))["lanes"]
    by_role = Counter()
    for n in m["nodes"]:   # labor placed on steps tells us where it happened
        for c in n.get("labor", []):
            by_role[lanes.get(n["lane"], {}).get("role", "?")] += 1
    kinds = Counter(l for b in m.get("argument", []) for l in b["labor"])   # labor the argument layer records
    res = run_map_layers(m, ["labor_by_screen"]).get("labor_by_screen", {})
    return {"by_role": dict(by_role), "by_kind": dict(kinds), "total": sum(kinds.values()),
            "placed_on_steps": sum(by_role.values()),
            "after_ai": res.get("summary", {}).get("share_after_an_AI_step", "–")}


def compare(a, b):
    da, db = domain_of(a), domain_of(b)
    out = {"a": {"title": a.get("title", ""), "domain": domain(da)["title"]},
           "b": {"title": b.get("title", ""), "domain": domain(db)["title"]},
           "same_setting": da == db, "marks_a": [], "marks_b": [], "facts": [], "sentences": []}
    la, lb = _labor(a), _labor(b)
    labor_kinds = vocab(da)["labor"]
    out["labor"] = {"a": la, "b": lb, "kinds": {k: v.split(":")[0] for k, v in labor_kinds.items()}}

    if not out["same_setting"]:
        out["mode"] = "labor across settings"
        if la is None or lb is None:
            missing = "A" if la is None else "B"
            out["sentences"].append(f"Map {missing} was coded without the argumentation lens, so its labor cannot be compared.")
            return out
        kinds = out["labor"]["kinds"]
        for k, name in kinds.items():
            x, y = la["by_kind"].get(k, 0), lb["by_kind"].get(k, 0)
            if x != y:
                out["sentences"].append(f"{name} labor: {x} in A, {y} in B.")
        for role in ("queue", "work", "record"):
            x, y = la["by_role"].get(role, 0), lb["by_role"].get(role, 0)
            if x or y:
                out["sentences"].append(f"Labor placed on {role} screens: {x} in A, {y} in B.")
        if not la["placed_on_steps"] or not lb["placed_on_steps"]:
            out["sentences"].append("One map records labor only in its argument layer, not on steps, so where the labor happened can be compared only in part.")
        else:
            out["sentences"].append(f"Labor after an AI step: {la['after_ai']} in A, {lb['after_ai']} in B.")
        return out

    out["mode"] = "episodes in one setting"
    ka, kb = Counter(_key(n) for n in a["nodes"]), Counter(_key(n) for n in b["nodes"])
    only_a, only_b = ka - kb, kb - ka
    left_a, left_b = Counter(only_a), Counter(only_b)
    for n in a["nodes"]:
        if left_a[_key(n)] > 0:
            left_a[_key(n)] -= 1
            out["marks_a"].append({"on": "node", "id": n["id"], "tag": "only in A", "level": "diff"})
    for n in b["nodes"]:
        if left_b[_key(n)] > 0:
            left_b[_key(n)] -= 1
            out["marks_b"].append({"on": "node", "id": n["id"], "tag": "only in B", "level": "diff"})
    shared = sum((ka & kb).values())
    lv = lambda m: max((n.get("level", 0) for n in m["nodes"]), default=0)
    out["facts"] = [
        ["Steps", len(a["nodes"]), len(b["nodes"])],
        ["Steps shared with the other map", shared, shared],
        ["AI position", a.get("ai_position", "").replace("_", " "), b.get("ai_position", "").replace("_", " ")],
        ["Escalation levels below the ordinary path", lv(a), lv(b)],
        ["Hand-offs between person and AI", _handoffs(a), _handoffs(b)],
        ["Claims closed on unexamined agreement", sum(c["unexamined"] for c in _claims(a)), sum(c["unexamined"] for c in _claims(b))],
    ]
    out["claims"] = {"a": _claims(a), "b": _claims(b)}
    ra = run_map_layers(a, ["reachability"]).get("reachability", {})
    rb = run_map_layers(b, ["reachability"]).get("reachability", {})
    out["reachability"] = {"a": [[r["claim"], r["verdict"]] for r in ra.get("rows", [])],
                           "b": [[r["claim"], r["verdict"]] for r in rb.get("rows", [])]}
    names = lambda c: ", ".join(sorted({f"{k[0]} ({k[1]})" for k in c.elements()}))
    if only_a:
        out["sentences"].append(f"Only in A: {names(only_a)}.")
    if only_b:
        out["sentences"].append(f"Only in B: {names(only_b)}.")
    ua, ub = out["facts"][5][1], out["facts"][5][2]
    if ua != ub:
        out["sentences"].append(f"{'A' if ua > ub else 'B'} has more claims closed on agreement with nothing independent checked ({max(ua, ub)} against {min(ua, ub)}).")
    if lv(a) != lv(b):
        out["sentences"].append(f"{'A' if lv(a) > lv(b) else 'B'} escalates further ({max(lv(a), lv(b))} level(s) against {min(lv(a), lv(b))}).")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    r = compare(load(args.a), load(args.b))
    if args.json:
        print(json.dumps(r, indent=2, ensure_ascii=False))
        return
    print(f"A: {r['a']['title']} ({r['a']['domain']})\nB: {r['b']['title']} ({r['b']['domain']})\nMode: {r['mode']}\n")
    for f in r["facts"]:
        print(f"  {f[0]:45s} A: {f[1]!s:24s} B: {f[2]}")
    if r.get("reachability"):
        for side in ("a", "b"):
            for claim, verdict in r["reachability"][side]:
                print(f"  reachability {side.upper()}: {claim[:50]}: {verdict}")
    lab = r["labor"]
    if lab["a"] and lab["b"]:
        print("\n  Labor          A    B")
        for k, name in lab["kinds"].items():
            print(f"  {name:14s} {lab['a']['by_kind'].get(k, 0):<4d} {lab['b']['by_kind'].get(k, 0)}")
    print()
    for s in r["sentences"]:
        print("  - " + s)


if __name__ == "__main__":
    main()
