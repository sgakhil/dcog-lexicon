"""Extraction AI: read a fieldnote, write a diagram file in the lexicon's format.

The model runs locally through Ollama. Its output is constrained to the
schema (and to the controlled vocabulary), checked with the validator, and
sent back once for correction if the check fails. Every run is logged with the
model version, prompt hash and settings, so results can be reproduced.

Usage:
    python3 extract.py ../notes/fn045.txt                  # writes ../predicted/fn045.json
    python3 extract.py ../notes/*.txt --model llama3.1:8b
    python3 extract.py ../notes/dev01.txt --domain software_development
"""
import argparse
import copy
import datetime
import hashlib
import json
from pathlib import Path

from lexicon import DEFAULT_DOMAIN, ROOT, SCHEMA, domain, domain_names, lens, lens_names, load, validate, vocab
from llm import DEFAULT_MODEL, LLMError, chat, model_digest

PROMPT_VERSION = "extract-v1.2"


# ---------- output schema: the diagram schema, minus bookkeeping, with vocabulary as enums
def _inline(schema):
    defs = schema.get("$defs", {})

    def walk(x):
        if isinstance(x, dict):
            if "$ref" in x:
                return walk(copy.deepcopy(defs[x["$ref"].split("/")[-1]]))
            return {k: walk(v) for k, v in x.items()
                    if k not in ("$defs", "$schema", "$id", "default", "pattern")}
        if isinstance(x, list):
            return [walk(v) for v in x]
        return x
    return walk(schema)


def output_schema(dom=DEFAULT_DOMAIN, lenses=None):
    VOCAB = vocab(dom)
    s = _inline(copy.deepcopy(SCHEMA))
    for k in ("id", "source", "domain"):
        s["properties"].pop(k)
        if k in s["required"]:
            s["required"].remove(k)
    node = s["properties"]["nodes"]["items"]["properties"]
    node["activity"] = {"enum": list(VOCAB["activities"])}
    node["system"] = {"enum": list(VOCAB["systems"])}
    node["lane"] = {"enum": list(VOCAB["lanes"])}
    node["practices"] = {"type": "array", "items": {"enum": list(VOCAB["practices"])}}
    lenses = lens_names() if lenses is None else lenses
    for n in lens_names():
        add = lens(n)["adds"]
        if n in lenses:
            s["required"].append(add["map_field"])
        else:
            s["properties"].pop(add["map_field"], None)
            node.pop(add.get("node_field"), None)
    return s


# ---------- prompt
def _terms(VOCAB, section):
    v = {k: (d["definition"] if isinstance(d, dict) else d) for k, d in VOCAB[section].items()}
    return "\n".join(f"  - {k}: {d}" if isinstance(d, str) else f"  - {k}" for k, d in v.items())


def lens_prompt(name, number):
    L = lens(name)
    T = L["terms"]
    text = L["prompt"].format(toulmin=", ".join(T.get("toulmin", {})), argument_status=", ".join(T.get("argument_status", {})),
                              labor_defs=_terms(T, "labor") if "labor" in T else "")
    return f"\n{number}. {text}\n"


def system_prompt(dom=DEFAULT_DOMAIN, lenses=None):
    VOCAB = vocab(dom)
    lenses = lens_names() if lenses is None else lenses
    _t = lambda section: _terms(VOCAB, section)
    return f"""You are coding an ethnographic fieldnote from a {VOCAB["setting"]}
({VOCAB["title"]}) into a structured activity map, following a cognitive-ethnography
lexicon. Code only what the note supports; do not invent steps. If something is unclear,
leave it out.

THE MAP HAS {2 + len(lenses)} LAYERS.

1. WORKFLOW. Each step the person takes is a node with an activity, the software
system it happens in, and the screen lane where it happens. Mark AI elements with
is_ai=true, the first step with entry=true, and sign-off with closes_claim=true. Link
steps with edges typed:
{_t("edge_types")}

Lanes:
{_t("lanes")}
Systems:
{_t("systems")}
Activities (use exactly these names):
{_t("activities")}
Practices (optional, on nodes): {", ".join(VOCAB["practices"])}

2. ROUTING. For each knowledge claim (a finding asserted by the human, the AI, or both),
list the epistemic states it passed through, in order:
{_t("states")}
Rules: closed=true only if the last state is provisional_acceptance. Set
unexamined_agreement=true (with claim_source "hybrid" and states ["provisional_acceptance"])
when a claim closed because reader and AI agreed and nothing independent was checked.
Looking again at the same AI output does not count as validation. In this setting,
independent checks are: {VOCAB["independent_checks"]}
Give every step a level: 0 for the default read, 1 for the first round of extra checking
prompted by doubt, 2 for the next, and so on. trigger says what re-opened appraisal: none, substantive_doubt
(the reader's own doubt), ai_generated_doubt (an AI flag), discordance (reader and AI
disagree), or protocol (a rule required a check).
{"".join(lens_prompt(n, 3 + i) for i, n in enumerate(lenses))}
Return only the JSON object."""


