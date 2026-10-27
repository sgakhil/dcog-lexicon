# Guide: running the tools

This guide is for people who have not run Python tools before. For what the notation means and how to code an episode by hand, read [LEXICON.md](LEXICON.md).

## Setup (once)

On Ubuntu or Debian:

```
sudo apt install python3-jsonschema graphviz
```

If drawing later fails with "no layout engine support for neato", also run `sudo apt install libgvplugin-neato-layout8 libgvplugin-pango8` and then `sudo dot -c`.

Commands go in the Terminal, inside the `tools` folder:

```
cd ~/Desktop/dcog-lexicon/tools
python3 validate.py ../gold/*.json
```

If the last line says `3/3 valid`, the setup works.

## Coding an episode by hand

1. Copy a gold file as a starting point: `cp ../gold/vignette2_decision_support.json ../gold/episode_fn045.json`.
2. Edit it in any text editor, following LEXICON.md §2. In VS Code (open the whole `dcog-lexicon` folder), press Ctrl+Space inside a value to see the allowed terms.
3. Check and draw it:
   ```
   python3 validate.py ../gold/episode_fn045.json
   python3 render.py ../gold/episode_fn045.json -o ../renders --layout levels
   ```

## Working in a setting other than radiology

Each map names its setting in a `"domain"` field. Two settings ship: `radiology` (the default) and `software_development`. To start a map in the second, copy `examples/dev_episode_illustrative.json`.

For a new setting, copy `domains/software_development.json` to, say, `domains/claims_processing.json` and replace its screens, systems, activities, AI tools and independent checks with ones from your fieldnotes (LEXICON.md §4.1 lists the six questions to answer). Then put `"domain": "claims_processing"` in your maps and add `--domain claims_processing` when you run `extract.py`. Nothing else changes.

After changing the gold set, a domain file or the core, refresh the generated files:

```
python3 build_codebook.py && python3 build_site.py && python3 make_editor_schema.py
```

## Use it from the browser instead of the terminal

From the `tools` folder run:

```
python3 app.py
```

Your browser opens a page at `http://localhost:8765`. Paste a fieldnote (or open a .txt file), choose the setting and the model, and press **Draft map**. The draft is drawn on the page with a list of any coding rules it breaks. You can correct it in the box below, re-check, save it to `predicted/`, download the drawing, or score it against a hand-coded map.

The app runs only on your computer: it does not listen on the network, the model is your local Ollama, and notes are saved only in `notes/`, which is never uploaded to git. Press Ctrl+C in the terminal to stop it.

## Plug-ins: coding lenses and analysis layers

The lexicon is modular. On top of the core (steps, links, claims) and the setting vocabularies sit two kinds of plug-in.

**Coding lenses** add a layer that you or the model code while reading the note, from one theoretical perspective. The first is **argumentation**: Toulmin breakdowns and argumentation labor (R, C, A, I), the largely invisible work of keeping an argument standing. It lives in `lenses/argumentation.json`. Switch it off when your study does not use it; the model then has a shorter set of instructions, which helps small models:

```
python3 extract.py ../notes/fn045.txt --lens               # workflow and claims only
python3 extract.py ../notes/fn045.txt --lens argumentation # with the argument layer (the default)
```

In the app, untick "Argumentation labor" before pressing Draft map.

**Analysis layers** are computed from a finished map and never written into it, so they re-run on any version: a fresh draft, a corrected draft or a hand-coded map. In the app, tick a layer above the drawing; from the terminal:

```
python3 analyse.py --list
python3 analyse.py ../gold/*.json ../predicted/*.json
```

Two layers ship as examples:

- **reachability** (lens: distributed cognition, trust as routing) asks whether a claim can travel from where it starts to where it closes without passing an independent check. Which activities count as checks is set in each setting's file (`check_activities` in `domains/<name>.json`).
- **labor_by_screen** (lens: argumentation) counts the argumentation labor on each screen and how much of it comes after an AI step. It needs the argumentation lens and says so if a map does not use it.

**Compare two episodes.** In the app's "Compare two episodes" card, or from the terminal, put two maps side by side:

```
python3 compare_episodes.py ../gold/vignette2_decision_support.json ../gold/vignette3_second_opinion.json
```

Within one setting, steps are matched by activity and screen; steps found in only one map are outlined in purple, and the two maps' claims, escalation, hand-offs and layer results are set side by side. Across settings the step names differ, so the comparison uses argumentation labor from the argumentation lens, which every setting shares. It gives no score: it shows how two episodes differ, not whether one is right.

To add a layer, copy `tools/layers/reachability.py`, change the rules and the name; the app and `analyse.py` find it automatically. To add a coding lens, copy `lenses/argumentation.json` and add its field to `schema/diagram.schema.json`.

## Test everything in one go

Once Ollama and a model are installed, run from the `tools` folder:

```
python3 selftest.py
```

It checks the setup, runs the tools without AI, has the model draft a map for each setting's worked example, and then runs a held-out test: the model writes a synthetic note from each radiology vignette and codes it without seeing the vignette. It writes `test_run/REPORT.md` with every result and score. On a laptop without a graphics card, allow 20–60 minutes; `python3 selftest.py --quick` takes a few minutes.

## What the AI parts do

| Tool | What goes in | What comes out | Why |
| --- | --- | --- | --- |
| `extract.py` | A fieldnote (`.txt`) | The AI's map of it (`.json`) | The AI codes your notes the way you do |
| `synthesize.py` | One of your maps | A realistic fake fieldnote, plus its answer key | Shareable test data with known right answers |
| `evaluate.py` | Answer keys + the AI's maps | Scores per layer | Shows where the AI matches you and where it fails |

