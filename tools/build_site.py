"""Build the project web page (docs/index.html) from the current gold set.

The page is a single self-contained HTML file: copy it into your website
(served from docs/ by GitHub Pages). Re-run after editing gold
maps, core.json or a domain file.

Usage: python3 build_site.py [--repo https://github.com/you/dcog-lexicon]
"""
import argparse
import json

from lexicon import CORE, ROOT, domain, domain_names, lens, lens_names, load

# The site shows the three radiology vignettes from fieldwork (one per AI position); the full
# gold set stays in the repository.
GOLD_ORDER = ["vignette1_automated_triage", "vignette2_decision_support", "vignette3_second_opinion"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="https://anonymous.4open.science/r/dcog-lexicon-2026")
    ap.add_argument("-o", "--out", default=str(ROOT / "docs" / "index.html"))
    ap.add_argument("--fragment", default=None, help=argparse.SUPPRESS)
    args = ap.parse_args()
    names = ["radiology"] + [n for n in domain_names() if n != "radiology"]
    domains = {n: domain(n) for n in names}
    examples = {n: {"note": (ROOT / D["example"]["note"]).read_text(), "map": load(ROOT / D["example"]["map"])}
                for n, D in domains.items()}
    data = {
        "core": CORE,
        "lenses": {n: lens(n) for n in lens_names()},
        "domains": domains,
        "gold": [load(ROOT / "gold" / f"{g}.json") for g in GOLD_ORDER],
        "examples": examples,
        "example_prediction": load(ROOT / "examples" / "vignette3_predicted_example.json"),
    }
    # analysis layers: the page cannot run Python, so results are computed here for every published map
    from layers import describe, run_map_layers
    published = data["gold"] + [e["map"] for n, e in examples.items() if n != "radiology"]
    data["layers"] = [d for d in describe() if d["scope"] == "map"]
    data["layer_results"] = {m["id"]: run_map_layers(m) for m in published}
    from compare_episodes import compare as compare_episodes
    data["episode_pairs"] = {f"{x['id']}|{y['id']}": compare_episodes(x, y)
                             for x in published for y in published if x["id"] != y["id"]}
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = (ROOT / "site" / "template.html").read_text()
    html = html.replace("/*MAPDRAW*/", (ROOT / "site" / "mapdraw.js").read_text())
    html = html.replace("/*DATA*/", blob).replace("REPO_URL", args.repo)
    # full standalone document for a website (GitHub Pages etc.)
    head, _, body = html.partition("<header class=\"bar\">")
    doc = ("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
           "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">\n"
           + head + "</head>\n<body>\n<header class=\"bar\">" + body + "\n</body>\n</html>\n")
    with open(args.out, "w") as fh:
        fh.write(doc)
    print(f"wrote {args.out} ({len(doc) // 1024} KB)")
    if args.fragment:
        with open(args.fragment, "w") as fh:
            fh.write(html)


if __name__ == "__main__":
    main()
