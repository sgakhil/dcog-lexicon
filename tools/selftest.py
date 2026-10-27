"""Check that the whole toolkit works on this computer, including the local AI model.

Runs in four parts and writes a report you can share (test_run/REPORT.md):

  1. Setup     Python packages, Graphviz, Ollama and the model
  2. Offline   checker, drawing, scoring and export on the hand-coded maps (no AI)
  3. Examples  the model drafts a map for each setting's worked example note.
               These notes are also shown to the model as its example, so high
               scores here only prove the mechanics work, not accuracy.
  4. Held-out  the model writes a synthetic note for each radiology vignette, then
               codes it without seeing the answer; the draft is scored against
               the vignette. This is the honest test.

Usage (from the tools folder):
    python3 selftest.py                    # everything, default model
    python3 selftest.py --model llama3.1:8b
    python3 selftest.py --writer llama3.1:8b --model qwen2.5:7b   # different writer and coder
    python3 selftest.py --quick            # parts 1-3 with one example note only

Nothing leaves your computer. Outputs go to ../test_run/ (excluded from git).
"""
import argparse
import json
import platform
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "test_run"
PY = sys.executable
report = []


def say(line=""):
    print(line, flush=True)
    report.append(line)


def run(args, label, timeout=None):
    """Run a tool, echo its output, return (ok, seconds, output)."""
    t0 = time.time()
    try:
        p = subprocess.run([PY, *args], cwd=ROOT / "tools", capture_output=True, text=True, timeout=timeout)
        out, ok = (p.stdout + p.stderr).strip(), p.returncode == 0
    except subprocess.TimeoutExpired:
        out, ok = "timed out", False
    dt = round(time.time() - t0, 1)
    print(out)
    say(f"- {'PASS' if ok else 'FAIL'}  {label}  ({dt} s)")
    if not ok:
        say("  ```\n  " + "\n  ".join(out.splitlines()[-8:]) + "\n  ```")
    return ok, dt, out


def scores_of(ref, pred):
    sys.path.insert(0, str(ROOT / "tools"))
    from compare import score
    from lexicon import load
    s = score(load(ref), load(pred))
    return {k: v["f1"] for k, v in s.items()}


