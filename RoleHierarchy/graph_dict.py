# nx_isolated_to_html.py
# Build a NetworkX graph from a dict (keeping isolated nodes) and export to interactive HTML (D3.js).

from pathlib import Path
import json
from typing import Any, Dict, Iterable, Tuple, Union, Optional, List
import networkx as nx


def dict_to_networkx(
    d: Dict[Any, Any],
    directed: bool = False,
    extra_nodes: Optional[Iterable[Any]] = None,
) -> Union[nx.Graph, nx.DiGraph]:
    """
    Convert a dictionary into a NetworkX Graph/DiGraph and KEEP ISOLATED NODES.

    Supports:
      1) Adjacency dict (neighbors as list/set OR dict of neighbor->weight):
         d = {"A": ["B", "C"], "B": {"C": 2.5}, "C": []}   # "C" kept even if no neighbors
      2) Edge->weight dict with 2-tuples as keys:
         d = {("A","B"): 3, ("B","C"): 1.2}

    Notes:
      - Non-numeric edge attributes stored as 'attr'
      - Numeric weights stored as 'weight'
      - 'extra_nodes' forces nodes to be added even if not in d
    """
    G = nx.DiGraph() if directed else nx.Graph()

    if isinstance(d, dict) and d and all(isinstance(k, tuple) and len(k) == 2 for k in d.keys()):
        # Case 2: Edge -> weight dict
        # Nodes are implied by edges; add any extra isolated nodes via 'extra_nodes'.
        for (u, v), w in d.items():
            if isinstance(w, (int, float)):
                G.add_edge(u, v, weight=float(w))
            elif w is None:
                G.add_edge(u, v)
            else:
                G.add_edge(u, v, attr=w)
    elif isinstance(d, dict):
        # Case 1: Adjacency dict (neighbors may be list/set OR dict of neighbor->weight)
        for u, nbrs in d.items():
            # Always add node u so it exists even when nbrs is empty => keeps isolated u
            G.add_node(u)

            if isinstance(nbrs, dict):
                for v, w in nbrs.items():
                    if isinstance(w, (int, float)):
                        G.add_edge(u, v, weight=float(w))
                    elif w is None:
                        G.add_edge(u, v)
                    else:
                        G.add_edge(u, v, attr=w)
            else:
                # iterable of neighbors
                for v in nbrs:
                    G.add_edge(u, v)
    else:
        raise ValueError("Unsupported input. Provide an adjacency dict or an edge->weight dict.")

    # Force-add any isolated/extra nodes explicitly provided
    if extra_nodes:
        for n in extra_nodes:
            G.add_node(n)

    return G