Everything runs on your own computer through **Ollama**, a free program that runs open AI models locally. No fieldnote is sent anywhere.

## One-time setup: install Ollama and a model

1. Check how much memory your computer has:
   ```
   free -h
   ```
   Look at the "total" number in the "Mem" row.

2. Install Ollama:
   ```
   curl -fsSL https://ollama.com/install.sh | sh
   ```

3. Download a model. Pick by your memory:

   | Memory | Command | Notes |
   | --- | --- | --- |
   | 8 GB | `ollama pull qwen2.5:7b` | The default. Fine for testing |
   | 16 GB or more | `ollama pull qwen2.5:14b` | Noticeably better coding. Use this for the real results |
   | 32 GB or more | `ollama pull qwen2.5:32b` | Best of the three. Slow without a graphics card |

   The download is several gigabytes and happens once.

4. Check it works:
   ```
   ollama run qwen2.5:7b "Say hello"
   ```
   Type `/bye` to exit.

If you use a model other than `qwen2.5:7b`, add `--model qwen2.5:14b` (or whichever) to every command below.

## Task 1: Have the AI code one of your fieldnotes

1. Make a folder for notes and save a fieldnote as plain text:
   ```
   mkdir -p ../notes
   ```
   Paste one episode into a file such as `../notes/fn045.txt`, using any text editor. One episode per file.

2. Run:
   ```
   python3 extract.py ../notes/fn045.txt
   ```
   For a setting other than radiology, add `--domain software_development` (or your own domain name).

   On a laptop without a graphics card this takes about 1–5 minutes per note.

3. Look at what it made:
   ```
   python3 render.py ../predicted/fn045.json -o ../renders
   python3 render.py ../predicted/fn045.json -o ../renders --layout levels
   ```
   The second command draws it the way your notebook does: one row per escalation level.
   Open `../renders/pred_fn045.png`.

4. If you have also coded the same episode yourself (say `../gold/episode_fn045.json`), compare the two:
   ```
   python3 compare.py ../gold/episode_fn045.json ../predicted/fn045.json
   ```

Every run is recorded in `../predicted/logs/`: exact model version, prompt version, settings, and the AI's raw answer. That record is what makes the results reproducible for reviewers.

## Task 2: Make synthetic fieldnotes with known answers

1. A plain synthetic note from one of your maps:
   ```
   python3 synthesize.py ../gold/vignette2_decision_support.json
   ```
   This creates `../synthetic/notes/...txt` (the fake note) and `../synthetic/answers/...json` (the right answer). Open the note and read it. You are the best judge of whether it sounds like a real reading room.

2. Notes with traps: descriptions that are known to mislead a coder.

   | Trap | What the note does | What it tests |
   | --- | --- | --- |
   | `agreement_looks_checked` | Reader and AI agree, with confident words, but nothing is actually checked | Does the model mistake confident language for validation? |
   | `implicit_doubt` | Doubt shown only by behaviour (pausing, re-scrolling), never said | Can the AI see doubt that isn't spoken? |
   | `unresolved_flag` | An AI flag is set aside and never resolved | Does the AI wrongly close an open claim? |

   For example:
   ```
   python3 synthesize.py ../gold/*.json --trap agreement_looks_checked --variants 3
   ```
   Maps that don't fit a trap are skipped with a message; that is expected.

3. Build a small test set: plain versions of all three vignettes, plus each trap:
   ```
   python3 synthesize.py ../gold/*.json --variants 2
   python3 synthesize.py ../gold/*.json --trap agreement_looks_checked --variants 3
   python3 synthesize.py ../gold/*.json --trap implicit_doubt --variants 3
   python3 synthesize.py ../gold/*.json --trap unresolved_flag --variants 3
   ```

## Task 3: Score the AI on the synthetic set

```
python3 extract.py ../synthetic/notes/*.txt -o ../predicted
python3 evaluate.py ../synthetic/answers ../predicted -o ../results.csv
```

You get a mean score for each layer, a breakdown by trap, and a spreadsheet (`results.csv`) with one row per note.

**How to read it:** 1.00 means the AI's map matches the answer key; 0.00 means it missed completely. The proposal predicts high scores on the `workflow` lines and lower scores on the claims (`routing`) and `argument` lines, especially for `agreement_looks_checked`. Whatever the numbers turn out to be, they are your first results.

## For a fair comparison

- **Write the synthetic notes with one model and code them with a different one**, so the AI isn't grading its own writing. For example, add `--model llama3.1:8b` to `synthesize.py` and keep `qwen2.5` for `extract.py`.
- **Read some synthetic notes yourself before trusting the scores.** If a note doesn't actually contain the events in its answer key, the problem is the note, not the extraction. Delete it.
- **Keep real fieldnotes out of the public repository.** `notes/` and `predicted/` from real data stay on your computer. Only the synthetic set goes public.

## When something goes wrong

| Message | What to do |
| --- | --- |
| `Could not reach Ollama` | Run `ollama serve` in another Terminal window, or restart the computer |
| `Model ... is not downloaded` | Run the `ollama pull` command it shows |
| `saved with N problem(s)` | The AI broke a rule even after one correction. The file is kept so you can see what it did wrong. That is itself data |
| Very slow | Use a smaller model, or run overnight on the whole folder |
