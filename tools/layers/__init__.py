"""Analysis layers: computed views of maps that sit beside them, never inside them.

The coded layers (workflow, claims, argument, labor) are judgments saved in each
map. Analysis layers are derived from a map by fixed rules, so they can be re-run
on any version of it: a fresh draft, a corrected draft, or a hand-coded map.

Each layer is one module in this folder that defines:

    NAME        short identifier, e.g. "reachability"
    LABEL       one-line question the layer answers
    SCOPE       "map" (zoom in: one episode) or "corpus" (zoom out: a set of maps)
    VERSION     bumped whenever the rules change; recorded with every result
    LENS        the theoretical perspective the layer operationalizes
    REQUIRES    (optional) coding lenses the map must use, e.g. ["argumentation"]
    run(...)    map layers: run(map, vocab); corpus layers: run(maps, vocab_of)

and returns a dict with "summary", optional "rows" (a table) and optional
"marks" (what to highlight on the drawing):

    {"on": "node", "id": "...", "tag": "...", "level": "info|warn"}
    {"on": "edge", "from": "...", "to": "...", "tag": "...", "level": "info|warn"}
    {"on": "claim", "id": "...", "tag": "...", "level": "info|warn"}

New layers are found automatically; nothing else needs to change.
"""
import importlib
import pkgutil
from pathlib import Path

_HERE = Path(__file__).parent


def available():
    """All layer modules in this folder, keyed by NAME."""
    out = {}
    for info in pkgutil.iter_modules([str(_HERE)]):
        if info.name.startswith("_"):
            continue
        mod = importlib.import_module(f"layers.{info.name}")
        if hasattr(mod, "NAME") and hasattr(mod, "run"):
            out[mod.NAME] = mod
    return out


def describe():
    return [{"name": m.NAME, "label": m.LABEL, "scope": m.SCOPE, "version": m.VERSION,
             "lens": getattr(m, "LENS", ""), "requires": getattr(m, "REQUIRES", []),
             "doc": (m.__doc__ or "").strip()} for m in available().values()]


def run_map_layers(m, names=None):
    """Run the chosen map-scope layers on one map; returns {name: result}."""
    from lexicon import domain_of, lenses_of, vocab
    v = vocab(domain_of(m))
    used = set(lenses_of(m))
    out = {}
    for name, mod in available().items():
        if mod.SCOPE != "map" or (names and name not in names):
            continue
        missing = [l for l in getattr(mod, "REQUIRES", []) if l not in used]
        if missing:
            out[name] = {"layer": name, "version": mod.VERSION, "rows": [], "marks": [],
                         "summary": {"skipped": f"this map does not use the {', '.join(missing)} lens"}}
            continue
        try:
            res = mod.run(m, v)
        except Exception as e:  # a broken map should not crash the app
            res = {"summary": {"error": str(e)}, "rows": [], "marks": []}
        res["layer"], res["version"] = name, mod.VERSION
        out[name] = res
    return out
