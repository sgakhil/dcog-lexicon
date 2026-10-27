# The dcog lexicon: codebook

Version 1.3. Anonymous authors (under review).

The lexicon is a notation for drawing **activity maps** of human–AI work from ethnographic fieldnotes: who or what did each step, on which screen, how one step led to the next, and what happened to each claim along the way. It grew out of a cognitive ethnography of AI-augmented radiology (2024–2026), where it began as a legend in the first author's fieldnotes.

The lexicon has two parts:

- a **core** (`schema/core.json`) that is the same in every setting: how steps link, what can happen to a claim, how an argument breaks down;
- a **domain vocabulary** (`domains/<name>.json`) for each setting: its screens, software systems, activities and AI tools.

Current domains:

- `radiology`: AI-augmented diagnostic radiology. Base case. Developed in 25 months of cognitive ethnography in a U.S. academic radiology department using several FDA-cleared AI tools.
- `legal`: Legal research and drafting with AI assistants. Extension case: written to show how the lexicon carries to a third setting. Synthetic; not yet tested on fieldwork.
- `software_development`: Software development with AI coding assistants. Extension case: written to show how the lexicon carries to a second setting. Synthetic; not yet tested on fieldwork.

The same terms are used by people coding by hand, by the AI model in `tools/extract.py`, and by the checker in `tools/validate.py`. This file is enough to code an episode. `README.md` explains the files and tools.

## 1. What a map records

The unit is one **episode**: a person working one item (a study, a ticket, a case) from where it arrives to where the result is recorded. A map can also code a **session** (patterns seen with one person in one sitting) or a **case type** (a composite of many episodes).

Each map has three layers.

1. **Workflow.** The steps, the software each used, the screen it happened on, and typed links between steps.
2. **Claims.** Each claim made during the episode (a finding, a diagnosis, a fix), who made it (person, AI or both), and the states it passed through before it closed or was left open.
3. **Coding lenses** (optional). Extra layers that apply one theory, switched on per study. The first, **argumentation**, records where the reasoning behind a claim broke down, in Toulmin's terms, and the argumentation labor the person did to keep it standing, a largely invisible kind of work (§5).

## 2. How to code an episode

1. **Choose the domain** and record the source: kind, origin, fieldnote ID, coder, and the session header (role, setting, time). Use roles, never names.
2. **List the steps in order.** For each, choose an activity, the system and the screen lane from the domain vocabulary. Mark the first step `entry`. Mark AI elements `is_ai`, name their model, and record what they showed (`ai_output`) if the note says.
3. **Assign levels.** Level 0 is the ordinary path. When doubt sends the person to further checking, those steps go one level down. In the original notebook each level began after a “why?”.
4. **Link the steps** with `action`, `doubt` or `institutional` links (§3.1). Add a short label where the note gives one.
5. **Follow each claim.** Record who made it, what re-opened it (§3.3), the states it passed through (§3.2), its steps, and whether it closed. Apply rules R1–R6.
6. **Code any lens layers** your study uses, for example the argument layer only where the note shows a breakdown (§5).
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

| Type | Meaning |
| --- | --- |
| `action` | The ordinary next step in the work (solid arrow). |
| `doubt` | A step taken because a claim was questioned; it re-opens appraisal (dashed arrow). |
| `institutional` | An influence that runs through the organisation rather than the read, such as a model update or engagement tracking (dotted arrow). |

### 3.2 Claim states

| State | Meaning |
| --- | --- |
| `provisional_acceptance` | The claim is taken as good enough to act on. The only state that closes a claim. |
| `validation` | The claim is checked against something independent of it. What counts as independent is listed in each domain file. Looking again at the same output that made the claim is not validation. |
| `consultation` | The claim is put to another person: a colleague, a senior, a client. |
| `deferral` | The claim is set aside unresolved: deprioritised, withheld, or carried forward. |

### 3.3 Triggers

| Trigger | What re-opened the claim |
| --- | --- |
| `none` | Nothing re-opened appraisal. |
| `substantive_doubt` | The person's own doubt about the work. |
| `ai_generated_doubt` | An AI flag, marking or message prompted the check. |
| `discordance` | The person's own judgement and the AI output disagreed. |
| `protocol` | A rule required the check, whatever the person thought. |

### 3.4 Claim sources

| Source | Meaning |
| --- | --- |
| `human` | Asserted by a person. |
| `ai` | Asserted by an AI model. |
| `hybrid` | Asserted jointly, typically when reader and AI agree. |

