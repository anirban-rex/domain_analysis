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
<style>body{{font:14px system-ui;margin:24px;color:#17202a;background:#fbfcfd}}h1{{margin-bottom:4px}}.metric{{display:inline-block;background:#eef3f7;padding:12px 18px;margin:8px 8px 18px 0;border-radius:6px}}.graph-controls{{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:12px 0}}.graph-controls input{{flex:1;min-width:240px;max-width:460px}}.graph-controls select,.graph-controls button{{padding:9px 12px;border:1px solid #cbd5dc;border-radius:6px;background:white;color:#17202a}}.graph-controls button{{cursor:pointer}}.graph-controls button:hover{{background:#eef3f7}}#graph{{display:block;border:1px solid #cbd5dc;border-radius:8px;width:100%;height:650px;background:#fff;cursor:grab;touch-action:none}}#graph:active{{cursor:grabbing}}#node-details{{min-height:48px;margin:10px 0 22px;padding:12px 14px;border:1px solid #d7dde2;border-radius:8px;background:#fff;overflow-wrap:anywhere}}#node-details strong{{color:#146c94}}table{{border-collapse:collapse;width:100%}}td,th{{border-bottom:1px solid #d7dde2;padding:8px;text-align:left;vertical-align:top}}.graph-help{{margin:4px 0;color:#65727d;font-size:12px}}.muted{{color:#65727d}}</style></head><body>
<h1>Domain Decomposition</h1><p class="muted">Cosine similarity is the only edge-weight formula.</p>
<div class="metric"><b>Initial Louvain clusters</b><br>{len(clusters)}</div><div class="metric"><b>Final services</b><br>{len(services.get('groups', {}))}</div><div class="metric"><b>Nodes</b><br>{len(nodes)}</div><div class="metric"><b>Edges</b><br>{len(edges)}</div><div class="metric"><b>Modularity</b><br>{modularity:.4f}</div>
<h2>Graph</h2><div class="graph-controls"><input id="search" placeholder="Search classes or packages" aria-label="Search classes or packages"><select id="color-by" aria-label="Color nodes by"><option value="cluster">Color by Louvain cluster</option><option value="service">Color by final service</option></select><button id="fit-view" type="button">Fit graph</button><button id="reset-view" type="button">Reset layout</button></div><p class="graph-help">Scroll to zoom · drag the background to pan · drag a node to reposition · click a node to inspect it. Search highlights matches and their neighbors.</p><canvas id="graph" aria-label="Interactive domain graph"></canvas><div id="node-details" aria-live="polite">Select a node to inspect its package, cluster, service, and connected classes.</div>
<h2>Initial Louvain clusters</h2><p class="muted">These are the raw graph communities before backend service-boundary assignment.</p><table><thead><tr><th>Cluster</th><th>Nodes</th><th>Members</th></tr></thead><tbody>{cluster_rows}</tbody></table>
<h2>Final service boundaries</h2><p class="muted">Supporting classes are assigned to the strongest service anchor. Shared classes: {len(services.get('shared', []))}; ambiguous cross-boundary classes: {len(services.get('cross_boundary', []))}.</p><table><thead><tr><th>Service</th><th>Nodes</th><th>Members</th></tr></thead><tbody>{service_rows}</tbody></table>
<h2>Signal coverage</h2><ul>{coverage_rows}</ul><p class="muted">Feature dimensions: {html.escape(', '.join(feature_names))}</p>
<script>
const data={json.dumps(payload)};
const canvas=document.getElementById('graph'),ctx=canvas.getContext('2d');
const search=document.getElementById('search'),colorBy=document.getElementById('color-by');
const details=document.getElementById('node-details');
const positions={{}},adjacency=new Map(data.nodes.map(n=>[n.id,[]]));
let scale=1,offsetX=0,offsetY=0,selected=null,hovered=null,pointer=null;
data.edges.forEach(e=>{{adjacency.get(e.source)?.push(e.target);adjacency.get(e.target)?.push(e.source)}});
function hashColor(value){{let hash=0;for(const ch of String(value))hash=(hash*31+ch.charCodeAt(0))|0;return `hsl(${{Math.abs(hash)%360}} 48% 43%)`}}
function nodeColor(node){{if(colorBy.value==='service')return hashColor(node.service);const palette=['#146c94','#b85c38','#4d9078','#7b5ea7','#d17a22','#3b5b92','#9b3d58','#668c3c','#b04f88'];return palette[(node.cluster-1)%palette.length]||'#777'}}
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
function inspect(node){{selected=node?.id||null;if(!node){{details.textContent='Select a node to inspect its package, cluster, service, and connected classes.';draw();return}}const neighbors=adjacency.get(node.id)||[];details.replaceChildren();const title=document.createElement('strong');title.textContent=node.label;details.append(title,document.createElement('br'));details.append(document.createTextNode(`Package: ${{node.package||'—'}} · Cluster: ${{node.cluster}} · Service: ${{node.service||'shared'}} · Connections: ${{neighbors.length}}`));if(neighbors.length){{details.append(document.createElement('br'));details.append(document.createTextNode('Connected: '+neighbors.map(id=>data.nodes.find(n=>n.id===id)?.label.split('.').pop()||id).join(', ')))}}draw()}}
canvas.addEventListener('pointerdown',event=>{{const point=screenPoint(event),node=hit(point);pointer={{x:event.clientX,y:event.clientY,lastX:event.clientX,lastY:event.clientY,nodeId:node?.id||null,moved:false}};canvas.setPointerCapture(event.pointerId)}});
canvas.addEventListener('pointermove',event=>{{const point=screenPoint(event);if(pointer){{const dx=event.clientX-pointer.lastX,dy=event.clientY-pointer.lastY;if(Math.abs(event.clientX-pointer.x)+Math.abs(event.clientY-pointer.y)>3)pointer.moved=true;if(pointer.nodeId&&pointer.moved){{positions[pointer.nodeId].x+=dx/scale;positions[pointer.nodeId].y+=dy/scale}}else if(!pointer.nodeId){{offsetX+=dx;offsetY+=dy}}pointer.lastX=event.clientX;pointer.lastY=event.clientY;draw();return}}const node=hit(point);hovered=node?.id||null;canvas.title=node?`${{node.label}} · ${{node.service||'shared'}}`:'Scroll to zoom, drag to pan';draw()}});
canvas.addEventListener('pointerup',event=>{{if(!pointer)return;const point=screenPoint(event),node=hit(point);if(!pointer.moved&&node)inspect(node);pointer=null}});
canvas.addEventListener('pointercancel',()=>pointer=null);
canvas.addEventListener('wheel',event=>{{event.preventDefault();const rect=canvas.getBoundingClientRect(),x=event.clientX-rect.left,y=event.clientY-rect.top,worldX=(x-offsetX)/scale,worldY=(y-offsetY)/scale,next=Math.max(.15,Math.min(4,scale*Math.exp(-event.deltaY*.001)));offsetX=x-worldX*next;offsetY=y-worldY*next;scale=next;draw()}},{{passive:false}});
search.addEventListener('input',draw);colorBy.addEventListener('change',draw);document.getElementById('fit-view').addEventListener('click',fit);document.getElementById('reset-view').addEventListener('click',()=>{{layout();fit()}});window.addEventListener('resize',resize);
layout();resize();fit();
</script></body></html>'''
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(document, encoding="utf-8")
