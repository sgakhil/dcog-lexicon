"""Write LEXICON.md, the standalone codebook, from schema/core.json and domains/*.json.

The prose lives here; every term table is generated from the JSON files, so the
codebook cannot drift from what the validator checks. Re-run after editing them.

Usage: python3 build_codebook.py
"""
from lexicon import CORE, ROOT, definition, domain, domain_names


def table(entries, head, extra=None):
    rows = [f"| {head[0]} | {head[1]} |" + (f" {extra[0]} |" if extra else ""),
            "| --- | --- |" + (" --- |" if extra else "")]
    for k, e in entries.items():
        rows.append(f"| `{k}` | {definition(e)} |" + (f" {extra[1](k, e)} |" if extra else ""))
    return "\n".join(rows)


def aliases(k, e):
    al = e.get("aliases", []) if isinstance(e, dict) else e
    return ", ".join(f"“{a}”" for a in al) or "–"


def domain_section(name, n):
    D = domain(name)
    sys_alias = lambda k, e: ", ".join(a for a, c in D.get("system_aliases", {}).items() if c == k) or "–"
    ai_role = lambda k, e: (e.get("ai_role", "").replace("_", " ") if isinstance(e, dict) else "") or "–"
    lanes = {k: {"definition": f"**{e['title']}** ({e['role']}). {e['definition']}"} for k, e in D["lanes"].items()}
    systems = {k: {"definition": definition(e) + (" *(AI)*" if e.get("ai") else "")} for k, e in D["systems"].items()}
    return f"""### 4.{n} {D['title']} (`{name}`)

{D['about']}

**Screen lanes**

{table(lanes, ("Lane", "Title, role and what it holds"))}

**Systems**

{table(systems, ("System", "What it is"), ("Shorthand accepted as a hint", sys_alias))}

**Activities**

{table(D['activities'], ("Activity", "Definition"), ("AI role", ai_role))}

**AI models:** {"; ".join(f"`{k}` ({v[0].lower() + v[1:].rstrip('.')})" for k, v in D['ai_models'].items())}.

**Practices (optional detail):** {", ".join(f"`{k}`" for k in D['practices'])}.

**What counts as an independent check here:** {D['independent_checks']}

**Worked example:** `{D['example']['note']}` coded as `{D['example']['map']}`.
"""


