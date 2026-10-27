"""Shared helpers: load the core lexicon and domain vocabularies, validate maps.

The lexicon has two parts:
  schema/core.json        domain-neutral terms (links, claim states, triggers, argument)
  domains/<name>.json     one setting's screens, systems, activities and AI models

Each map names its domain in a "domain" field (default: radiology).
"""
import json
from functools import lru_cache
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = json.loads((ROOT / "schema" / "diagram.schema.json").read_text())
CORE = json.loads((ROOT / "schema" / "core.json").read_text())
DEFAULT_DOMAIN = "radiology"


def domain_names():
    return sorted(p.stem for p in (ROOT / "domains").glob("*.json"))


@lru_cache(maxsize=None)
def domain(name=DEFAULT_DOMAIN):
    path = ROOT / "domains" / f"{name}.json"
    if not path.exists():
        raise ValueError(f"unknown domain '{name}' (available: {', '.join(domain_names())})")
    return json.loads(path.read_text())


@lru_cache(maxsize=None)
def vocab(name=DEFAULT_DOMAIN):
    """Core and domain terms merged into one dictionary."""
    return {**CORE, **domain(name)}


def domain_of(diagram):
    return diagram.get("domain", DEFAULT_DOMAIN)


def definition(entry):
    return entry.get("definition", "") if isinstance(entry, dict) else entry


def _alias_map(name, section):
    m = {}
    for canon, entry in vocab(name)[section].items():
        aliases = entry.get("aliases", []) if isinstance(entry, dict) else entry
        m[canon.lower()] = canon
        for a in aliases:
            m[a.lower()] = canon
    return m


def canonical_activity(label, name=DEFAULT_DOMAIN):
    return _alias_map(name, "activities").get(label.strip().lower())


def ai_systems(name=DEFAULT_DOMAIN):
    return {k for k, e in domain(name)["systems"].items() if isinstance(e, dict) and e.get("ai")}


def load(path):
    return json.loads(Path(path).read_text())


def validate(diagram):
    """Return a list of error strings (empty if valid)."""
    errors = [f"schema: {e.message} at {'/'.join(map(str, e.path))}"
              for e in jsonschema.Draft202012Validator(SCHEMA).iter_errors(diagram)]
    if errors:
        return errors
    try:
        V = vocab(domain_of(diagram))
    except ValueError as e:
        return [str(e)]
    dom = domain_of(diagram)
    lane_alias = {k.lower(): v for k, v in V.get("lane_aliases", {}).items()}
    sys_alias = {k.lower(): v for k, v in V.get("system_aliases", {}).items()}
    acts = _alias_map(dom, "activities")
    pracs = _alias_map(dom, "practices")

    ids = [n["id"] for n in diagram["nodes"]]
    if len(ids) != len(set(ids)):
        errors.append("duplicate node ids")
    idset = set(ids)

    for n in diagram["nodes"]:
        if n["activity"] not in V["activities"]:
            hint = acts.get(n["activity"].lower())
            errors.append(f"node {n['id']}: activity '{n['activity']}' is not in the {dom} vocabulary"
                          + (f" (use '{hint}')" if hint else ""))
        if n["system"] not in V["systems"]:
            hint = sys_alias.get(n["system"].lower())
            errors.append(f"node {n['id']}: unknown system '{n['system']}'" + (f" (use '{hint}')" if hint else ""))
        if n["lane"] not in V["lanes"]:
            hint = lane_alias.get(n["lane"].lower())
            errors.append(f"node {n['id']}: unknown lane '{n['lane']}'" + (f" (use '{hint}')" if hint else "")
                          + f"; lanes are {', '.join(V['lanes'])}")
        if "ai_model" in n and n["ai_model"] not in V["ai_models"]:
            errors.append(f"node {n['id']}: unknown ai_model '{n['ai_model']}' (one of: {', '.join(V['ai_models'])})")
        for p in n.get("practices", []):
            if p not in V["practices"]:
                hint = pracs.get(p.lower())
                errors.append(f"node {n['id']}: practice '{p}' not canonical" + (f" (use '{hint}')" if hint else ""))

    for e in diagram["edges"]:
        for end in ("from", "to"):
            if e[end] not in idset:
                errors.append(f"edge {e['from']}->{e['to']}: unknown node '{e[end]}'")

    if not any(n.get("entry") for n in diagram["nodes"]):
        errors.append("no entry node")

    for c in diagram["routing"]:
        for nid in c.get("nodes", []):
            if nid not in idset:
                errors.append(f"claim {c['claim_id']}: unknown node '{nid}'")
        closes = c["states"][-1] == "provisional_acceptance"
        if c["closed"] and not closes:
            errors.append(f"claim {c['claim_id']}: closed but last state is not provisional_acceptance (R1)")
        if not c["closed"] and closes:
            errors.append(f"claim {c['claim_id']}: ends in provisional_acceptance but closed=false (R1)")
        if c.get("unexamined_agreement"):
            if c["states"] != ["provisional_acceptance"]:
                errors.append(f"claim {c['claim_id']}: unexamined_agreement means the claim closed with no check, "
                              "so its only state must be provisional_acceptance (R3)")
            if c["claim_source"] != "hybrid":
                errors.append(f"claim {c['claim_id']}: unexamined_agreement needs claim_source 'hybrid' (R3)")

    for b in diagram.get("argument", []):
        for nid in b.get("nodes", []):
            if nid not in idset:
                errors.append(f"argument {b['element']}: unknown node '{nid}'")
    return errors