### 3.5 Lane roles and AI roles

Every domain's screen lanes have one of three roles. The role of an AI step follows from its lane unless its activity says otherwise.

| Lane role | Meaning |
| --- | --- |
| `queue` | Where work arrives and is sorted or prioritised (a worklist, a ticket queue, an inbox). |
| `work` | Where the main task is done and checked (an image viewer, a code editor, a case file). |
| `record` | Where the result is written down, signed or shipped (a report, a pull request, a decision letter). |

| AI role | Meaning |
| --- | --- |
| `triage` | AI sorts, flags or prioritises work before the person does it. |
| `support` | AI assists while the person does the work. |
| `second_opinion` | AI checks or reviews after the person has done the work. |

| AI position in the episode | Meaning |
| --- | --- |
| `none` | No AI element in the episode. |
| `implicit_confirmatory` | AI output is present but only confirms what the person already saw; it does not change the path. |
| `triage` | AI acts before the work, in the queue. |
| `decision_support` | AI acts during the work. |
| `second_opinion` | AI acts after the person's own work, as a check. |
| `triage_and_decision_support` | AI acts both before and during the work. |
| `decision_support_and_second_opinion` | AI acts both during the work and after it. |

### 3.6 Source kinds

| Kind | Meaning |
| --- | --- |
| `case_type` | Composite of many observations. |
| `vignette` | Composite written up as a vignette in a paper. |
| `session` | Patterns observed with one informant in one observation session. |
| `episode` | One observed episode. |
| `illustrative` | Written to illustrate the notation; not fieldwork data. |
| `synthetic` | Generated test note with a known answer. |

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

### 4.2 AI-augmented diagnostic radiology (`radiology`)

Base case. Developed in 25 months of cognitive ethnography in a U.S. academic radiology department using several FDA-cleared AI tools.

**Screen lanes**

| Lane | Title, role and what it holds |
| --- | --- |
| `L` | **Left monitor** (queue). Left monitor: PACS worklist (with AI result column), priors, EHR, chat. |
| `CL` | **Centre, left pane** (work). Centre monitor, left pane (C1): main image. |
| `CR` | **Centre, right pane** (work). Centre monitor, right pane (C2): other views, priors, comparisons. |
| `R` | **Right monitor** (record). Right monitor: dictation and report. |

**Systems**

| System | What it is | Shorthand accepted as a hint |
| --- | --- | --- |
| `PACS` | Picture archiving and communication system (worklist and viewer). | PAC |
| `Dictation` | Voice-recognition dictation and reporting system. | Dictation system |
| `EHR` | Electronic health record. | EMR |
| `RIS` | Radiology information system. | – |
| `Vendor AI` | Commercial AI platform from an external vendor (triage, overlays, second opinion). *(AI)* | – |
| `In-house AI` | AI models developed inside the department or health system. *(AI)* | – |
| `Email` | Institutional email (e.g., alerts from the department). | – |
| `Chat` | Messaging to reach or answer colleagues (in the PACS or the EHR). | PACS Messenger |
| `Web search` | General web search, mostly to look up reference images. | Q.Google |
| `General-purpose AI` | ChatGPT, Grok or similar, mostly to look up reference images. | Q.ChatGPT, Q.Grok |
| `Rad Ops` | Radiology operations staff who contact the referring clinician. | – |

**Activities**

| Activity | Definition | AI role |
| --- | --- | --- |
| `Worklist` | Open or scan the PACS worklist and choose the next study. | – |
| `Check AI result column` | Read the AI result column in the worklist (e.g. 'No finding', 'ETT 3.4') before or instead of opening the study. | – |
| `AI triage` | An AI model reorders or flags studies in the worklist before the read. | triage |
| `Read main image` | The reader's own read of the primary images: scrolling, zooming, windowing. | – |
| `AI overlay` | An AI marking shown on or beside the image in the viewer (heatmap, box, ping). | support |
| `Cross-check views` | Compare the primary view with other views, series or the AI output in the second pane. | – |
| `Re-examine image` | Return to the image specifically to test a claim that has been questioned. | – |
| `Search priors` | Find and open earlier studies of the same patient. | – |
| `Compare prior volumes` | Measure a finding against priors (size, volume, growth). | – |
| `Review patient history` | Read history, notes, labs or status in the EHR. | – |
| `Look up reference images` | Search outside the record (web search or a general-purpose AI) for what a finding typically looks like. | – |
| `Message colleague` | Ask or answer a colleague through chat (PACS or EHR). | – |
| `Decode AI flag` | Work out what an AI flag refers to when its what, where or why is not shown. | – |
| `Reconstruct AI claim` | Search the image for the basis of an AI claim that gives no explanation. | – |
| `AI second opinion` | An AI read offered for comparison after the reader's own read. | second opinion |
| `Deprioritise case` | Set a flagged case aside and read another first. | – |
| `Dictate report` | Dictate findings and impression, often by choosing template options. | – |
| `Flag critical result` | Insert the critical-result flag in the report macro so Rad Ops is alerted. | – |
| `Flag in RIS` | Mark the case in the radiology information system for follow-up. | – |
| `Sign off report` | Sign the report. The point where a claim reaches closure. | – |
| `Notify clinician via Rad Ops` | Rad Ops staff contact the referring clinician about a flagged result. | – |
| `Model update drift` | Institutional event: a model's behaviour changes after an update. | – |
| `Non-engagement alert` | Institutional event: the department tracks whether readers looked at the AI output. | – |