def table(rows):
    keys = ["workflow.nodes", "workflow.edges", "workflow.ai_nodes", "routing.state_paths",
            "routing.unexamined_agreement", "argument.breakdowns", "argument.labor"]
    head = ["note", "steps", "links", "AI steps", "claim paths", "unexamined agr.", "breakdowns", "labor"]
    say("| " + " | ".join(head) + " |")
    say("|" + " --- |" * len(head))
    for name, s in rows:
        say(f"| {name} | " + " | ".join(f"{s[k]:.2f}" if s.get(k) is not None else "–" for k in keys) + " |")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default=None, help="model that codes notes (default: DCOG_MODEL or qwen2.5:7b)")
    ap.add_argument("--writer", default=None, help="model that writes the synthetic notes (default: same as --model)")
    ap.add_argument("--quick", action="store_true", help="skip the held-out test and code only one example note")
    args = ap.parse_args()
    sys.path.insert(0, str(ROOT / "tools"))
    from llm import DEFAULT_MODEL, OLLAMA_URL
    model = args.model or DEFAULT_MODEL
    writer = args.writer or model
    OUT.mkdir(exist_ok=True)

    say("# dcog-lexicon self-test")
    say(f"{time.strftime('%Y-%m-%d %H:%M')} · Python {platform.python_version()} · {platform.system()} {platform.machine()}")
    say(f"Coding model: `{model}` · writing model: `{writer}`")
    say()

    # 1. setup ---------------------------------------------------------------
    say("## 1. Setup")
    problems = []
    try:
        import jsonschema  # noqa: F401
        say("- PASS  jsonschema installed")
    except ImportError:
        problems.append("jsonschema"); say("- FAIL  jsonschema missing: sudo apt install python3-jsonschema")
    if shutil.which("dot"):
        say("- PASS  Graphviz installed")
    else:
        problems.append("graphviz"); say("- FAIL  Graphviz missing: sudo apt install graphviz")
    models = []
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=10) as r:
            models = [m["name"] for m in json.loads(r.read()).get("models", [])]
        say(f"- PASS  Ollama running at {OLLAMA_URL}; models: {', '.join(models) or 'none'}")
    except Exception as e:
        problems.append("ollama"); say(f"- FAIL  Ollama not reachable at {OLLAMA_URL} ({e}). Start it with: ollama serve")
    for m in {model, writer}:
        if models and m not in models and f"{m}:latest" not in models:
            problems.append(m); say(f"- FAIL  model `{m}` not downloaded. Run: ollama pull {m}")
    try:
        mem = [l for l in open("/proc/meminfo") if l.startswith("MemTotal")][0].split()[1]
        say(f"- INFO  memory: {int(mem) // 1048576} GB")
    except Exception:
        pass
    if problems:
        say("\nFix the items above and run again.")
        (OUT / "REPORT.md").write_text("\n".join(report) + "\n")
        return 1
    say()

    # 2. offline tools --------------------------------------------------------
    say("## 2. Tools without AI")
    maps = sorted(str(p) for p in (ROOT / "gold").glob("*.json")) + sorted(str(p) for p in (ROOT / "examples").glob("*.json"))
    run(["validate.py", *maps], f"checker on {len(maps)} maps")
    run(["render.py", *maps[:1], "-o", str(OUT / "renders"), "--layout", "levels"], "drawing a map")
    run(["compare.py", str(ROOT / "gold/vignette3_second_opinion.json"), str(ROOT / "examples/vignette3_predicted_example.json")], "scoring")
    run(["export_eventlog.py", *maps, "-o", str(OUT / "eventlog.csv")], "event-log export")
    ok, dt, out = run(["analyse.py", str(ROOT / "examples/night_head_ct_synthetic.json"), "--layer", "reachability"],
                      "analysis layer: reachability")
    expected = "every route passes a check" in out and "can close unchecked" in out
    say(f"- {'PASS' if expected else 'FAIL'}  reachability gives the known answer on the head-CT test map")
    ok, dt, out = run(["analyse.py", str(ROOT / "examples/night_head_ct_synthetic.json"), "--layer", "labor_by_screen"],
                      "analysis layer: labor by screen")
    say(f"- {'PASS' if 'labor_codes=3' in out else 'FAIL'}  labor by screen gives the known answer on the head-CT test map")
    say()

    # 3. worked examples -----------------------------------------------------
    say("## 3. Model drafts the worked examples (mechanics check)")
    say("These notes are also the model's example, so scores should be high. Low scores here mean something is broken.")
    sys.path.insert(0, str(ROOT / "tools"))
    from lexicon import domain, domain_names
    rows = []
    names = ["legal"] if args.quick else domain_names()
    for dom in names:
        ex = domain(dom)["example"]
        ok, dt, out = run(["extract.py", str(ROOT / ex["note"]), "--domain", dom, "--model", model,
                           "-o", str(OUT / "examples")], f"{dom}: draft from {Path(ex['note']).name}")
        pred = OUT / "examples" / (Path(ex["note"]).stem + ".json")
        if ok and pred.exists():
            rows.append((dom, scores_of(ROOT / ex["map"], pred)))
    if rows:
        table(rows)
    say()

    # 4. held-out test --------------------------------------------------------
    if not args.quick:
        say("## 4. Held-out test on the radiology vignettes")
        say(f"`{writer}` writes a note from each vignette; `{model}` codes it without seeing the vignette.")
        ans, notes, preds = OUT / "synthetic" / "answers", OUT / "synthetic" / "notes", OUT / "heldout"
        run(["synthesize.py", *sorted(str(p) for p in (ROOT / "gold").glob("*.json")), "--model", writer,
             "-o", str(OUT / "synthetic")], "writing 3 synthetic notes")
        rows = []
        for note in sorted(notes.glob("*.txt")):
            ok, dt, out = run(["extract.py", str(note), "--domain", "radiology", "--model", model, "-o", str(preds)],
                              f"coding {note.name}")
            if ok and (preds / f"{note.stem}.json").exists():
                rows.append((note.stem.replace("syn_", "").replace("_none_v1", ""),
                             scores_of(ans / f"{note.stem}.json", preds / f"{note.stem}.json")))
        if rows:
            table(rows)
            say()
            say("Read the synthetic notes in test_run/synthetic/notes/ before trusting these scores: "
                "if a note leaves out a step, the draft cannot be expected to find it.")
        say()

    say("## Files")
    say("Drafts, logs (with model digest and timings) and this report are in `test_run/`.")
    (OUT / "REPORT.md").write_text("\n".join(report) + "\n")
    print(f"\nReport written to {OUT / 'REPORT.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