def ai_roles(diagram):
    """Roles of the AI elements: from the activity if the domain defines one, else from the lane's role."""
    V = vocab(domain_of(diagram))
    roles = set()
    for n in diagram["nodes"]:
        if not n.get("is_ai") or n["activity"] == "Model update drift":
            continue
        act = V["activities"].get(n["activity"], {})
        role = act.get("ai_role") if isinstance(act, dict) else None
        if not role:
            lane_role = V["lanes"].get(n["lane"], {}).get("role")
            role = {"queue": "triage", "work": "support", "record": "second_opinion"}.get(lane_role)
        if role:
            roles.add(role)
    return roles


def infer_ai_position(diagram):
    return {
        frozenset(): "none",
        frozenset({"triage"}): "triage",
        frozenset({"support"}): "decision_support",
        frozenset({"second_opinion"}): "second_opinion",
        frozenset({"triage", "support"}): "triage_and_decision_support",
        frozenset({"support", "second_opinion"}): "decision_support_and_second_opinion",
    }.get(frozenset(ai_roles(diagram)), "mixed")


def notes(diagram):
    """Soft checks that point at coding questions rather than errors."""
    out = []
    coded = diagram.get("ai_position")
    inferred = infer_ai_position(diagram)
    if coded != "implicit_confirmatory" and coded != inferred:
        out.append(f"ai_position is coded '{coded}' but the AI elements suggest '{inferred}' (R5)")
    ai_sys = ai_systems(domain_of(diagram))
    nodes = {n["id"]: n for n in diagram["nodes"]}
    for n in diagram["nodes"]:
        if n.get("is_ai") and "ai_model" not in n:
            out.append(f"node {n['id']}: AI element without ai_model")
        if n["system"] in ai_sys and not n.get("is_ai"):
            out.append(f"node {n['id']}: system '{n['system']}' is an AI system but is_ai is not set")
    for c in diagram["routing"]:
        if c["claim_source"] in ("ai", "hybrid") and not any(nodes.get(i, {}).get("is_ai") for i in c.get("nodes", [])):
            out.append(f"claim {c['claim_id']}: source is '{c['claim_source']}' but none of its nodes is an AI element (R4)")
    linked = {e["from"] for e in diagram["edges"]} | {e["to"] for e in diagram["edges"]}
    for n in diagram["nodes"]:
        if n["id"] not in linked and len(diagram["nodes"]) > 1:
            out.append(f"node {n['id']}: not linked to any other step")
    return out
