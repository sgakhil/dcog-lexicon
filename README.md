# dcog-lexicon

A lexicon and a local AI tool for turning ethnographic fieldnotes into **activity maps** of human–AI work: who or what did each step, on which screen, and how each claim was checked, accepted or left open. Many maps drawn the same way show how knowledge and cognition are distributed across people and AI in a workplace.

The tool runs an open-weight model **on the researcher's own machine**, because fieldnotes from hospitals, firms and other sensitive sites usually cannot be sent to a cloud service. It produces a draft map; the researcher checks and corrects it.

Anonymous authors (under review). Version 1.2, October 2026. Stage 1 research artifact for the *Organization Science* special issue "AI-Enabled Frontiers in Organizational Science".

## Start here

| If you want to | Read |
| --- | --- |
| Understand the notation and code an episode by hand | [LEXICON.md](LEXICON.md), the codebook |
| Use it in a setting other than radiology | [LEXICON.md §4.1](LEXICON.md#41-how-to-write-a-vocabulary-for-a-new-setting) |
| Run the tools, including the local AI, step by step | [GUIDE.md](GUIDE.md) |
| See maps without installing anything | `docs/index.html` (open it in a browser), or the [project page](https://anonymous.4open.science/w/dcog-lexicon-2026/) |

## How it works

```
fieldnote ──► local model (Ollama) ──► draft map ──► researcher corrects ──► many maps ──► patterns
               uses the lexicon          checked by the rules R1–R6           event log, comparisons
```

The lexicon has two parts:

| Part | File | Contents |
| --- | --- | --- |
| Core (every setting) | `schema/core.json` | Link types (action, doubt, institutional); claim states (provisional acceptance, validation, consultation, deferral); triggers; Toulmin breakdowns and repair labor; lane roles (queue, work, record) and AI roles (triage, support, second opinion) |
| Domain (one per setting) | `domains/<name>.json` | That setting's screens, software, activities, AI tools, and what counts as an independent check |

Three domains ship now. Radiology is the base case; the other two are extension cases (Burawoy, 1998), synthetic for now:

| Domain | Status |
| --- | --- |
| `radiology`: AI-augmented diagnostic radiology | **Base case.** Built from 25 months of fieldwork; three hand-coded vignettes |
| `software_development`: developers working with AI coding assistants | **Extension, synthetic.** One synthetic note and map, not fieldwork |
| `legal`: legal research and drafting with AI assistants | **Extension, synthetic.** One synthetic note and map, not fieldwork |

The object of every map is a relation rather than a person or a place: how a claim passes between people, AI and screens (relational ethnography; Desmond, 2014).

A new setting needs only a new domain file; the core, the rules and the tools stay the same.

## What works and what does not yet

- **Works:** the lexicon (three domains), the checker, the renderer, scoring, event-log export, the synthetic-note generator and the extraction pipeline, all tested end to end with a stand-in server.
- **Not yet tested:** extraction with a real local model on real fieldnotes. That is the Stage 2 work. Until then we make no claim about how accurate the drafts are.
- **Not automated:** linking each map element to the fieldnote passage behind it. The researcher does this when correcting a draft.

## Contents

```
LEXICON.md                   Codebook: procedure, rules R1-R6, core terms, every domain, adapting to a new setting
GUIDE.md                     Step-by-step guide to running everything, for non-programmers
schema/core.json             Domain-neutral terms
schema/diagram.schema.json   JSON Schema for one map
domains/                     One vocabulary per setting (radiology, software_development, legal)
gold/                        Three hand-coded radiology vignettes (answer keys)
examples/                    One note and map per domain (radiology illustrative, software and legal synthetic); a hand-made flawed prediction
renders/                     Every map drawn in both layouts (PNG and SVG)
eventlog.csv                 The maps as an event log for process-mining tools
docs/index.html              Standalone project page (served as the website)
site/template.html           Source of the project page
tools/extract.py             Fieldnote to draft map, with a local model (--domain)
tools/validate.py            Checks a map against the schema, its domain and the rules
tools/render.py              Draws a map (screen lanes, or notebook-style escalation rows)
tools/compare.py             Scores one map against another, layer by layer
tools/synthesize.py          Synthetic fieldnotes with known answers, for testing extraction
tools/evaluate.py            Scores a folder of drafts against their answer keys
tools/export_eventlog.py     Exports maps as an event log (CSV)
tools/build_codebook.py      Regenerates LEXICON.md from core.json and domains/
tools/build_site.py          Regenerates docs/index.html
tools/make_editor_schema.py  Regenerates the VS Code autocomplete schema
tools/llm.py, lexicon.py     Shared code
```

## Radiology gold set

| File | Source | AI position | What it shows |
| --- | --- | --- | --- |
| vignette1_automated_triage | Published vignette 1 | triage | Missing warrant [R], unstable qualifier [A]; flag deferred |
| vignette2_decision_support | Published vignette 2 | decision support | Opaque warrant [R][C], expanded rebuttal [I] |
| vignette3_second_opinion | Published vignette 3 | second opinion | Concordant branch closes with no check; unstable backing [A] |

Each vignette is a composite drawn from published work, so no single fieldnote or person can be traced from it. Product names are replaced with generic ones (vendor AI, in-house AI, dictation system).

## Quick start

Requires Python 3, `jsonschema` and Graphviz. On Ubuntu: `sudo apt install python3-jsonschema graphviz`. The AI parts also need [Ollama](https://ollama.com) and one model; see GUIDE.md.

```bash
cd tools
python3 validate.py ../gold/*.json ../examples/*episode*.json
python3 render.py ../gold/*.json -o ../renders                   # screen lanes
python3 render.py ../gold/*.json -o ../renders --layout levels    # notebook style
python3 extract.py ../examples/dev_illustrative_note.txt --domain software_development   # needs Ollama
```

## Data and ethics

Real fieldnotes stay with the researchers and are processed only on their own machines. The field site is not named, and details that could identify it (size, locations, product names) are left out. Public files use roles, never names, and point to fieldnotes by ID. Quotations appear only where they are already published. The `notes/` and `predicted/` folders, which hold real material, are excluded from the repository by `.gitignore`. Synthetic and illustrative notes are labelled as such.

## Citation

Anonymous (2026). *dcog-lexicon: A lexicon and local AI tool for mapping distributed cognition in human–AI work* (Version 1.2). Under review.