**AI models:** `triage` (vendor triage model shown in the worklist (square Ai in the notebook)); `widget` (vendor model shown as a widget in the viewer (rounded Ai in the notebook)); `Pneu` (pneumothorax model); `ETT` (endotracheal tube position model); `MSK` (musculoskeletal or fracture model); `PE` (pulmonary embolism model); `nodule` (lung nodule model); `other` (any other model; name it in detail).

**Practices (optional detail):** `scrolling`, `zooming`, `switching`, `triage`, `searching`, `identifying`, `choose options`, `impressions`, `findings`, `confirming`, `cross checking`, `validating AI claim`.

**What counts as an independent check here:** Priors, other views or series, measurements against priors, patient history, a colleague, a reference image.

**Activities counted as independent checks** (used by the reachability analysis layer): `Search priors`, `Compare prior volumes`, `Review patient history`, `Look up reference images`, `Message colleague`.

**Worked example:** `examples/fn031_illustrative_note.txt` coded as `examples/episode_fn031.json`.

### 4.3 Legal research and drafting with AI assistants (`legal`)

Extension case: written to show how the lexicon carries to a third setting. Synthetic; not yet tested on fieldwork.

**Screen lanes**

| Lane | Title, role and what it holds |
| --- | --- |
| `M` | **Matter inbox** (queue). Email and matter management: where assignments and deadlines arrive. |
| `D` | **Draft** (work). The memo, brief or contract being written, including AI drafting suggestions. |
| `A` | **AI assistant** (work). Legal AI assistant panel: questions, answers, summaries, suggested authorities. |
| `L` | **Legal sources** (work). Case-law and statute database, citator, the source documents themselves. |
| `S` | **Sign-off** (record). Review by a senior lawyer and sending to the client or filing with the court. |

**Systems**

| System | What it is | Shorthand accepted as a hint |
| --- | --- | --- |
| `Email` | Email and calendar. | Outlook |
| `Matter management` | Matter, docket and deadline system. | – |
| `Word processor` | Word processor or drafting tool where the document is written. | Word |
| `Legal AI assistant` | AI that answers legal questions, summarises sources and suggests authorities. *(AI)* | – |
| `AI contract review` | AI that flags clauses or issues in a set of documents. *(AI)* | – |
| `Case-law database` | Database of cases, statutes and secondary sources. | Westlaw, Lexis |
| `Citator` | Tool that checks whether a case exists, is still good law and how it has been treated. | KeyCite, Shepard's |
| `Document management` | Firm's store of precedents, prior memos and client documents. | – |
| `Team chat` | Messaging with colleagues. | Teams |

**Activities**

| Activity | Definition | AI role |
| --- | --- | --- |
| `Receive assignment` | Take on a task from a senior lawyer or client and read what is asked. | – |
| `Read documents` | Read the client's documents or the file. | – |
| `AI issue flag` | An AI review tool flags a clause, document or issue for attention. | triage |
| `Ask AI assistant` | Put a legal question to an AI assistant and read its answer. | support |
| `Paste AI text` | Copy text or citations from the AI answer into the draft. | – |
| `Search case law` | Search the database for cases, statutes or commentary. | – |
| `Read source` | Open and read the case, statute or document itself. | – |
| `Check citation` | Run a citation through the citator: does it exist, is it still good law. | – |
| `Find precedent` | Look up a prior memo, brief or contract from the firm. | – |
| `Draft text` | The lawyer's own writing or editing of the document. | – |
| `Ask colleague` | Ask a colleague in person or by chat. | – |
| `Senior review` | A senior lawyer reviews the work and comments. | – |
| `Send or file` | Send the work to the client or file it. The point where a claim reaches closure. | – |