def build():
    names = domain_names()
    order = ["radiology"] + [n for n in names if n != "radiology"]
    domains_md = "\n".join(domain_section(n, 2 + i) for i, n in enumerate(order))
    domain_list = "\n".join(f"- `{n}`: {domain(n)['title']}. {domain(n)['about']}" for n in order)
    return f"""# The dcog lexicon: codebook

Version {CORE['version']}. Anonymous authors (under review).

The lexicon is a notation for drawing **activity maps** of human–AI work from ethnographic fieldnotes: who or what did each step, on which screen, how one step led to the next, and what happened to each claim along the way. It grew out of a cognitive ethnography of AI-augmented radiology (2024–2026), where it began as a legend in the first author's fieldnotes.

The lexicon has two parts:

- a **core** (`schema/core.json`) that is the same in every setting: how steps link, what can happen to a claim, how an argument breaks down;
- a **domain vocabulary** (`domains/<name>.json`) for each setting: its screens, software systems, activities and AI tools.

Current domains:

{domain_list}

The same terms are used by people coding by hand, by the AI model in `tools/extract.py`, and by the checker in `tools/validate.py`. This file is enough to code an episode. `README.md` explains the files and tools.

## 1. What a map records

The unit is one **episode**: a person working one item (a study, a ticket, a case) from where it arrives to where the result is recorded. A map can also code a **session** (patterns seen with one person in one sitting) or a **case type** (a composite of many episodes).

Each map has three layers.

1. **Workflow.** The steps, the software each used, the screen it happened on, and typed links between steps.
2. **Claims.** Each claim made during the episode (a finding, a diagnosis, a fix), who made it (person, AI or both), and the states it passed through before it closed or was left open.
3. **Argument** (optional). Where the reasoning behind a claim broke down, in Toulmin's terms, and the work the person did to repair it.

## 2. How to code an episode

1. **Choose the domain** and record the source: kind, origin, fieldnote ID, coder, and the session header (role, setting, time). Use roles, never names.
2. **List the steps in order.** For each, choose an activity, the system and the screen lane from the domain vocabulary. Mark the first step `entry`. Mark AI elements `is_ai`, name their model, and record what they showed (`ai_output`) if the note says.
3. **Assign levels.** Level 0 is the ordinary path. When doubt sends the person to further checking, those steps go one level down. In the original notebook each level began after a “why?”.
4. **Link the steps** with `action`, `doubt` or `institutional` links (§3.1). Add a short label where the note gives one.
5. **Follow each claim.** Record who made it, what re-opened it (§3.3), the states it passed through (§3.2), its steps, and whether it closed. Apply rules R1–R6.
6. **Code the argument layer** only where the note shows a breakdown (§3.6–3.8).
7. **Link to evidence.** Point each step, link or claim to the fieldnote passage that supports it. Quote only published text.
8. **Check** with `python3 validate.py <file>`. Errors mean the map breaks a rule; notes mean it is worth a second look.

### Coding rules (enforced by `validate.py`)

- **R1. Only acceptance closes.** A claim is closed if and only if its last state is `provisional_acceptance`.
- **R2. A check must be independent.** Code `validation` only when the claim was checked against something independent of it. Each domain lists what counts. Looking again at the same output that made the claim is not a check.
- **R3. Agreement without a check.** Flag `unexamined_agreement` when a claim closed because the person and the AI agreed and nothing independent was consulted. Such a claim has source `hybrid` and the single state `provisional_acceptance`.
- **R4. AI claims point to AI.** A claim from the AI, or from person and AI together, should include an AI step (a note, not an error).
- **R5. AI position follows its role.** Each AI step has a role, from its activity or from its lane: in the queue it is triage, in the work it is support, after the work it is a second opinion. If the coded `ai_position` disagrees, the checker prints a note.
- **R6. One meaning per term.** Use the canonical terms. Shorthand from notebooks is accepted only as a hint.

## 3. Core terms (every domain)

### 3.1 Link types

{table(CORE['edge_types'], ("Type", "Meaning"))}

### 3.2 Claim states

{table(CORE['states'], ("State", "Meaning"))}

### 3.3 Triggers

{table(CORE['triggers'], ("Trigger", "What re-opened the claim"))}

### 3.4 Claim sources

{table(CORE['claim_sources'], ("Source", "Meaning"))}

### 3.5 Lane roles and AI roles

Every domain's screen lanes have one of three roles. The role of an AI step follows from its lane unless its activity says otherwise.

{table(CORE['lane_roles'], ("Lane role", "Meaning"))}

{table(CORE['ai_roles'], ("AI role", "Meaning"))}

{table(CORE['ai_positions'], ("AI position in the episode", "Meaning"))}

### 3.6 Toulmin elements

{table(CORE['toulmin'], ("Element", "Meaning"))}

### 3.7 Breakdown status

{table(CORE['argument_status'], ("Status", "Meaning"))}

### 3.8 Repair labor

{table(CORE['labor'], ("Code", "Labor"))}

### 3.9 Source kinds

{table(CORE['source_kinds'], ("Kind", "Meaning"))}

## 4. Domain vocabularies

### 4.1 How to write a vocabulary for a new setting

A new setting needs only a new file in `domains/`. Copy an existing one and answer six questions from your fieldnotes:

1. **Screens.** What surfaces do people work across? Give each a short code, a title and a role: queue (where work arrives), work (where it is done and checked) or record (where the result is written or shipped).
2. **Systems.** Which software do they use? Mark AI systems with `"ai": true`.
3. **Activities.** What do people do, in their own terms? Write a one-sentence definition for each. For AI activities, give an `ai_role` if the lane does not make it clear.
4. **AI models.** Which AI tools appear, and what kinds of output do they show?
5. **Independent checks.** In this setting, what counts as checking a claim against something independent?
6. **A worked example.** One short note and its map, used to show the AI model what is expected.

Then run `python3 make_editor_schema.py` and `python3 build_codebook.py`, and code with `--domain <name>`. The core and the rules do not change.

{domains_md}
## 5. Reading a rendered map

`tools/render.py` draws a map two ways: **screens** (one column per lane, left to right) and **escalation rows** (`--layout levels`, the notebook layout, one row per level of checking).

| Mark | Meaning |
| --- | --- |
| Bold border | Entry step |
| Double border | The claim closes here |
| Dashed blue border, square corners | AI step in a queue lane |
| Dashed blue border, rounded corners | AI step in a work or record lane |
| Solid arrow | Action |
| Dashed red arrow | Doubt |
| Dotted purple arrow | Institutional influence |
| [R] [C] [A] [I] | Repair labor at that step |
| “shows: …” | What the AI displayed |
| “PAC · CL” | In escalation rows: system shorthand and lane |

## 6. Changes

| Version | Change |
| --- | --- |
| 1.2 | Legal work added as a second extension domain with a synthetic example; extension examples relabelled as synthetic; product names replaced with generic ones and the gold set reduced to the three published vignettes, to protect the field site. |
| 1.1 | Lexicon split into a domain-neutral core and domain vocabularies; software development added as a second domain with a worked example; lane roles and AI roles make AI position work in any setting. |
| 1.0 | Every term defined; rules R1–R6 stated and enforced; Case 3 and Case 1 recoded; escalation levels assigned. |
| 0.2 | Aligned with the field notebook: lanes L, CL, CR, R; AI shape by screen; model and output fields; levels; session header. |
| 0.1 | First schema and seven maps from published figures. |
"""


if __name__ == "__main__":
    text = build()
    (ROOT / "LEXICON.md").write_text(text)
    print(f"wrote LEXICON.md ({len(text.split())} words)")
