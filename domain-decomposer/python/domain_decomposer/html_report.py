from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


def render(output_path: str | Path, graph: Any, labels: dict[str, int], modularity: float, feature_names: list[str], coverage: dict[str, Any], services: dict[str, Any] | None = None, candidate_domains: dict[str, Any] | None = None) -> None:
    services = services or {"anchors": {}, "groups": {}, "shared": [], "cross_boundary": []}
    candidate_domains = candidate_domains or {"domains": [], "assignments": {}, "cross_domain_dependencies": [], "review_required_count": 0}
    domain_by_id = {domain["id"]: domain for domain in candidate_domains.get("domains", [])}
    nodes = []
    for node_id, data in graph.nodes(data=True):
        cluster_id = labels.get(node_id, 0)
        nodes.append({"id": node_id, "label": data.get("fqcn", node_id), "cluster": cluster_id, "package": data.get("package", ""), "domain": domain_by_id.get(cluster_id, {}).get("name", f"Candidate domain {cluster_id}")})
    edges = [{"source": left, "target": right, "weight": round(float(data.get("weight", 0.0)), 5), "signals": data.get("signal_scores", {})} for left, right, data in graph.edges(data=True)]
    clusters = {}
    for node in nodes:
        clusters.setdefault(str(node["cluster"]), []).append(node["label"])
    payload = {"nodes": nodes, "edges": edges}
    cluster_rows = "".join(f"<tr><td>{html.escape(name)}</td><td>{len(items)}</td><td>{html.escape(', '.join(items))}</td></tr>" for name, items in sorted(clusters.items(), key=lambda item: int(item[0])))
    coverage_rows = "".join(f"<li><b>{html.escape(str(name))}</b>: {html.escape(str(value))}</li>" for name, value in coverage.items())
    domain_rows = []
    ambiguous_rows = []
    for domain in candidate_domains.get("domains", []):
        anchor_names = domain.get("anchor_names", [])
        member_names = [facts_name for facts_name in (graph.nodes[node_id].get("fqcn", node_id) for node_id in domain.get("members", []))]
        reasons = domain.get("review_reasons", [])
        status = "Review required" if domain.get("review_required") else "Provisional"
        member_list = "".join(f"<li>{html.escape(name)}</li>" for name in member_names)
        reason_list = "".join(f"<li>{html.escape(reason)}</li>" for reason in reasons)
        domain_rows.append(
            f"<tr><td>{domain.get('id', '')}</td><td><strong>{html.escape(str(domain.get('name', 'Candidate domain')))}</strong></td>"
            f"<td>{len(domain.get('members', []))}</td><td>{len(domain.get('anchors', []))}</td>"
            f"<td>{domain.get('cohesion', 0.0):.3f}</td><td>{html.escape(status)}</td>"
            f"<td><details><summary>Inspect members and evidence</summary><b>Anchors</b><ul>{''.join(f'<li>{html.escape(name)}</li>' for name in anchor_names) or '<li>None detected</li>'}</ul>"
            f"<b>Review notes</b><ul>{reason_list or '<li>No automated review flags.</li>'}</ul><b>Classes</b><ul>{member_list}</ul></details></td></tr>"
        )
        for item in domain.get("ambiguous_classes", []):
            ambiguous_rows.append(
                f"<tr><td>{html.escape(str(item.get('fqcn', item.get('node_id', ''))))}</td>"
                f"<td>{html.escape(str(domain.get('name', '')))}</td><td>{item.get('external_weight', 0.0):.3f}</td>"
                f"<td>{', '.join(str(cluster) for cluster in item.get('neighbor_clusters', []))}</td></tr>"
            )
    cross_domain_rows = "".join(
        f"<tr><td>{html.escape(str(item.get('source', '')))}</td><td>{html.escape(str(item.get('type', 'reference')))}</td>"
        f"<td>{html.escape(str(item.get('method') or ''))}</td><td>{html.escape(str(item.get('target', '')))}</td>"
        f"<td>{item.get('source_domain', '')} → {item.get('target_domain', '')}</td></tr>"
        for item in candidate_domains.get("cross_domain_dependencies", [])
    )
    weights = graph.graph.get("signal_weights", {})
    weight_rows = "".join(f"<li><b>{html.escape(str(name))}</b>: {float(value):.2f}</li>" for name, value in sorted(weights.items()))
    payload_json = json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    document = f'''<!doctype html><html><head><meta charset="utf-8"><title>Domain Decomposition Report</title>
<style>body{{font:14px system-ui;margin:24px;color:#17202a;background:#fbfcfd}}h1{{margin-bottom:4px}}h2{{margin-top:30px}}.metric{{display:inline-block;background:#eef3f7;padding:12px 18px;margin:8px 8px 18px 0;border-radius:8px}}.graph-controls{{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:12px 0}}.graph-controls input{{flex:1;min-width:240px;max-width:460px}}.graph-controls select,.graph-controls button{{padding:9px 12px;border:1px solid #cbd5dc;border-radius:6px;background:white;color:#17202a}}.graph-controls button{{cursor:pointer}}.graph-controls button:hover{{background:#eef3f7}}#graph{{display:block;border:1px solid #cbd5dc;border-radius:8px;width:100%;height:650px;background:#fff;cursor:grab;touch-action:none}}#graph:active{{cursor:grabbing}}#node-details{{min-height:48px;margin:10px 0 22px;padding:12px 14px;border:1px solid #d7dde2;border-radius:8px;background:#fff;overflow-wrap:anywhere}}#node-details strong{{color:#146c94}}table{{border-collapse:collapse;width:100%;margin:10px 0 22px}}td,th{{border-bottom:1px solid #d7dde2;padding:9px;text-align:left;vertical-align:top}}details summary{{cursor:pointer;color:#146c94}}details ul{{margin-top:5px}}.graph-help{{margin:4px 0;color:#65727d;font-size:12px}}.muted{{color:#65727d}}.notice{{padding:12px 15px;border-left:4px solid #d49a3a;background:#fff8e9;color:#74531f;border-radius:0 8px 8px 0}}</style></head><body>
<h1>Domain Decomposition</h1><p class="muted">Candidate domains are Louvain communities from a pairwise, signal-weighted cohesion graph. These are review candidates, not approved microservices.</p>
<div class="metric"><b>Candidate domains</b><br>{len(candidate_domains.get('domains', []))}</div><div class="metric"><b>Review required</b><br>{candidate_domains.get('review_required_count', 0)}</div><div class="metric"><b>Service anchors</b><br>{candidate_domains.get('anchor_count', 0)}</div><div class="metric"><b>Nodes / edges</b><br>{len(nodes)} / {len(edges)}</div><div class="metric"><b>Modularity</b><br>{modularity:.4f}</div>
<p class="notice">Automated cohesion and review indicators support human review; they do not establish final bounded contexts or deployment boundaries.</p>
<h2>Interactive cohesion graph</h2><div class="graph-controls"><input id="search" placeholder="Search classes or packages" aria-label="Search classes or packages"><select id="color-by" aria-label="Color nodes by"><option value="cluster">Color by Louvain community</option><option value="domain">Color by candidate domain</option></select><button id="fit-view" type="button">Fit graph</button><button id="reset-view" type="button">Reset layout</button></div><p class="graph-help">Scroll to zoom · drag background to pan · drag a node to reposition · click a node to inspect it. Search highlights matches and neighbors.</p><canvas id="graph" aria-label="Interactive domain graph"></canvas><div id="node-details" aria-live="polite">Select a node to inspect its package, candidate domain, Louvain community, and connected classes.</div>
<h2>Candidate domains for review</h2><p class="muted">Each candidate is one Louvain community. Review anchors, cohesion, boundary evidence, and notes before accepting a domain.</p><table><thead><tr><th>Community</th><th>Candidate name</th><th>Classes</th><th>Anchors</th><th>Internal cohesion</th><th>Status</th><th>Review details</th></tr></thead><tbody>{''.join(domain_rows) or '<tr><td colspan="7">No candidate domains were generated.</td></tr>'}</tbody></table>
<h2>Ambiguous class ownership</h2><p class="muted">These classes have at least as much weighted connection outside their current community as inside, across multiple other communities. Their Louvain assignment is retained but should be reviewed.</p><table><thead><tr><th>Class</th><th>Assigned candidate</th><th>External edge weight</th><th>Neighbor communities</th></tr></thead><tbody>{''.join(ambiguous_rows) or '<tr><td colspan="4">No classes met the ambiguity heuristic.</td></tr>'}</tbody></table>
<h2>Direct dependencies crossing candidate boundaries</h2><p class="muted">These are directed references from the parser/facts input. They are coupling to review, not automatic API endpoint recommendations.</p><table><thead><tr><th>Consumer class</th><th>Reference type</th><th>Method</th><th>Referenced class</th><th>Community</th></tr></thead><tbody>{cross_domain_rows or '<tr><td colspan="5">No direct cross-domain references were found.</td></tr>'}</tbody></table>
<h2>Evidence and configuration</h2><p class="muted">Signal weights used in the pairwise graph:</p><ul>{weight_rows}</ul><p class="muted">Node-level signal coverage: {coverage_rows}</p><p class="muted">Feature dimensions retained for diagnostics: {html.escape(', '.join(feature_names))}</p>
<script>
const data={payload_json};
const canvas=document.getElementById('graph'),ctx=canvas.getContext('2d');
const search=document.getElementById('search'),colorBy=document.getElementById('color-by');
const details=document.getElementById('node-details');
const positions={{}},adjacency=new Map(data.nodes.map(n=>[n.id,[]]));
let scale=1,offsetX=0,offsetY=0,selected=null,hovered=null,pointer=null;
data.edges.forEach(e=>{{adjacency.get(e.source)?.push(e.target);adjacency.get(e.target)?.push(e.source)}});
function hashColor(value){{let hash=0;for(const ch of String(value))hash=(hash*31+ch.charCodeAt(0))|0;return `hsl(${{Math.abs(hash)%360}} 48% 43%)`}}
function nodeColor(node){{if(colorBy.value==='domain')return hashColor(node.domain);const palette=['#146c94','#b85c38','#4d9078','#7b5ea7','#d17a22','#3b5b92','#9b3d58','#668c3c','#b04f88'];return palette[(node.cluster-1)%palette.length]||'#777'}}
function layout(){{
    const groups=new Map();data.nodes.forEach(n=>{{const key=String(n.cluster);if(!groups.has(key))groups.set(key,[]);groups.get(key).push(n)}});
    const entries=[...groups.entries()].sort((a,b)=>Number(a[0])-Number(b[0])),centerX=950,centerY=650,ring=Math.max(240,entries.length*34);
    entries.forEach(([cluster,members],groupIndex)=>{{const angle=-Math.PI/2+2*Math.PI*groupIndex/entries.length,cx=centerX+Math.cos(angle)*ring,cy=centerY+Math.sin(angle)*ring;const radius=Math.max(48,Math.sqrt(members.length)*23);members.forEach((n,index)=>{{const a=index*2.399963229728653;const r=radius*Math.sqrt((index+0.5)/members.length);positions[n.id]={{x:cx+Math.cos(a)*r,y:cy+Math.sin(a)*r}}}})}});
}}
function resize(){{const rect=canvas.getBoundingClientRect(),dpr=window.devicePixelRatio||1;canvas.width=Math.max(1,Math.round(rect.width*dpr));canvas.height=Math.max(1,Math.round(rect.height*dpr));draw()}}
function fit(){{const rect=canvas.getBoundingClientRect(),points=Object.values(positions);if(!points.length)return;const xs=points.map(p=>p.x),ys=points.map(p=>p.y),minX=Math.min(...xs)-40,maxX=Math.max(...xs)+40,minY=Math.min(...ys)-40,maxY=Math.max(...ys)+40;scale=Math.min(rect.width/(maxX-minX),rect.height/(maxY-minY),1.5);offsetX=(rect.width-(maxX-minX)*scale)/2-minX*scale;offsetY=(rect.height-(maxY-minY)*scale)/2-minY*scale;draw()}}
function draw(){{
    const rect=canvas.getBoundingClientRect(),dpr=window.devicePixelRatio||1;ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,rect.width,rect.height);ctx.setTransform(dpr*scale,0,0,dpr*scale,dpr*offsetX,dpr*offsetY);
    const query=search.value.trim().toLowerCase(),matches=new Set(data.nodes.filter(n=>!query||n.label.toLowerCase().includes(query)||n.package.toLowerCase().includes(query)).map(n=>n.id));
    const related=new Set(matches);matches.forEach(id=>(adjacency.get(id)||[]).forEach(other=>related.add(other)));
    data.edges.forEach(e=>{{const a=positions[e.source],b=positions[e.target];if(!a||!b)return;const focused=!query||matches.has(e.source)||matches.has(e.target)||selected===e.source||selected===e.target;ctx.strokeStyle=focused?'#aab8c2':'#e8edf0';ctx.globalAlpha=focused?Math.min(.85,.25+e.weight*.55):.3;ctx.lineWidth=focused?Math.max(.7,e.weight*1.4):.6;ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke()}});ctx.globalAlpha=1;
    data.nodes.forEach(n=>{{const p=positions[n.id];if(!p)return;const isMatch=matches.has(n.id),isRelated=related.has(n.id),isSelected=selected===n.id,isHovered=hovered===n.id;ctx.globalAlpha=query&&!isRelated?0.14:1;ctx.fillStyle=nodeColor(n);ctx.beginPath();ctx.arc(p.x,p.y,isSelected||isHovered?10:7,0,Math.PI*2);ctx.fill();if(isSelected||isHovered){{ctx.strokeStyle='#17202a';ctx.lineWidth=2;ctx.stroke()}}if((query&&isMatch)||isSelected){{ctx.strokeStyle=isSelected?'#17202a':'#d17a22';ctx.lineWidth=2;ctx.beginPath();ctx.arc(p.x,p.y,12,0,Math.PI*2);ctx.stroke()}}if((query&&isMatch)||isSelected||isHovered){{ctx.globalAlpha=1;ctx.fillStyle='#17202a';ctx.font='12px system-ui';ctx.fillText(n.label.split('.').pop(),p.x+12,p.y+4)}}}});ctx.globalAlpha=1;
}}
function screenPoint(event){{const r=canvas.getBoundingClientRect();return {{x:(event.clientX-r.left-offsetX)/scale,y:(event.clientY-r.top-offsetY)/scale}}}}
function hit(point){{for(let i=data.nodes.length-1;i>=0;i--){{const n=data.nodes[i],p=positions[n.id];if(p&&Math.hypot(p.x-point.x,p.y-point.y)<13)return n}}return null}}
function inspect(node){{selected=node?.id||null;if(!node){{details.textContent='Select a node to inspect its package, candidate domain, Louvain community, and connected classes.';draw();return}}const neighbors=adjacency.get(node.id)||[];details.replaceChildren();const title=document.createElement('strong');title.textContent=node.label;details.append(title,document.createElement('br'));details.append(document.createTextNode(`Package: ${{node.package||'—'}} · Community: ${{node.cluster}} · Candidate: ${{node.domain||'—'}} · Connections: ${{neighbors.length}}`));if(neighbors.length){{details.append(document.createElement('br'));details.append(document.createTextNode('Connected: '+neighbors.map(id=>data.nodes.find(n=>n.id===id)?.label.split('.').pop()||id).join(', ')))}}draw()}}
canvas.addEventListener('pointerdown',event=>{{const point=screenPoint(event),node=hit(point);pointer={{x:event.clientX,y:event.clientY,lastX:event.clientX,lastY:event.clientY,nodeId:node?.id||null,moved:false}};canvas.setPointerCapture(event.pointerId)}});
canvas.addEventListener('pointermove',event=>{{const point=screenPoint(event);if(pointer){{const dx=event.clientX-pointer.lastX,dy=event.clientY-pointer.lastY;if(Math.abs(event.clientX-pointer.x)+Math.abs(event.clientY-pointer.y)>3)pointer.moved=true;if(pointer.nodeId&&pointer.moved){{positions[pointer.nodeId].x+=dx/scale;positions[pointer.nodeId].y+=dy/scale}}else if(!pointer.nodeId){{offsetX+=dx;offsetY+=dy}}pointer.lastX=event.clientX;pointer.lastY=event.clientY;draw();return}}const node=hit(point);hovered=node?.id||null;canvas.title=node?`${{node.label}} · ${{node.domain||'—'}}`:'Scroll to zoom, drag to pan';draw()}});
canvas.addEventListener('pointerup',event=>{{if(!pointer)return;const point=screenPoint(event),node=hit(point);if(!pointer.moved&&node)inspect(node);pointer=null}});
canvas.addEventListener('pointercancel',()=>pointer=null);
canvas.addEventListener('wheel',event=>{{event.preventDefault();const rect=canvas.getBoundingClientRect(),x=event.clientX-rect.left,y=event.clientY-rect.top,worldX=(x-offsetX)/scale,worldY=(y-offsetY)/scale,next=Math.max(.15,Math.min(4,scale*Math.exp(-event.deltaY*.001)));offsetX=x-worldX*next;offsetY=y-worldY*next;scale=next;draw()}},{{passive:false}});
search.addEventListener('input',draw);colorBy.addEventListener('change',draw);document.getElementById('fit-view').addEventListener('click',fit);document.getElementById('reset-view').addEventListener('click',()=>{{layout();fit()}});window.addEventListener('resize',resize);
layout();resize();fit();
</script></body></html>'''
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(document, encoding="utf-8")