def build_messages(note_text, dom=DEFAULT_DOMAIN, lenses=None):
    example = domain(dom)["example"]
    ex_note = (ROOT / example["note"]).read_text()
    ex = load(ROOT / example["map"])
    lenses = lens_names() if lenses is None else lenses
    ex_out = {k: v for k, v in ex.items() if k not in ("id", "source", "domain")}
    for n in lens_names():   # the worked example shows only the layers being coded
        if n not in lenses:
            add = lens(n)["adds"]
            ex_out.pop(add["map_field"], None)
            ex_out["nodes"] = [{k: v for k, v in nd.items() if k != add.get("node_field")} for nd in ex_out["nodes"]]
    return [
        {"role": "system", "content": system_prompt(dom, lenses)},
        {"role": "user", "content": f"FIELDNOTE:\n{ex_note}"},
        {"role": "assistant", "content": json.dumps(ex_out, indent=1)},
        {"role": "user", "content": f"FIELDNOTE:\n{note_text}"},
    ]


# ---------- run
def extract(note_path, model=DEFAULT_MODEL, coder_label=None, dom=DEFAULT_DOMAIN, lenses=None):
    """lenses: coding lenses to apply (default: all in lenses/; [] for workflow and claims only)."""
    note_path = Path(note_path)
    lenses = lens_names() if lenses is None else [l for l in lenses if l in lens_names()]
    messages = build_messages(note_path.read_text(), dom, lenses)
    schema = output_schema(dom, lenses)
    raw, meta = chat(messages, model=model, schema=schema)
    attempts = [{"raw": raw, **meta}]

    stem = note_path.stem.lower().replace("-", "_").replace(" ", "_")
    def finish(text):
        d = json.loads(text)
        d = {"id": f"pred_{stem}", "domain": dom, "title": d.pop("title", note_path.stem),
             "source": {"kind": "episode", "origin": f"LLM extraction ({model}, {PROMPT_VERSION})",
                        "fieldnote_id": note_path.name, "coder": coder_label or model}, **d}
        return d, validate(d)

    try:
        diagram, errors = finish(raw)
    except json.JSONDecodeError as e:
        diagram, errors = None, [f"not valid JSON: {e}"]

    if errors:  # one correction round: show the model its errors
        messages += [{"role": "assistant", "content": raw},
                     {"role": "user", "content": "The checker found these problems:\n- "
                      + "\n- ".join(errors) + "\nReturn the corrected JSON object."}]
        raw, meta = chat(messages, model=model, schema=schema)
        attempts.append({"raw": raw, **meta})
        try:
            diagram, errors = finish(raw)
        except json.JSONDecodeError as e:
            diagram, errors = None, [f"not valid JSON: {e}"]

    log = {
        "note": note_path.name,
        "note_sha256": hashlib.sha256(note_path.read_bytes()).hexdigest(),
        "model": model, "model_digest": model_digest(model), "domain": dom, "lenses": lenses,
        "prompt_version": PROMPT_VERSION,
        "prompt_sha256": hashlib.sha256(json.dumps(messages[:-1] if len(attempts) > 1 else messages).encode()).hexdigest(),
        "settings": {"temperature": 0.0, "seed": 42},
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "attempts": attempts, "final_errors": errors,
    }
    return diagram, errors, log


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("notes", nargs="+", help="fieldnote .txt files")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--lens", nargs="*", default=None, choices=lens_names(),
                    help="coding lenses to apply (default: all); give --lens with no names for workflow and claims only")
    ap.add_argument("--domain", default=DEFAULT_DOMAIN, choices=domain_names(),
                    help="which domain vocabulary to code with (default: radiology)")
    ap.add_argument("-o", "--outdir", default=str(ROOT / "predicted"))
    args = ap.parse_args()
    out = Path(args.outdir)
    (out / "logs").mkdir(parents=True, exist_ok=True)
    for n in args.notes:
        print(f"coding {n} with {args.model} ...", flush=True)
        try:
            diagram, errors, log = extract(n, args.model, dom=args.domain, lenses=args.lens)
        except LLMError as e:
            print(f"\nERROR: {e}")
            return 1
        stem = Path(n).stem
        (out / "logs" / f"{stem}.log.json").write_text(json.dumps(log, indent=2))
        if diagram is None:
            print(f"   failed: {errors[0]}  (details in {out}/logs/{stem}.log.json)")
            continue
        (out / f"{stem}.json").write_text(json.dumps(diagram, indent=2))
        status = "valid" if not errors else f"saved with {len(errors)} problem(s): " + "; ".join(errors[:3])
        print(f"   -> {out}/{stem}.json  ({status}; {log['attempts'][-1]['total_duration_s']} s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
