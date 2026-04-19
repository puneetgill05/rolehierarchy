import random
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

########################################
# CONFIG
########################################

NUM_STEPS = 40            # length of the walk
START_NODE = "u0"         # starting user (must exist in graph)
OUTPUT_FILE = "walk.gif"  # .gif or .mp4 (mp4 needs ffmpeg)
SEED = 1337               # for reproducibility
random.seed(SEED)


########################################
# ROLE HIERARCHY CONSTRUCTION
########################################

def build_example_rh():
    """
    Demo role hierarchy:

      u0 -> rA -> rB -> {p1,p2}
      u0 -> rC -> p3
      u1 -> rA
      rA -> p4

    Node attribute 'ntype' ∈ {'user','role','perm'}
    so we can layer them visually.
    """
    G = nx.DiGraph()

    # Users
    G.add_node("u0", ntype="user")
    G.add_node("u1", ntype="user")

    # Roles
    for r in ["rA", "rB", "rC"]:
        G.add_node(r, ntype="role")

    # Perms
    for p in ["p1", "p2", "p3", "p4"]:
        G.add_node(p, ntype="perm")

    edges = [
        ("u0", "rA"),
        ("u0", "rC"),
        ("u1", "rA"),

        ("rA", "rB"),
        ("rA", "p4"),
        ("rC", "p3"),

        ("rB", "p1"),
        ("rB", "p2"),
    ]

    G.add_edges_from(edges)
    return G


G_dir = build_example_rh()
G = G_dir.to_undirected()


if START_NODE not in G:
    raise ValueError(f"START_NODE {START_NODE} not in graph")


########################################
# LAYOUT (layered: users -> roles -> perms)
########################################

def layered_layout(G):
    """
    Put users on y=2, roles on y=1, perms on y=0.
    Spread nodes of each type horizontally.
    """
    # assign y per node type
    y_level = {"user": 2, "role": 1, "perm": 0}

    # bucket nodes by type
    buckets = {"user": [], "role": [], "perm": []}
    for n, data in G.nodes(data=True):
        t = data.get("ntype", "role")
        # default any unknown to role layer
        if t not in buckets:
            t = "role"
        buckets[t].append(n)

    pos = {}
    # for each layer, lay nodes out at integer x positions centered ~0
    for layer_type, nodes in buckets.items():
        k = len(nodes)
        # example x coords: -k/2, -k/2+1, ..., k/2-1
        for i, n in enumerate(nodes):
            x = i - (k - 1) / 2.0
            y = y_level[layer_type]
            pos[n] = (x, y)

    return pos


pos = layered_layout(G)


########################################
# RANDOM WALK SIMULATION
########################################

def random_walk_path(G, start, num_steps):
    """
    Directed random walk:
    - from current node, pick a random successor
    - if no successors (sink), teleport back to `start`
    Returns list of visited nodes [n0, n1, ..., n_num_steps].
    """
    path = [start]
    current = start
    for _ in range(num_steps):
        nbrs = list(G.neighbors(current))
        if not nbrs:
            # dead end -> restart from start
            current = start
        else:
            current = random.choice(nbrs)
        path.append(current)
    return path


walk_nodes = random_walk_path(G, START_NODE, NUM_STEPS)
walk_edges = list(zip(walk_nodes[:-1], walk_nodes[1:]))


########################################
# MATPLOTLIB SETUP
########################################

fig, ax = plt.subplots(figsize=(6, 4))
plt.axis("off")

all_nodes = list(G.nodes())
all_edges = list(G.edges())

# color / size by type so the hierarchy is visually obvious
node_colors = []
node_sizes = []
for n in all_nodes:
    t = G.nodes[n].get("ntype", "")
    if t == "user":
        node_colors.append("#1f77b4")   # bluish
        node_sizes.append(600)
    elif t == "role":
        node_colors.append("#2ca02c")   # greenish
        node_sizes.append(500)
    else:
        node_colors.append("#7f7f7f")   # gray for perms
        node_sizes.append(400)

# --- static background graph (light / low alpha) ---
nx.draw_networkx_edges(
    G,
    pos,
    edgelist=all_edges,
    edge_color="lightgray",
    width=1.0,
    arrows=True,
    arrowstyle='-|>',
    arrowsize=10,
    ax=ax
)

nx.draw_networkx_nodes(
    G,
    pos,
    nodelist=all_nodes,
    node_color=node_colors,
    node_size=node_sizes,
    alpha=0.3,
    ax=ax
)

nx.draw_networkx_labels(
    G,
    pos,
    font_size=8,
    ax=ax
)

# --- dynamic artists we will mutate per frame ---

# 1. bold path edges (the walk so far)
_walk_edge_list = nx.draw_networkx_edges(
    G,
    pos,
    edgelist=[],             # start empty
    edge_color="black",
    width=2.5,
    arrows=True,
    arrowstyle='-|>',
    arrowsize=12,
    ax=ax
)
# draw_networkx_edges returns a list-like of LineCollection
# grab first collection so we can call set_segments()
path_edge_coll = _walk_edge_list[0] if _walk_edge_list else None

# 2. current node highlight (a big gold marker with black outline)
current_node_scatter = ax.scatter(
    [], [],
    s=800,
    edgecolors="black",
    linewidths=2,
    facecolors="gold",
    zorder=5
)

# 3. info box text
step_text = ax.text(
    0.02,
    0.95,
    "",
    transform=ax.transAxes,
    fontsize=9,
    bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="black", lw=0.5)
)


########################################
# ANIMATION UPDATE FUNCTION
########################################

def update(frame_idx):
    """
    frame_idx: 0 .. NUM_STEPS
    Show:
      - edges walked up to this frame
      - highlight current node
      - update text
    """
    # Edges travelled so far
    travelled_edges = walk_edges[:frame_idx]

    # Build segment list for LineCollection
    if path_edge_coll is not None:
        segments = []
        for (u, v) in travelled_edges:
            segments.append([pos[u], pos[v]])
        path_edge_coll.set_segments(segments)

    # Highlight current node
    curr_node = walk_nodes[frame_idx]
    x, y = pos[curr_node]
    current_node_scatter.set_offsets([[x, y]])

    # Update status text
    step_text.set_text(f"step: {frame_idx}\ncurrent: {curr_node}")

    return (path_edge_coll, current_node_scatter, step_text)


########################################
# BUILD ANIMATION
########################################

anim = FuncAnimation(
    fig,
    update,
    frames=len(walk_nodes),   # one frame per visited node
    interval=400,             # ms per frame
    blit=False,
    repeat=False
)

print(f"Saving animation to {OUTPUT_FILE} ...")
anim.save(OUTPUT_FILE, dpi=150)
print("Done.")
