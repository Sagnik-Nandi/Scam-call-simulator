"""Draw a scenario's call graph with Graphviz.

    python scripts/graph_diagram.py                      # digital_arrest -> docs/call_graph_digital_arrest.{dot,png,svg}
    python scripts/graph_diagram.py --scenario <id>

The picture is generated from scenarios/<id>/graph.json, so it never goes out of date.
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

LABELS = {"comply": "agree", "refuse": "refuse / doubt", "default": "no match", "leak": "says the OTP", "unknown": "no match"}
SOFT = {"greet", "parcel", "reassure", "isolate", "verify", "reassure_doubt"}
OTP = {"otp_demand", "otp_soft"}
PRESSURE = {"pushback", "final_early", "otp_pressure", "final_warning"}


def style(nid, node):
    if "terminal" in node:
        return ('fillcolor="#f8d7da"' if node["terminal"] == "lose" else 'fillcolor="#d4edda"') + ' shape=doublecircle fontsize=11'
    if nid in PRESSURE:
        return 'fillcolor="#ffd9b3" shape=box style="rounded,filled"'
    if nid in OTP:
        return 'fillcolor="#fff3b0" shape=box style="rounded,filled"'
    return 'fillcolor="#dbeafe" shape=box style="rounded,filled"'


def build_dot(graph):
    nodes = graph["nodes"]
    out = ['digraph call {', '  rankdir=TB; nodesep=0.45; ranksep=0.55; fontname="Helvetica";',
           '  node [fontname="Helvetica" fontsize=11 style=filled margin="0.12,0.07"];',
           '  edge [fontname="Helvetica" fontsize=9];',
           '  labelloc=t; fontsize=15; label="%s: how the call moves (blue = friendly helper, yellow = asking for the OTP, orange = pressure)";' % graph["title"]]
    for nid, n in nodes.items():
        tactics = ", ".join(n.get("tactics", []))
        notes = []
        if n.get("max_visits"):
            notes.append("used at most %d time%s" % (n["max_visits"], "" if n["max_visits"] == 1 else "s"))
        if n.get("remember"):
            notes.append("remembers the interrupted step")
        if n.get("show_otp"):
            notes.append("OTP card shown")
        label = nid + (("\\n[" + tactics + "]") if tactics else "") + ("".join("\\n(" + x + ")" for x in notes))
        if "terminal" in n:
            label = nid.replace("end_", "END: ")
        out.append('  %s [label="%s" %s];' % (nid, label, style(nid, n)))
    out.append('  RESUME [label="back to the step\\nthe user interrupted\\n(RESUME)" shape=diamond fillcolor="#e9ecef" fontsize=10];')
    out.append('  start [label="call starts" shape=plaintext style=""]; start -> %s;' % graph["start"])

    for nid, n in nodes.items():
        if "terminal" in n:
            continue
        grouped, selfloops = {}, []
        for intent, target in n["on"].items():
            if intent == "confused":
                continue                                    # drawn as one note below
            if target == "@clarify":
                selfloops.append(LABELS.get(intent, intent))
                continue
            target = "RESUME" if target == "@resume" else target
            grouped.setdefault(target, []).append(LABELS.get(intent, intent))
        for target, labels in grouped.items():
            uniq = list(dict.fromkeys(labels))
            if "agree" in uniq and "no match" in uniq:
                uniq = ["agree / no match"] + [x for x in uniq if x not in ("agree", "no match")]
            color = ' color="#b00020"' if target == "end_lose" else (' style=dashed color="#555555"' if target == "RESUME" else "")
            out.append('  %s -> %s [label="%s"%s];' % (nid, target, "\\n".join(uniq), color))
        if selfloops:
            out.append('  %s -> %s [label="%s: asks again\\n(up to %d times, then counted as a refusal)" style=dashed color="#888888"];'
                       % (nid, nid, "/".join(dict.fromkeys(selfloops)), graph.get("clarify_limit", 2)))
        if n.get("max_visits") and n.get("on_exhausted"):
            out.append('  %s -> %s [label="already used" style=dotted color="#b35900" fontcolor="#b35900"];' % (nid, n["on_exhausted"]))

    out.append('  RESUME -> verify [style=invis];')   # keeps the diamond near the middle; real target depends on the step
    inter = ", ".join(graph.get("interrupts", {}))
    out.append('  notes [shape=note fillcolor="#f1f3f5" fontsize=10 label="On any step (the step does not change):\\l'
               ' - confused reply: the caller explains again, same step\\l'
               ' - question (%s):\\l   an in-character answer; 3 in a row = counted as a refusal\\l'
               ' - unrecognised reply: asked once more, then the default branch\\l'
               ' - silence twice in a row: call ends (idle)\\l'
               ' - hang up: call ends (win)\\l"];' % inter.replace("_", " "))
    out.append("}")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="digital_arrest")
    a = ap.parse_args()
    graph = json.load(open(ROOT / "scenarios" / a.scenario / "graph.json", encoding="utf-8"))
    dot_text = build_dot(graph)
    out_dir = ROOT / "docs"
    out_dir.mkdir(exist_ok=True)
    base = out_dir / f"call_graph_{a.scenario}"
    base.with_suffix(".dot").write_text(dot_text, encoding="utf-8")
    dot = shutil.which("dot") or r"C:\Program Files\Graphviz\bin\dot.exe"
    for fmt in ("png", "svg"):
        subprocess.run([dot, f"-T{fmt}", "-Gdpi=130", str(base.with_suffix(".dot")), "-o", str(base.with_suffix("." + fmt))], check=True)
    print("wrote", base.with_suffix(".png"))


if __name__ == "__main__":
    sys.exit(main())
