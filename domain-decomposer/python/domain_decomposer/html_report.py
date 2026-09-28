from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


def render(output_path: str | Path, graph: Any, labels: dict[str, int], modularity: float, feature_names: list[str], coverage: dict[str, Any], services: dict[str, Any] | None = None) -> None:
    services = services or {"anchors": {}, "groups": {}, "shared": [], "cross_boundary": []}
    nodes = []
    for node_id, data in graph.nodes(data=True):
        nodes.append({"id": node_id, "label": data.get("fqcn", node_id), "cluster": labels.get(node_id, 0), "package": data.get("package", "")})
    edges = [{"source": left, "target": right, "weight": round(float(data.get("weight", 0.0)), 5)} for left, right, data in graph.edges(data=True)]
    clusters = {}
    for node in nodes:
        clusters.setdefault(str(node["cluster"]), []).append(node["label"])
    for node in nodes:
        node["service"] = services.get("assignments", {}).get(node["id"], "shared")
    payload = {"nodes": nodes, "edges": edges}
    cluster_rows = "".join(f"<tr><td>{html.escape(name)}</td><td>{len(items)}</td><td>{html.escape(', '.join(items))}</td></tr>" for name, items in sorted(clusters.items(), key=lambda item: int(item[0])))
    coverage_rows = "".join(f"<li><b>{html.escape(str(name))}</b>: {html.escape(str(value))}</li>" for name, value in coverage.items())
    service_rows = "".join(f"<tr><td>{html.escape(services['anchors'].get(anchor_id, anchor_id))}</td><td>{len(members)}</td><td>{html.escape(', '.join(graph.nodes[node_id].get('fqcn', node_id) for node_id in members))}</td></tr>" for anchor_id, members in sorted(services.get("groups", {}).items(), key=lambda item: services.get("anchors", {}).get(item[0], item[0])))
    document = f'''<!doctype html><html><head><meta charset="utf-8"><title>Domain Decomposition Report</title>
<style>body{{font:14px system-ui;margin:24px;color:#17202a}}h1{{margin-bottom:4px}}.metric{{display:inline-block;background:#eef3f7;padding:12px 18px;margin:8px 8px 18px 0;border-radius:6px}}#graph{{border:1px solid #cbd5dc;width:100%;height:620px}}table{{border-collapse:collapse;width:100%}}td,th{{border-bottom:1px solid #d7dde2;padding:8px;text-align:left;vertical-align:top}}input{{padding:9px;width:320px}}.muted{{color:#65727d}}</style></head><body>
<h1>Domain Decomposition</h1><p class="muted">Cosine similarity is the only edge-weight formula.</p>
<div class="metric"><b>Initial Louvain clusters</b><br>{len(clusters)}</div><div class="metric"><b>Final services</b><br>{len(services.get('groups', {}))}</div><div class="metric"><b>Nodes</b><br>{len(nodes)}</div><div class="metric"><b>Edges</b><br>{len(edges)}</div><div class="metric"><b>Modularity</b><br>{modularity:.4f}</div>
<h2>Graph</h2><input id="search" placeholder="Filter classes or packages"><canvas id="graph" width="1200" height="620"></canvas>
<h2>Initial Louvain clusters</h2><p class="muted">These are the raw graph communities before backend service-boundary assignment.</p><table><thead><tr><th>Cluster</th><th>Nodes</th><th>Members</th></tr></thead><tbody>{cluster_rows}</tbody></table>
<h2>Final service boundaries</h2><p class="muted">Supporting classes are assigned to the strongest service anchor. Shared classes: {len(services.get('shared', []))}; ambiguous cross-boundary classes: {len(services.get('cross_boundary', []))}.</p><table><thead><tr><th>Service</th><th>Nodes</th><th>Members</th></tr></thead><tbody>{service_rows}</tbody></table>
<h2>Signal coverage</h2><ul>{coverage_rows}</ul><p class="muted">Feature dimensions: {html.escape(', '.join(feature_names))}</p>
<script>const data={json.dumps(payload)};const canvas=document.getElementById('graph'),ctx=canvas.getContext('2d'),search=document.getElementById('search');let positions={{}};function color(c){{const palette=['#146c94','#b85c38','#4d9078','#7b5ea7','#d17a22','#3b5b92','#9b3d58'];return palette[(c-1)%palette.length]||'#777'}}function draw(){{ctx.clearRect(0,0,canvas.width,canvas.height);const query=search.value.toLowerCase();const visible=new Set(data.nodes.filter(n=>!query||n.label.toLowerCase().includes(query)||n.package.toLowerCase().includes(query)).map(n=>n.id));data.nodes.forEach((n,i)=>positions[n.id]={{x:70+(i%12)*92,y:55+Math.floor(i/12)*82}});ctx.lineWidth=1;data.edges.forEach(e=>{{if(!visible.has(e.source)||!visible.has(e.target))return;const a=positions[e.source],b=positions[e.target];ctx.strokeStyle='#c6ced5';ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke()}});data.nodes.forEach(n=>{{if(!visible.has(n.id))return;const p=positions[n.id];ctx.fillStyle=color(n.cluster);ctx.beginPath();ctx.arc(p.x,p.y,8,0,Math.PI*2);ctx.fill();ctx.fillStyle='#17202a';ctx.font='11px system-ui';ctx.fillText(n.label.split('.').pop(),p.x+11,p.y+4)}})}}search.addEventListener('input',draw);draw();</script></body></html>'''
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(document, encoding="utf-8")
