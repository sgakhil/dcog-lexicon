"""Render a diagram to SVG/PNG with Graphviz.

Two layouts:
  lanes  (default)  four screen lanes left to right (L, CL, CR, R), as on the desk
  levels            the notebook's own layout: each row is one escalation level,
                    read left to right; rows are separated where a 'why?' or
                    'Doubts?' opened the next level of checking

Conventions follow the notebook: dashed border = AI element (square corners for
AI in the worklist, rounded for AI in the viewer), double border = sign-off
(closure), bold border = entry point, dashed arrow = doubt or interrogation,
dotted arrow = institutional loop, [R]/[C]/[A]/[I] = argumentation labor.

Usage: python3 render.py ../gold/vignette1_automated_triage.json -o ../renders
       python3 render.py ../gold/*.json -o ../renders --layout levels
"""
import argparse
import textwrap
import subprocess
from html import escape
from pathlib import Path

from lexicon import domain_of, load, vocab

def lane_title(d, lane):
    return f"{vocab(domain_of(d))['lanes'][lane]['title']} ({lane})"


def lane_fill(d, lane):
    return "#dceef8" if vocab(domain_of(d))["lanes"][lane]["role"] == "record" else "#e3f1dc"


def sys_short(d, system):
    entry = vocab(domain_of(d))["systems"].get(system, {})
    return entry.get("short", system) if isinstance(entry, dict) else system
EDGE_STYLE = {"action": "solid", "doubt": "dashed", "institutional": "dotted"}
EDGE_COLOR = {"action": "#2b4a6f", "doubt": "#b3261e", "institutional": "#6b5b95"}
STATE_SHORT = {"provisional_acceptance": "accept", "validation": "validate",
               "consultation": "consult", "deferral": "defer"}


def node_label(n, lane_tag=False, d=None):
    rows = []
    if lane_tag:
        tag = sys_short(d, n["system"]) if d else n["system"]
        if n.get("ai_model") and n["ai_model"] not in ("triage", "widget", "other"):
            tag += "." + n["ai_model"]
        rows.append(f'<FONT POINT-SIZE="8" COLOR="#555555">{escape(tag)} · {escape(n["lane"])}</FONT>')
    rows.append(f"<B>{escape(n['activity'])}</B>")
    if n.get("detail"):
        rows += [f"<I>{escape(t)}</I>" for t in textwrap.wrap(n["detail"], 28)]
    tail = f"({escape(n['system'])})"
    if n.get("labor"):
        tail += "  " + " ".join(f"[{l}]" for l in n["labor"])
    if n.get("ai_output"):
        rows += [f'<FONT POINT-SIZE="9" COLOR="#0b6e99">{escape(t)}</FONT>'
                 for t in textwrap.wrap("shows: " + n["ai_output"], 30)]
    rows.append(f'<FONT POINT-SIZE="9">{tail}</FONT>')
    if n.get("practices"):
        ps = n["practices"]
        for i in range(0, len(ps), 3):
            rows.append(f'<FONT POINT-SIZE="8" COLOR="#555555">{escape(" · ".join(ps[i:i+3]))}</FONT>')
    return "<" + "<BR/>".join(rows) + ">"


LANE_W, LANE_GAP, ROW_H = 2.7, 0.15, 1.05   # inches


def layout(d):
    """Place nodes on a lane x row grid: x = lane, y = BFS depth from entry."""
    lanes = list(vocab(domain_of(d))["lanes"])
    adj = {}
    for e in d["edges"]:
        adj.setdefault(e["from"], []).append(e["to"])
    depth = {}
    frontier = [n["id"] for n in d["nodes"] if n.get("entry")]
    for nid in frontier:
        depth[nid] = 0
    while frontier:
        nxt = []
        for nid in frontier:
            for t in adj.get(nid, []):
                if t not in depth:
                    depth[t] = depth[nid] + 1
                    nxt.append(t)
        frontier = nxt
    # unreached nodes (e.g., institutional sources) sit one row above their target
    for n in d["nodes"]:
        if n["id"] not in depth:
            targets = [depth[t] for t in adj.get(n["id"], []) if t in depth]
            depth[n["id"]] = max(min(targets) - 1, 0) if targets else 0
    used, pos = set(), {}
    for n in sorted(d["nodes"], key=lambda n: depth[n["id"]]):
        row, col = depth[n["id"]], lanes.index(n["lane"])
        while (row, col) in used:
            row += 1
        used.add((row, col))
        pos[n["id"]] = (col * (LANE_W + LANE_GAP) + LANE_W / 2, -row * ROW_H)
    return pos