**AI models:** `research_assistant` (assistant that answers legal questions and suggests authorities); `drafting_assistant` (assistant that writes or rewrites passages); `contract_review` (tool that flags clauses or issues across documents); `other` (any other model; name it in detail).

**Practices (optional detail):** `reading`, `typing`, `highlighting`, `searching`, `comparing versions`.

**What counts as an independent check here:** Reading the case or statute itself, running a citation through the citator, the client's own documents, a colleague's or senior lawyer's reading. Reading the AI's summary of a case again is not a check.

**Activities counted as independent checks** (used by the reachability analysis layer): `Read documents`, `Read source`, `Check citation`, `Find precedent`, `Ask colleague`, `Senior review`.

**Worked example:** `examples/legal_synthetic_note.txt` coded as `examples/legal_episode_synthetic.json`.

### 4.4 Software development with AI coding assistants (`software_development`)

Extension case: written to show how the lexicon carries to a second setting. Synthetic; not yet tested on fieldwork.

**Screen lanes**

| Lane | Title, role and what it holds |
| --- | --- |
| `T` | **Tracker** (queue). Ticket tracker and notifications: where work arrives and is prioritised. |
| `E` | **Editor** (work). Code editor, including inline AI completions. |
| `S` | **Side panel** (work). AI chat panel, documentation and web search beside the editor. |
| `X` | **Terminal** (work). Terminal: running code, tests and reading logs. |
| `P` | **Pull request** (record). Version control and code review: commits, pull requests, review comments, merge. |

**Systems**

| System | What it is | Shorthand accepted as a hint |
| --- | --- | --- |
| `Issue tracker` | Ticket or issue tracker (e.g. Jira, Linear). | Jira |
| `IDE` | Code editor or IDE. | VS Code |
| `Code assistant` | Inline AI completion in the editor. *(AI)* | Copilot |
| `AI chat` | AI chat assistant in a side panel or browser. *(AI)* | ChatGPT |
| `AI review bot` | AI that comments on pull requests. *(AI)* | – |
| `Docs and search` | Documentation, Stack Overflow, web search. | – |
| `Terminal` | Shell, local run, test runner, logs. | – |
| `Git host` | Version control host: branches, pull requests, review, merge. | GitHub |
| `CI` | Continuous integration: automated builds and tests on each push. | – |
| `Team chat` | Messaging with colleagues (e.g. Slack). | Slack |

**Activities**

| Activity | Definition | AI role |
| --- | --- | --- |
| `Pick up ticket` | Choose the next ticket and read what is asked. | – |
| `Read code` | Read the existing code around the change. | – |
| `Write code` | The developer's own writing or editing of code. | – |
| `Accept inline suggestion` | Accept an AI completion offered in the editor. | support |
| `Ask AI assistant` | Put a question or error to an AI chat assistant and read its answer. | support |
| `Paste AI answer` | Copy code or text from the AI answer into the work. | – |
| `Read documentation` | Look up documentation, examples or forum answers. | – |
| `Run code` | Run the program locally and look at what happens. | – |
| `Run tests` | Run the test suite or specific tests. | – |
| `Read error output` | Read an error message, stack trace or log. | – |
| `Ask colleague` | Ask or answer a colleague in chat or in person. | – |
| `Open pull request` | Commit, push and open a pull request for review. | – |
| `AI review comment` | An AI reviewer comments on the pull request. | second opinion |
| `Human review` | A colleague reviews the pull request and comments. | – |
| `CI result` | Automated build and tests report pass or fail. | – |
| `Merge` | Merge the change. The point where a claim reaches closure. | – |

**AI models:** `inline_completion` (completion that appears as ghost text in the editor); `chat_assistant` (conversational assistant answering questions or proposing code); `ai_review` (automated reviewer commenting on pull requests); `other` (any other model; name it in detail).

**Practices (optional detail):** `reading`, `typing`, `scrolling`, `searching`, `debugging`, `comparing diff`.

**What counts as an independent check here:** Running the code, running tests, CI results, documentation, a colleague's review. Re-reading the AI answer is not a check.

**Activities counted as independent checks** (used by the reachability analysis layer): `Read documentation`, `Run code`, `Run tests`, `Ask colleague`, `Human review`, `CI result`.

**Worked example:** `examples/dev_illustrative_note.txt` coded as `examples/dev_episode_illustrative.json`.

