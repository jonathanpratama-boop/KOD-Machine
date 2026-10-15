#!/usr/bin/env python3
"""Copy every completed agent result of the kod-next-move workflow out of its journal into
handoff/kod-next-move/outputs/<phase>/<label>.{json,md}. Idempotent; safe to re-run while the
workflow is live. Usage: python3 sync_outputs.py [journal.jsonl] [outputs_dir]"""
import json, os, sys, re
J = sys.argv[1] if len(sys.argv) > 1 else ("/root/.claude/projects/-home-user-KOD-Machine/74d3ac27-b8ad-5917-a6c3-ea51c410b250"
                                            "/subagents/workflows/wf_1f360293-1fd/journal.jsonl")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "outputs")
started, done, order = {}, {}, []
for line in open(J, encoding="utf-8"):
    try:
        r = json.loads(line)
    except json.JSONDecodeError:
        continue
    if r.get("type") == "started":
        started[r["key"]] = r; order.append(r["key"])
    elif r.get("type") == "result" and r["key"] in started:
        done[r["key"]] = r.get("result", r.get("output"))
def md(v, depth=0):
    if isinstance(v, dict):
        return "\n".join(f"{'#' * min(6, depth + 2)} {k}\n{md(x, depth + 1)}" for k, x in v.items())
    if isinstance(v, list):
        return "\n".join(("- " + md(x, depth + 1).replace("\n", "\n  ")) if not isinstance(x, (dict, list)) else md(x, depth + 1) for x in v)
    return str(v)
n = 0
for key in order:
    s = started[key]
    if key not in done:
        continue
    phase = s.get("phase", "misc"); label = re.sub(r"[^A-Za-z0-9._-]+", "_", s.get("label", s["agentId"]))
    d = os.path.join(OUT, phase); os.makedirs(d, exist_ok=True)
    v = done[key]
    with open(os.path.join(d, label + ".json"), "w", encoding="utf-8") as f:
        json.dump({"agentId": s["agentId"], "label": s.get("label"), "phase": phase, "result": v}, f, indent=1, ensure_ascii=False)
    with open(os.path.join(d, label + ".md"), "w", encoding="utf-8") as f:
        f.write(f"# {s.get('label')} ({phase}; agent {s['agentId']})\n\n" + (md(v) if not isinstance(v, str) else v) + "\n")
    n += 1
pending = [started[k].get("label") for k in order if k not in done]
print(f"synced {n} completed outputs to {os.path.abspath(OUT)}; pending: {pending}")