def node_attrs(n):
    style = ["filled"]
    attrs = []
    if not (n.get("is_ai") and n.get("_queue")):   # notebook: square Ai = queue lane, rounded = work lanes
        style.append("rounded")
    if n.get("is_ai"):
        style.append("dashed")
        attrs.append('color="#0b6e99"')
    if n.get("closes_claim"):
        attrs.append("peripheries=2")
    if n.get("entry"):
        attrs.append("penwidth=2")
    attrs.append(f'style="{",".join(style)}"')
    return attrs


def edges_and_legend(d, legend_x, legend_y_top):
    out = []
    for e in d["edges"]:
        lbl = f', xlabel="{escape(e["label"])}"' if e.get("label") else ""
        out.append(f'  {e["from"]} -> {e["to"]} [style={EDGE_STYLE[e["type"]]}, '
                   f'color="{EDGE_COLOR[e["type"]]}", fontcolor="{EDGE_COLOR[e["type"]]}"{lbl}];')
    rows = []
    for c in d["routing"]:
        path = " → ".join(STATE_SHORT[s] for s in c["states"])
        flag = "  ⚠ unexamined agreement" if c.get("unexamined_agreement") else ""
        rows.append(f"{escape(c['claim'])} [{c['claim_source']}]: {path}"
                    f"{' (closed)' if c['closed'] else ' (open)'}{flag}")
    for b in d.get("argument", []):
        rows.append(f"Toulmin {b['element']}: {b['status']} → " + " ".join(f"[{l}]" for l in b["labor"]))
    legend = '<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="1">' + \
        '<TR><TD ALIGN="LEFT"><B>Routing and argument layers</B></TD></TR>' + \
        "".join(f'<TR><TD ALIGN="LEFT">{r}</TD></TR>' for r in rows) + "</TABLE>>"
    ly = legend_y_top - 0.25 - 0.18 * len(rows)
    out.append(f'  legend [shape=note, style=filled, fillcolor="#fffbe6", width=0, label={legend}, '
               f'pos="{legend_x*72:.0f},{ly*72:.0f}"];')
    return out


def sequence(d):
    """Breadth-first order from the entry node(s); unreached nodes keep file order at the end."""
    adj = {}
    for e in d["edges"]:
        adj.setdefault(e["from"], []).append(e["to"])
    order, seen = [], set()
    queue = [n["id"] for n in d["nodes"] if n.get("entry")]
    while queue:
        nid = queue.pop(0)
        if nid in seen:
            continue
        seen.add(nid)
        order.append(nid)
        queue += adj.get(nid, [])
    rest = [n["id"] for n in d["nodes"] if n["id"] not in seen]
    feeds = [nid for nid in rest if adj.get(nid)]           # e.g. an AI column feeding the worklist
    return feeds + order + [nid for nid in rest if nid not in feeds]


COL_W, LEVEL_H = 2.75, 1.75   # inches


def mark_queue(d):
    lanes = vocab(domain_of(d))["lanes"]
    for n in d["nodes"]:
        n["_queue"] = lanes.get(n["lane"], {}).get("role") == "queue"