## 5. Coding lenses and analysis layers

The lexicon is modular. Two kinds of plug-in sit on top of the core and the setting vocabularies.

- A **coding lens** (`lenses/<name>.json`) adds a layer that the researcher or the model codes while reading the note, from one theoretical perspective. It brings its own terms, coding rules and instructions for the model, and it can be switched off (`extract.py --lens`, or the checkboxes in the app). A map without the lens is complete.
- An **analysis layer** (`tools/layers/<name>.py`) is computed from a map by fixed rules and never written into it, so it re-runs on any corrected version. Each declares the lens it operationalizes and, if it reads a coding lens, which one it needs. Run them with `python3 analyse.py` or tick them in the app.

### 5.1 Coding lens: Argumentation labor (`argumentation`)

Toulmin's (1958) model of argument, with argumentation labor: the largely invisible work people do to rebuild, test, weigh or complete an argument when part of it breaks down, in four kinds (reconstructive, comparative, adjudicative, integrative), as theorized in prior work on AI-augmented radiology. A coding lens: it adds a layer to the map that the researcher or the model codes while reading the note. Switch it off when your study does not use this theory; the workflow and claims layers stand on their own.

**Rules:** Code a breakdown only where the note shows one; an empty list is a valid answer. Every breakdown names one Toulmin element, one status and at least one kind of labor. The same labor codes may also be put on the steps where that labor happens.

| Toulmin element | Meaning |
| --- | --- |
| `claim` | The conclusion asserted (a finding, a diagnosis, a fix). |
| `data` | The evidence the claim rests on. |
| `warrant` | Why the data supports the claim. |
| `backing` | What makes the warrant trustworthy (for an AI, how it was validated or trained). |
| `qualifier` | How strongly the claim is held (priority, confidence). |
| `rebuttal` | Conditions under which the claim would not hold. |

| Breakdown status | Meaning |
| --- | --- |
| `missing` | The element is not given at all (e.g. a flag with no reason). |
| `ambiguous` | The element is given but can be read more than one way. |
| `opaque` | The element exists but cannot be inspected. |
| `absent` | The reader would expect it and it is not there. |
| `unstable` | The element changes over time or between cases (e.g. after a model update). |
| `expanded` | The reader adds more of this element than usual (e.g. extra rebuttals). |
| `persistent` | The element stays open after sign-off (e.g. a rebuttal carried into the report). |

| Labor code | Meaning |
| --- | --- |
| `R` | Reconstructive: reverse-engineering a missing warrant |
| `C` | Comparative: testing own judgment against the machine, case by case |
| `A` | Adjudicative: deciding to trust or dismiss under false flags, drift, alerts |
| `I` | Integrative: synthesising machine output with history, physiology, trajectory |


### Analysis layers in this release

| Layer | Question | Theoretical lens | Needs |
| --- | --- | --- | --- |
| `labor_by_screen` | Where is argumentation labor done, and does it follow the AI? | Argumentation labor (Toulmin) | argumentation |
| `reachability` | Can a claim reach closure without an independent check? | Distributed cognition; epistemic trust as routing | – |

To add an analysis layer, copy `tools/layers/reachability.py`, change the rules, and give it a new name; the app and `analyse.py` find it automatically. To add a coding lens, copy `lenses/argumentation.json` and add its field to `schema/diagram.schema.json`.

## 6. Reading a rendered map

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
| [R] [C] [A] [I] | Argumentation labor at that step |
| “shows: …” | What the AI displayed |
| “PAC · CL” | In escalation rows: system shorthand and lane |

## 7. Changes

| Version | Change |
| --- | --- |
| 1.3 | Plug-in model: argumentation moved out of the core into the first coding lens; analysis layers added, with reachability and labor by screen as the first two; activities counted as independent checks listed in each setting. |
| 1.2 | Legal work added as a second extension domain with a synthetic example; extension examples relabelled as synthetic; product names replaced with generic ones and the gold set reduced to the three published vignettes, to protect the field site. |
| 1.1 | Lexicon split into a domain-neutral core and domain vocabularies; software development added as a second domain with a worked example; lane roles and AI roles make AI position work in any setting. |
| 1.0 | Every term defined; rules R1–R6 stated and enforced; Case 3 and Case 1 recoded; escalation levels assigned. |
| 0.2 | Aligned with the field notebook: lanes L, CL, CR, R; AI shape by screen; model and output fields; levels; session header. |
| 0.1 | First schema and seven maps from published figures. |