def networkx_to_html_with_zoom(
    G: Union[nx.Graph, nx.DiGraph],
    title: str = "NetworkX Graph (Interactive HTML + Zoom)",
    filename: str = "nx_graph_zoom.html",
) -> str:
    """
    Serialize a NetworkX Graph/DiGraph to an interactive HTML using D3.js.

    - Keeps isolated nodes and lays them out nicely even if there are no edges,
      AND also when other nodes are linked.
    - Zoom/pan, fit-to-view, link distance & charge controls, drag to reposition.
    - Isolated vertices are colored gray by default.
    """
    # Prepare nodes/links JSON (include degree to identify isolated)
    deg = dict(G.degree())
    nodes = [{"id": str(n), "deg": int(deg.get(n, 0))} for n in G.nodes()]
    links: List[Dict[str, Any]] = []
    for u, v, data in G.edges(data=True):
        entry = {"source": str(u), "target": str(v)}
        if "weight" in data and isinstance(data["weight"], (int, float)):
            entry["weight"] = float(data["weight"])
        links.append(entry)

    nodes_json = json.dumps(nodes)
    links_json = json.dumps(links)
    directed = isinstance(G, nx.DiGraph)

    marker_defs = (
        """
      <defs>
        <marker id="arrow" viewBox="0 -5 10 10" refX="16" refY="0" markerWidth="6" markerHeight="6" orient="auto">
          <path d="M0,-5L10,0L0,5" fill="#999"></path>
        </marker>
      </defs>
        """ if directed else ""
    )

    # Edge coloring by weight; defaults neutral if no weight
    link_line = (
        '  const link = gLinks.selectAll("line")\n'
        '    .data(links)\n'
        '    .join("line")\n'
        '    .attr("class", "link")\n'
        '    .attr("marker-end", "url(#arrow)")\n'
        '    .attr("stroke", d => (d.weight == null) ? "#999" : (d.weight < 1 ? "#88c" : (d.weight < 3 ? "#c84" : "#000")))\n'
        '    .attr("stroke-width", d => d.weight ? Math.max(1, Math.sqrt(d.weight)) : 1.5);\n'
    ) if directed else (
        '  const link = gLinks.selectAll("line")\n'
        '    .data(links)\n'
        '    .join("line")\n'
        '    .attr("class", "link")\n'
        '    .attr("stroke", d => (d.weight == null) ? "#999" : (d.weight < 1 ? "#88c" : (d.weight < 3 ? "#c84" : "#000")))\n'
        '    .attr("stroke-width", d => d.weight ? Math.max(1, Math.sqrt(d.weight)) : 1.5);\n'
    )

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <style>
    html, body {{ height: 100%; margin: 0; }}
    header {{ padding: 12px 16px; background: #111; color: #fff; font-family: system-ui, sans-serif; }}
    #panel {{ padding: 10px 14px; border-bottom: 1px solid #ddd; display: flex; gap: 16px; align-items: center; font-family: system-ui, sans-serif; flex-wrap: wrap; }}
    #panel button {{ padding: 6px 10px; border: 1px solid #aaa; background: #f5f5f5; border-radius: 6px; cursor: pointer; }}
    #panel button:hover {{ background: #eee; }}
    svg {{ width: 100%; height: calc(100% - 96px); display: block; background: #fafafa; }}
    .node {{ stroke: #fff; stroke-width: 1.5px; cursor: grab; }}
    .node:active {{ cursor: grabbing; }}
    .label {{ font-size: 11px; pointer-events: none; font-family: system-ui, sans-serif; }}
  </style>
</head>
<body>
  <header><strong>{title}</strong></header>
  <div id="panel">
    <label>Charge: <input id="charge" type="range" min="-500" max="0" value="-220" step="10"></label>
    <label>Link distance: <input id="distance" type="range" min="20" max="240" value="80" step="5"></label>
    <button id="zoomIn">+</button>
    <button id="zoomOut">−</button>
    <button id="zoomReset">Reset</button>
    <button id="zoomFit">Fit</button>
  </div>
  <svg>
    {marker_defs}
  </svg>

  <script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
  <script>
    const nodes = {nodes_json};
    const links = {links_json};

    const svg = d3.select("svg");
    const width = svg.node().clientWidth;
    const height = svg.node().clientHeight;

    // Main groups for zoom/pan
    const gMain  = svg.append("g").attr("class", "gMain");
    const gLinks = gMain.append("g").attr("class", "links");
    const gNodes = gMain.append("g").attr("class", "nodes");
    const gLabels= gMain.append("g").attr("class", "labels");

{link_line}

    // Color isolated nodes differently (deg == 0)
    const node = gNodes.selectAll("circle")
      .data(nodes)
      .join("circle")
        .attr("class", "node")
        .attr("r", 8)
        .attr("fill", (d, i) => (d.deg === 0 ? "#aaa" : d3.schemeTableau10[i % 10]));

    const label = gLabels.selectAll("text")
      .data(nodes)
      .join("text")
        .attr("class", "label")
        .attr("dx", 12)
        .attr("dy", "0.35em")
        .text(d => d.id);

    // --- Isolated node handling ---
    // Pre-position isolated nodes (deg==0) on a circle so they show nicely even if graph has other links.
    const iso = nodes.filter(d => (d.deg || 0) === 0);
    if (iso.length > 0) {{
      const R = Math.min(width, height) / 2.6;
      iso.forEach((d, i) => {{
        const a = 2 * Math.PI * i / iso.length;
        d.x = width/2  + R * Math.cos(a);
        d.y = height/2 + R * Math.sin(a);
      }});
    }}

    let sim = buildSimulation();

    function buildSimulation(charge=-220, distance=80) {{
      const sim = d3.forceSimulation(nodes)
        .force("charge", d3.forceManyBody().strength(charge))
        .force("center", d3.forceCenter(width/2, height/2))
        .force("collide", d3.forceCollide(14))          // keep nodes from overlapping
        .force("x", d3.forceX(width/2).strength(0.02))  // gentle tether so isolated don't drift away
        .force("y", d3.forceY(height/2).strength(0.02))
        .on("tick", ticked);

      // Only add link force if links exist
      if (links.length > 0) {{
        sim.force("link", d3.forceLink(links).id(d => d.id).distance(distance));
      }}
      return sim;
    }}

    function ticked() {{
      gLinks.selectAll("line")
        .attr("x1", d => d.source.x)
        .attr("y1", d => d.source.y)
        .attr("x2", d => d.target.x)
        .attr("y2", d => d.target.y);

      node.attr("cx", d => d.x).attr("cy", d => d.y);
      label.attr("x", d => d.x).attr("y", d => d.y);
    }}

    // D3 zoom
    const zoom = d3.zoom()
      .scaleExtent([0.2, 5])
      .on("zoom", (event) => {{
        gMain.attr("transform", event.transform);
      }});
    svg.call(zoom).on("dblclick.zoom", null);

    // Buttons
    document.getElementById("zoomIn").addEventListener("click", () => {{
      svg.transition().duration(250).call(zoom.scaleBy, 1.2);
    }});
    document.getElementById("zoomOut").addEventListener("click", () => {{
      svg.transition().duration(250).call(zoom.scaleBy, 1/1.2);
    }});
    document.getElementById("zoomReset").addEventListener("click", () => {{
      svg.transition().duration(300).call(zoom.transform, d3.zoomIdentity);
    }});
    document.getElementById("zoomFit").addEventListener("click", () => zoomToFit());

    function zoomToFit(pad = 0.9) {{
      const bounds = gMain.node().getBBox();
      const fullWidth  = svg.node().clientWidth;
      const fullHeight = svg.node().clientHeight;

      const dx = bounds.width;
      const dy = bounds.height;
      const cx = bounds.x + dx / 2;
      const cy = bounds.y + dy / 2;

      if (!dx || !dy) {{
        svg.transition().call(zoom.transform, d3.zoomIdentity);
        return;
      }}

      const scale = pad / Math.max(dx / fullWidth, dy / fullHeight);
      const transform = d3.zoomIdentity
        .translate(fullWidth / 2, fullHeight / 2)
        .scale(scale)
        .translate(-cx, -cy);

      svg.transition().duration(600).call(zoom.transform, transform);
    }}

    // Dragging
    node.call(d3.drag()
      .on("start", (event, d) => {{
        if (!event.active) sim.alphaTarget(0.3).restart();
        d.fx = d.x; d.fy = d.y;
      }})
      .on("drag", (event, d) => {{
        d.fx = event.x; d.fy = event.y;
      }})
      .on("end", (event, d) => {{
        if (!event.active) sim.alphaTarget(0);
        d.fx = null; d.fy = null;
      }})
    );

    // Force controls
    const chargeInput = document.getElementById("charge");
    const distInput = document.getElementById("distance");

    chargeInput.addEventListener("input", (e) => {{
      const val = +e.target.value;
      sim.force("charge").strength(val);
      sim.alpha(0.5).restart();
    }});

    distInput.addEventListener("input", (e) => {{
      const val = +e.target.value;
      if (sim.force("link")) {{
        sim.force("link").distance(val);
        sim.alpha(0.5).restart();
      }}
    }});
  </script>
</body>
</html>"""
    Path(filename).write_text(html, encoding="utf-8")
    return str(Path(filename).resolve())


# ---------------- Demo usage ----------------
if __name__ == "__main__":
    # Example 1: Adjacency dict with isolated nodes
    example_adj = {
        "A": ["B", "C"],
        "B": ["C"],
        "C": [],          # isolated if no other edges point to it
        "D": {},          # isolated explicitly
        "E": ["F"],
        "F": []           # endpoint
    }

    # Example 2: Edge->weight dict (uncomment to try).
    # Note: nodes that never appear on any edge won't exist unless you pass them via extra_nodes.
    # example_edges = {
    #     ("A", "B"): 1.0,
    #     ("B", "C"): 2.0,
    # }
    # extra = {"C", "D"}  # force-add isolated nodes for edge->weight case
    # G = dict_to_networkx(example_edges, directed=False, extra_nodes=extra)

    # Build graph (undirected here; set directed=True for DiGraph)
    G = dict_to_networkx(example_adj, directed=False)

    # Export to interactive HTML
    out_file = networkx_to_html_with_zoom(
        G,
        title="NetworkX from Dict → Interactive HTML (Isolated Nodes Visible)",
        filename="nx_graph_zoom.html"
    )
    print("Wrote:", out_file)