def to_dot_levels(d):
    mark_queue(d)
    nodes = {n["id"]: n for n in d["nodes"]}
    levels = sorted({n.get("level", 0) for n in d["nodes"]})
    col = {lv: 0 for lv in levels}
    pos, colof = {}, {}
    preds = {}
    for e in d["edges"]:
        preds.setdefault(e["to"], []).append(e["from"])
    for nid in sequence(d):
        lv = nodes[nid].get("level", 0)
        c = col[lv]
        if lv > 0:   # an escalation starts under the step that triggered it
            up = [colof[p] for p in preds.get(nid, []) if p in colof and nodes[p].get("level", 0) < lv]
            if up:
                c = max(c, max(up))
        colof[nid] = c
        pos[nid] = (1.7 + c * COL_W + 1.2, -levels.index(lv) * LEVEL_H)
        col[lv] = c + 1
    width = 1.7 + max(col.values()) * COL_W + 0.4
    out = ['digraph G {',
           '  graph [fontname="Helvetica", fontsize=11, splines=true, outputorder=nodesfirst];',
           '  node [shape=box, style="rounded,filled", fillcolor=white, fontname="Helvetica", fontsize=10, color="#2b4a6f", width=2.1];',
           '  edge [fontname="Helvetica", fontsize=8];',
           f'  title [shape=plaintext, style="", width=0, label=<<B>{escape(d["title"])}</B>>, pos="{width/2*72:.0f},{1.25*72:.0f}"];']
    for i, lv in enumerate(levels):
        y = -i * LEVEL_H
        name = "default read" if lv == 0 else f"escalation {lv}"
        out.append(f'  lvl{i} [shape=plaintext, style="", width=0, fontsize=10, fontcolor="#555555", '
                   f'label=<<B>Level {lv}</B><BR/>{name}>, pos="{0.7*72:.0f},{y*72:.0f}"];')
        if i:
            out.append(f'  why{i} [shape=plaintext, style="", width=0, fontsize=10, fontcolor="#b3261e", label="why?", '
                       f'pos="{0.7*72:.0f},{(y + LEVEL_H/2)*72:.0f}"];')
            out.append(f'  rule{i} [shape=box, style=filled, fillcolor="#e4e4e4", color="#e4e4e4", fixedsize=true, margin=0, '
                       f'width={width-1.8:.2f}, height=0.01, label="", pos="{(1.7+(width-1.8)/2)*72:.0f},{(y + LEVEL_H/2)*72:.0f}"];')
    for nid, (x, y) in pos.items():
        n = nodes[nid]
        out.append(f'  {nid} [label={node_label(n, lane_tag=True, d=d)}, {", ".join(node_attrs(n))}, pos="{x*72:.0f},{y*72:.0f}"];')
    out += edges_and_legend(d, width / 2, -(len(levels) - 1) * LEVEL_H - 0.45)
    out.append("}")
    return "\n".join(out)


def to_dot(d):
    mark_queue(d)
    pos = layout(d)
    rows_used = max(-y for _, y in pos.values()) / ROW_H + 1
    lane_h = rows_used * ROW_H + 0.5
    top = 0.75
    out = ['digraph G {',
           '  graph [fontname="Helvetica", fontsize=11, splines=true, outputorder=nodesfirst];',
           '  node [shape=box, style="rounded,filled", fillcolor=white, fontname="Helvetica", fontsize=10, color="#2b4a6f", width=2.3];',
           '  edge [fontname="Helvetica", fontsize=8];',
           f'  title [shape=plaintext, style="", label=<<B>{escape(d["title"])}</B>>, pos="{2*(LANE_W+LANE_GAP)*72:.0f},{(top+0.45)*72:.0f}"];']
    lanes = list(vocab(domain_of(d))["lanes"])
    for i, lane in enumerate(lanes):
        cx = i * (LANE_W + LANE_GAP) + LANE_W / 2
        cy = top - lane_h / 2
        out.append(f'  lane_{lane} [shape=box, style=filled, fillcolor="{lane_fill(d, lane)}", color="#999999", '
                   f'width={LANE_W}, height={lane_h:.2f}, fixedsize=true, label="{lane_title(d, lane)}", '
                   f'labelloc=t, fontsize=11, pos="{cx*72:.0f},{cy*72:.0f}"];')
    for n in d["nodes"]:
        attrs = node_attrs(n)
        x, y = pos[n["id"]]
        attrs.append(f'pos="{x*72:.0f},{(y-0.25)*72:.0f}"')
        out.append(f'  {n["id"]} [label={node_label(n)}, {", ".join(attrs)}];')
    out += edges_and_legend(d, 2 * (LANE_W + LANE_GAP), top - lane_h)
    out.append("}")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("-o", "--outdir", default="renders")
    ap.add_argument("--formats", default="svg,png")
    ap.add_argument("--layout", choices=["lanes", "levels"], default="lanes")
    args = ap.parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    for f in args.files:
        d = load(f)
        name = d["id"] + ("" if args.layout == "lanes" else "_levels")
        dot_path = outdir / f"{name}.dot"
        dot_path.write_text(to_dot(d) if args.layout == "lanes" else to_dot_levels(d))
        for fmt in args.formats.split(","):
            out = str(outdir / f"{name}.{fmt}")
            for extra in ([], ["-Gsplines=curved"], ["-Gsplines=line"]):   # fall back if spline routing fails
                r = subprocess.run(["neato", "-n2", *extra, f"-T{fmt}", str(dot_path), "-o", out],
                                   stderr=subprocess.DEVNULL)
                if r.returncode == 0:
                    break
            else:
                raise SystemExit(f"Graphviz could not draw {name}")
        dot_path.unlink()
        print(f"rendered {name}")


if __name__ == "__main__":
    main()
