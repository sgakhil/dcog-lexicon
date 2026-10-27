"""Synthetic fieldnote generator: diagram in, realistic fieldnote out.

Each synthetic note comes with its answer key (the diagram it was written from),
so extraction can be scored against a known truth. Optional "traps" tell the
writer to describe the episode in a way that is known to mislead coders, e.g.
agreement that sounds like checking. These seed known coding traps.

Usage:
    python3 synthesize.py ../gold/vignette1_automated_triage.json
    python3 synthesize.py ../gold/*.json --variants 3
    python3 synthesize.py ../gold/vignette3_second_opinion.json --trap agreement_looks_checked

Writes ../synthetic/notes/<name>.txt and ../synthetic/answers/<name>.json
"""
import argparse
import json
from pathlib import Path

from lexicon import ROOT, domain, domain_of, load, validate
from llm import DEFAULT_MODEL, LLMError, chat, model_digest

PROMPT_VERSION = "synth-v0.1"

TRAPS = {
    "none": {
        "instruction": "Describe the episode plainly and accurately.",
        "requires": None,
    },
    "agreement_looks_checked": {
        "instruction": ("Where the reader and the AI agree, have the reader use confirming words "
                        "('yep, that matches', 'looks right') and glance around the image, but do NOT "
                        "have them open priors, other views, history, or ask anyone. The agreement "
                        "must close without any independent check, even though it sounds careful."),
        "requires": "unexamined_agreement",
        "tests": "Does the coder mistake confident language for validation?",
    },
    "implicit_doubt": {
        "instruction": ("Show the reader's doubt only through behaviour - a long pause, scrolling back, "
                        "leaning in, re-zooming - never by saying they are unsure."),
        "requires": "doubt_edge",
        "tests": "Does the coder detect doubt that is shown but not said?",
    },
    "unresolved_flag": {
        "instruction": ("Make clear the AI flag is never resolved: the reader sets it aside or moves on "
                        "without accepting or rejecting it."),
        "requires": "open_claim",
        "tests": "Does the coder wrongly close a claim that was left open?",
    },
}


def fits(trap, d):
    need = TRAPS[trap]["requires"]
    if need == "unexamined_agreement":
        return any(c.get("unexamined_agreement") for c in d["routing"])
    if need == "doubt_edge":
        return any(e["type"] == "doubt" for e in d["edges"])
    if need == "open_claim":
        return any(not c["closed"] for c in d["routing"])
    return True


def describe(d):
    """Plain-language spec of the diagram for the writer (no lexicon jargon leaks into the note)."""
    nodes = {n["id"]: n for n in d["nodes"]}
    lines = ["Steps, in roughly this order:"]
    for n in d["nodes"]:
        bits = [n["activity"]]
        if n.get("detail"):
            bits.append(f"({n['detail']})")
        bits.append(f"in {n['system']}")
        if n.get("is_ai"):
            bits.append("[this is the AI tool]")
        lines.append("- " + " ".join(bits))
    lines.append("How the steps connect:")
    for e in d["edges"]:
        kind = {"action": "then", "doubt": "because of doubt or checking, goes to",
                "institutional": "(organisational loop) affects"}[e["type"]]
        lines.append(f"- {nodes[e['from']]['activity']} {kind} {nodes[e['to']]['activity']}"
                     + (f" - {e['label']}" if e.get("label") else ""))
    lines.append("What happens to each finding:")
    for c in d["routing"]:
        lines.append(f"- '{c['claim']}' (from {c['claim_source']}): goes through "
                     + " then ".join(s.replace("_", " ") for s in c["states"])
                     + (", and is signed off" if c["closed"] else ", and is left unresolved")
                     + (". Reader and AI simply agree; nothing independent is checked."
                        if c.get("unexamined_agreement") else "."))
    return "\n".join(lines)


def messages_for(d, trap, setting=None):
    dom = domain(domain_of(d))
    setting = setting or dom["setting"]
    style_example = (ROOT / dom["example"]["note"]).read_text()
    system = (f"You write realistic ethnographic fieldnotes from a {setting}, "
              "as an observing social scientist would: present tense or past tense, concrete actions, "
              "short quoted remarks, the observer's occasional aside. Use participant codes (A1, R3, F2), "
              "never real names. Do not use analytic terms such as 'validation', 'epistemic', "
              "'routing', 'deferral', 'Toulmin', or 'labor'. 120-250 words. Output only the note.")
    user = (f"Style example:\n{style_example}\n\n---\nWrite a new fieldnote of a {setting} episode that "
            f"contains exactly these events, and no extra diagnostic steps.\n\n{describe(d)}\n\n"
            f"Writing instruction: {TRAPS[trap]['instruction']}")
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("diagrams", nargs="+")
    ap.add_argument("--trap", choices=list(TRAPS), default="none")
    ap.add_argument("--variants", type=int, default=1, help="notes per diagram (different seeds)")
    ap.add_argument("--setting", default=None, help="override the setting named in the domain file")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("-o", "--outdir", default=str(ROOT / "synthetic"))
    args = ap.parse_args()
    out = Path(args.outdir)
    for sub in ("notes", "answers"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    digest = model_digest(args.model)

    for path in args.diagrams:
        d = load(path)
        if validate(d):
            print(f"skip {path}: diagram is not valid (run validate.py)")
            continue
        if not fits(args.trap, d):
            print(f"skip {path}: trap '{args.trap}' needs a diagram with {TRAPS[args.trap]['requires']}")
            continue
        for v in range(1, args.variants + 1):
            name = f"syn_{d['id']}_{args.trap}_v{v}"
            seed = 1000 + v
            print(f"writing {name} ...", flush=True)
            try:
                note, meta = chat(messages_for(d, args.trap, args.setting), model=args.model,
                                  temperature=0.8, seed=seed)
            except LLMError as e:
                print(f"\nERROR: {e}")
                return 1
            (out / "notes" / f"{name}.txt").write_text(note.strip() + "\n")
            answer = dict(d)
            answer["id"] = name
            answer["source"] = {
                "kind": "synthetic",
                "origin": f"Generated from {Path(path).name} by {args.model} ({PROMPT_VERSION}, seed {seed}, "
                          f"digest {digest}); trap={args.trap}",
                "fieldnote_id": f"notes/{name}.txt",
                "notes": TRAPS[args.trap].get("tests", "plain rendering"),
            }
            (out / "answers" / f"{name}.json").write_text(json.dumps(answer, indent=2))
            print(f"   -> notes/{name}.txt + answers/{name}.json ({meta['total_duration_s']} s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
