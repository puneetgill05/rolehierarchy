# from __future__ import annotations
# import math
# from dataclasses import dataclass
# from typing import Dict, List, Tuple, Set, Optional
# import numpy as np
# import networkx as nx
#
# User = ''
# Role = None
# Perm = ''
#
# @dataclass
# class RHSpec:
#     user_role: List[Tuple[User, Role]]
#     role_role: List[Tuple[Role, Role]]  # default: (senior -> junior)
#     role_perm: List[Tuple[Role, Perm]]
#     inherit_senior_to_junior: bool = True  # flip if your edges are (junior->senior)
#     lazy: bool = True
#
# class RoleWalkAnalyzer:
#     """
#     For each user u:
#       - Find authorizations A(u) = reachable permissions via RH.
#       - Build a working graph (roles ∪ perms) for exploration.
#       - Estimate cover time to visit all perms in A(u) via lazy random walk.
#     """
#
#     def __init__(self, spec: RHSpec):
#         self.spec = spec
#         self.G_dir = nx.DiGraph()
#         self.users: Set[User] = {u for u,_ in spec.user_role}
#         self.roles: Set[Role] = {r for _,r in spec.user_role} | {a for a,_ in spec.role_role} | {b for _,b in spec.role_role}
#         self.perms: Set[Perm] = {p for _,p in spec.role_perm}
#
#         # Tag nodes to keep types
#         for u in self.users:
#             self.G_dir.add_node(u, kind="U")
#         for r in self.roles:
#             self.G_dir.add_node(r, kind="R")
#         for p in self.perms:
#             self.G_dir.add_node(p, kind="P")
#
#         # U->R
#         self.G_dir.add_edges_from(spec.user_role)
#         # R->R (ensure direction is senior->junior unless flipped)
#         if spec.inherit_senior_to_junior:
#             self.G_dir.add_edges_from(spec.role_role)
#         else:
#             self.G_dir.add_edges_from([(jr, sr) for (sr, jr) in spec.role_role])
#         # R->P
#         self.G_dir.add_edges_from(spec.role_perm)
#
#         # Precompute role reachability (downstream juniors) for speed
#         self._downstream_roles: Dict[Role, Set[Role]] = {}
#         R_only = self.G_dir.subgraph([x for x, d in self.G_dir.nodes(data=True) if d["kind"] == "R"])
#         for r in R_only.nodes():
#             self._downstream_roles[r] = set(nx.descendants(R_only, r)) | {r}
#
#         # Build an undirected “exploration” graph over roles ∪ perms (no user nodes)
#         # We allow walking along edges in either direction to keep the walk mobile.
#         self.G_ud = nx.Graph()
#         for u in self.roles:
#             self.G_ud.add_node(u, kind="U")
#         for r in self.roles:
#             self.G_ud.add_node(r, kind="R")
#         for p in self.perms:
#             self.G_ud.add_node(p, kind="P")
#
#         # Connect roles bidirectionally along inheritance
#         for (a, b) in self.spec.role_role:
#             a2, b2 = (a, b) if self.spec.inherit_senior_to_junior else (b, a)
#             if a2 in self.roles and b2 in self.roles:
#                 self.G_ud.add_edge(a2, b2)
#
#         # Connect roles <-> users bidirectionally
#         for (u, r) in self.spec.user_role:
#             if u in self.users and r in self.roles:
#                 self.G_ud.add_edge(u, r)
#
#         # Connect roles <-> perms bidirectionally
#         for (r, p) in self.spec.role_perm:
#             if r in self.roles and p in self.perms:
#                 self.G_ud.add_edge(r, p)
#
#         # Precompute degrees and neighbors for fast sampling
#         self._neighbors = {n: np.array(list(self.G_ud.neighbors(n))) for n in self.G_ud.nodes()}
#         self._deg = {n: len(self._neighbors[n]) for n in self.G_ud.nodes()}
#
#     def user_reachable_perms(self, u: User) -> Set[Perm]:
#         """Authorizations for user u via directed reachability along R->R->P."""
#         assert u in self.users, f"Unknown user {u}"
#         assigned_roles = [v for _, v in self.G_dir.out_edges(u)]
#         perms: Set[Perm] = set()
#         for r in assigned_roles:
#             for r2 in self._downstream_roles.get(r, {r}):
#                 for _, p in self.G_dir.out_edges(r2):
#                     if self.G_dir.nodes[p]["kind"] == "P":
#                         perms.add(p)
#         return perms
#
#     def _transition(self, node, already_visited: set, rng: np.random.Generator):
#         """One lazy random-walk step on the undirected graph (roles∪perms)."""
#         # if self.spec.lazy:
#             # 1/2 stay; 1/2 move uniformly to a neighbor (if any)
#             # if rng.random() < 0 or self._deg[node] == 0:
#             #     return node
#         deg = self._deg[node]
#
#         if deg == 0:
#             return node
#         nbrs_set = set(self._neighbors[node])
#         nbrs = np.array(list(nbrs_set.difference(already_visited)))
#         # nbrs = self._neighbors[node]
#         if len(nbrs) == 0:
#             nbrs = self._neighbors[node]
#
#
#         return rng.choice(nbrs)
#
#     def estimate_cover_time_for_user(
#         self,
#         u: User,
#         trials: int = 128,
#         max_steps: int = 1_000_000,
#         seed: int = 12345,
#     ) -> Dict[str, float | int]:
#         """
#         Monte-Carlo estimate of steps to visit all reachable permissions for user u.
#         Start node per trial is sampled uniformly from u's assigned roles.
#         """
#         targets: Set[Perm] = self.user_reachable_perms(u)
#         if not targets:
#             return {"user": u, "num_targets": 0, "mean_steps": 0.0, "median_steps": 0.0, "success_rate": 1.0}
#
#         # Starting role set (if some roles are isolated in G_ud, we still start there)
#         start_roles = [v for _, v in self.G_dir.out_edges(u) if self.G_dir.nodes[v]["kind"] == "R"]
#         if not start_roles:
#             return {"user": u, "num_targets": len(targets), "mean_steps": math.inf, "median_steps": math.inf, "success_rate": 0.0}
#
#         rng = np.random.default_rng(seed)
#         target_idx = {t:i for i,t in enumerate(sorted(targets))}
#         visited_mask = np.zeros(len(targets), dtype=bool)
#
#         steps_list: List[Optional[int]] = []
#         paths = list()
#         for t in range(trials):
#             cur = rng.choice(start_roles)
#             visited_mask[:] = False
#             steps = 0
#             # If start node is a permission and is in targets, mark it
#             if cur in targets:
#                 visited_mask[target_idx[cur]] = True
#             # Walk
#             already_visited = set()
#             path = [cur]
#             while steps < max_steps and not visited_mask.all():
#                 cur = self._transition(cur, already_visited, rng)
#
#                 if isinstance(cur, str) and not (cur.startswith('U') or cur.startswith('u') or cur.startswith('P') or cur.startswith('p')):
#                     cur = int(cur)
#                 path.append(cur)
#
#                 if cur in targets:
#                     visited_mask[target_idx[cur]] = True
#                     already_visited.add(cur)
#                 steps += 1
#             steps_list.append(steps if visited_mask.all() else None)
#             paths.append(path)
#
#         arr = np.array([s for s in steps_list if s is not None], dtype=float)
#         success_rate = (arr.size / len(steps_list)) if steps_list else 0.0
#         mean_steps = float(arr.mean()) if arr.size else math.inf
#         median_steps = float(np.median(arr)) if arr.size else math.inf
#         return {
#             "user": u,
#             "num_targets": len(targets),
#             "mean_steps": mean_steps,
#             "median_steps": median_steps,
#             "success_rate": success_rate,
#             "trials": trials
#             # "paths": paths
#         }
#
#     def estimate_for_all_users(self, **kw) -> List[Dict[str,float|int]]:
#         return [self.estimate_cover_time_for_user(u, **kw) for u in sorted(self.users)]
#
#
#
# import matplotlib.pyplot as plt
# import numpy as np
#
# def draw_walk_static(G_ud, path, targets=None, pos=None, title="Random Walk on RH"):
#     """
#     Static figure:
#       - roles vs perms colored differently
#       - start node + visited targets highlighted
#       - path edges overlaid (with fading alpha)
#     """
#     if pos is None:
#         pos = nx.spring_layout(G_ud, seed=3)
#
#     kinds = nx.get_node_attributes(G_ud, "kind")  # expects {"R","P"} from earlier code
#     roles = [n for n,k in kinds.items() if k == "R"]
#     perms = [n for n,k in kinds.items() if k == "P"]
#     targets = set(targets or [])
#
#     plt.figure(figsize=(9,7))
#     # base graph
#     nx.draw_networkx_edges(G_ud, pos, alpha=0.3, width=1.0)
#     nx.draw_networkx_nodes(G_ud, pos, nodelist=roles, node_size=250, alpha=0.9, label="Roles")
#     nx.draw_networkx_nodes(G_ud, pos, nodelist=perms, node_shape="s", node_size=220, alpha=0.9, label="Perms")
#
#     # highlight targets
#     if targets:
#         nx.draw_networkx_nodes(G_ud, pos, nodelist=list(targets), node_shape="s",
#                                node_size=280, alpha=1.0, linewidths=1.5)
#
#     # path edges (fading)
#     edges = list(zip(path[:-1], path[1:]))
#     m = max(1, len(edges))
#     for i, e in enumerate(edges):
#         a = 0.15 + 0.85 * (i+1)/m  # fade in
#         nx.draw_networkx_edges(G_ud, pos, edgelist=[e], width=2.2, alpha=a)
#
#     # start & end
#     start, end = path[0], path[-1]
#     nx.draw_networkx_nodes(G_ud, pos, nodelist=[start], node_size=450, linewidths=2.0)
#     nx.draw_networkx_nodes(G_ud, pos, nodelist=[end], node_size=450, linewidths=2.0)
#
#     # labels (optional for small graphs)
#     if len(G_ud) <= 60:
#         nx.draw_networkx_labels(G_ud, pos, font_size=9)
#
#     plt.title(title)
#     plt.axis("off")
#     plt.legend(scatterpoints=1)
#     plt.tight_layout()
#     plt.show()
#
#
# def run_random_walk(UR, RR, RP):
#     # Tiny illustrative RH
#     # Users
#     # UR = [("U1", "R_admin"), ("U2", "R_viewer"), ("U3", "R_editor")]
#     # # Inheritance: senior -> junior (admin inherits from editor; editor inherits from viewer)
#     # RR = [("R_admin", "R_editor"), ("R_editor", "R_viewer")]
#     # # Role -> Permission
#     # RP = [
#     #     ("R_viewer", "P_read"),
#     #     ("R_viewer", "P1"),
#     #     ("R_viewer", "P2"),
#     #     ("R_editor", "P_write"),
#     #     ("R_editor", "P3"),
#     #     ("R_admin",  "P_delete"),
#     #     ("R_admin",  "P_config"),
#     # ]
#
#     users = {e[0] for e in UR}
#     spec = RHSpec(user_role=UR, role_role=RR, role_perm=RP, inherit_senior_to_junior=True, lazy=True)
#     A = RoleWalkAnalyzer(spec)
#
#     # Show each user's reachable permissions
#     for u in users:
#         print(u, "authorizations:", sorted(A.user_reachable_perms(u)))
#
#     # Estimate cover time to reach ALL of each user's permissions
#     out = A.estimate_for_all_users(trials=1, max_steps=200000)
#     median_steps_for_rh = 0
#     num_unsuccessful = 0
#     for row in out:
#         if row['median_steps'] == np.inf and row['success_rate'] == 0:
#             num_unsuccessful += 1
#         else:
#             median_steps_for_rh += row['median_steps']
#         # paths = row['paths']
#         u = row['user']
#         targets = A.user_reachable_perms(u)
#
#         pos = nx.spring_layout(A.G_ud, seed=3)
#         # for path in paths:
#         #     draw_walk_static(A.G_ud, path, targets=targets, pos=pos, title=f"Random walk for {u}")
#
#         print(row)
#     median_steps_for_rh = median_steps_for_rh / len(out)
#     print('median_steps for RH: ', median_steps_for_rh)
#     print('# unsuccessful walks for RH: ', num_unsuccessful)
#
#
#
# # -------------------- Demo --------------------
# if __name__ == "__main__":
#     run_random_walk()
from __future__ import annotations
import math
from dataclasses import dataclass
from pprint import pprint
from typing import Dict, List, Tuple, Set, Optional
import numpy as np
import networkx as nx
import torch

User = ''
Role = None
Perm = ''



@dataclass
class RHSpec:
    user_role: List[Tuple[User, Role]]
    role_role: List[Tuple[Role, Role]]  # default: (senior -> junior)
    role_perm: List[Tuple[Role, Perm]]
    inherit_senior_to_junior: bool = True  # flip if your edges are (junior->senior)
    lazy: bool = True


class RoleWalkAnalyzer:
    def __init__(self, spec: RHSpec, walk_mode: str = "uniform", p: float = 1.0, q: float = 0.25):
        self.spec = spec
        self.walk_mode = walk_mode  # "uniform" or "node2vec"
        self.p = float(p)
        self.q = float(q)

        self.G_dir = nx.DiGraph()
        self.users: Set[User] = {u for u, _ in spec.user_role}
        self.roles: Set[Role] = {r for _, r in spec.user_role} | {a for a, _ in spec.role_role} | {b for _, b in
                                                                                                   spec.role_role}
        self.perms: Set[Perm] = {p for _, p in spec.role_perm}

        # Tag nodes
        for u in self.users:
            self.G_dir.add_node(u, kind="U")
        for r in self.roles:
            self.G_dir.add_node(r, kind="R")
        for p_ in self.perms:
            self.G_dir.add_node(p_, kind="P")

        # U->R
        self.G_dir.add_edges_from(spec.user_role)
        # R->R
        if spec.inherit_senior_to_junior:
            self.G_dir.add_edges_from(spec.role_role)
        else:
            self.G_dir.add_edges_from([(jr, sr) for (sr, jr) in spec.role_role])
        # R->P
        self.G_dir.add_edges_from(spec.role_perm)

        # Role descendants (R-only)
        self._downstream_roles: Dict[Role, Set[Role]] = {}
        R_only = self.G_dir.subgraph([x for x, d in self.G_dir.nodes(data=True) if d["kind"] == "R"])
        for r in R_only.nodes():
            self._downstream_roles[r] = set(nx.descendants(R_only, r)) | {r}

        # Undirected exploration graph (R ∪ P ∪ U)
        self.G_ud = nx.Graph()
        for u in self.users:
            self.G_ud.add_node(u, kind="U")
        for r in self.roles:
            self.G_ud.add_node(r, kind="R")
        for p_ in self.perms:
            self.G_ud.add_node(p_, kind="P")

        # R<->R inheritance
        for (a, b) in self.spec.role_role:
            a2, b2 = (a, b) if self.spec.inherit_senior_to_junior else (b, a)
            if a2 in self.roles and b2 in self.roles:
                self.G_ud.add_edge(a2, b2)
        # U<->R
        for (u, r) in self.spec.user_role:
            if u in self.users and r in self.roles:
                self.G_ud.add_edge(u, r)
        # R<->P
        for (r, p_) in self.spec.role_perm:
            if r in self.roles and p_ in self.perms:
                self.G_ud.add_edge(r, p_)

        # Precompute neighbors / degrees
        self._neighbors = {n: np.array(list(self.G_ud.neighbors(n))) for n in self.G_ud.nodes()}
        self._deg = {n: len(self._neighbors[n]) for n in self.G_ud.nodes()}

        # GPU: CSR
        self.cuda_available = torch.cuda.is_available()
        if self.cuda_available:
            self._nid, self._nodes_rev, self._indptr_cu, self._indices_cu = nx_to_csr_tensors(self.G_ud)
            # cache id-sets for quick lookup
            self._id_users = {self._nid[n] for n in self.users if n in self._nid}
            self._id_roles = {self._nid[n] for n in self.roles if n in self._nid}
            self._id_perms = {self._nid[n] for n in self.perms if n in self._nid}
        else:
            self._nid, self._nodes_rev, self._indptr_cu, self._indices_cu = None, None, None, None

    def _to_ids(self, nodes_iterable):
        if not self.cuda_available:
            raise RuntimeError("CUDA not available; cannot map ids for GPU walk.")
        return [self._nid[n] for n in nodes_iterable if n in self._nid]

    # --- NEW: node2vec transition ---
    def _transition_node2vec(self, prev, cur, rng: np.random.Generator):
        nbrs = self._neighbors[cur]
        if nbrs.size == 0:
            return cur
        # Weights as in node2vec
        #   1/p for x==prev, 1 if (x,prev) edge exists, 1/q otherwise
        if prev is None:
            # first step: uniform over neighbors of cur
            return rng.choice(nbrs)
        w = np.empty(nbrs.size, dtype=float)
        for i, x in enumerate(nbrs):
            if x == prev:
                w[i] = 1.0 / self.p
            elif self.G_ud.has_edge(x, prev):
                w[i] = 1.0
            else:
                w[i] = 1.0 / self.q
        w_sum = w.sum()
        if w_sum == 0.0:
            return rng.choice(nbrs)
        return rng.choice(nbrs, p=w / w_sum)

    # (your original uniform transition, unchanged except removed visited-bias)
    def _transition_uniform(self, node, rng: np.random.Generator):
        deg = self._deg[node]
        if deg == 0:
            return node
        return rng.choice(self._neighbors[node])

    def _next_step(self, prev, cur, rng):
        if self.walk_mode == "node2vec":
            return self._transition_node2vec(prev, cur, rng)
        else:
            return self._transition_uniform(cur, rng)

    def estimate_cover_time_for_user(
            self,
            u: User,
            trials: int = 128,
            max_steps: int = 1_000_000,
            seed: int = 12345,
    ) -> Dict[str, float | int]:
        targets: Set[Perm] = self.user_reachable_perms(u)
        if not targets:
            return {"user": u, "num_targets": 0, "mean_steps": 0.0, "median_steps": 0.0, "success_rate": 1.0}

        start_roles = [v for _, v in self.G_dir.out_edges(u) if self.G_dir.nodes[v]["kind"] == "R"]
        if not start_roles:
            return {"user": u, "num_targets": len(targets), "mean_steps": math.inf, "median_steps": math.inf,
                    "success_rate": 0.0}

        rng = np.random.default_rng(seed)
        target_idx = {t: i for i, t in enumerate(sorted(targets))}
        visited_mask = np.zeros(len(targets), dtype=bool)

        steps_list: List[Optional[int]] = []
        for _ in range(trials):
            cur = rng.choice(start_roles)
            prev = None  # <- needed for node2vec
            visited_mask[:] = False
            steps = 0
            if cur in targets:
                visited_mask[target_idx[cur]] = True
            while steps < max_steps and not visited_mask.all():
                nxt = self._next_step(prev, cur, rng)
                prev, cur = cur, nxt
                if isinstance(cur, str) and not (
                        cur.startswith('U') or cur.startswith('u') or cur.startswith('P') or cur.startswith('p')):
                    try:
                        cur = int(cur)
                    except ValueError:
                        pass
                if cur in targets:
                    visited_mask[target_idx[cur]] = True
                steps += 1
            steps_list.append(steps if visited_mask.all() else None)

        arr = np.array([s for s in steps_list if s is not None], dtype=float)
        success_rate = (arr.size / len(steps_list)) if steps_list else 0.0
        mean_steps = float(arr.mean()) if arr.size else math.inf
        median_steps = float(np.median(arr)) if arr.size else math.inf
        return {
            "user": u,
            "num_targets": len(targets),
            "mean_steps": mean_steps,
            "median_steps": median_steps,
            "success_rate": success_rate,
            "trials": trials
        }

    def estimate_for_all_users(self, **kw) -> List[Dict[str, float | int]]:
        return [self.estimate_cover_time_for_user(u, **kw) for u in sorted(self.users)]

    def user_reachable_perms(self, u: User) -> Set[Perm]:
        """Authorizations for user u via directed reachability along R->R->P."""
        assert u in self.users, f"Unknown user {u}"
        assigned_roles = [v for _, v in self.G_dir.out_edges(u)]
        perms: Set[Perm] = set()
        for r in assigned_roles:
            for r2 in self._downstream_roles.get(r, {r}):
                for _, p in self.G_dir.out_edges(r2):
                    if self.G_dir.nodes[p]["kind"] == "P":
                        perms.add(p)
        return perms

    @torch.no_grad()
    def estimate_cover_time_for_user_gpu(
            self, u: User, trials: int = 5, max_steps: int = 10000,
            p: float = 1.0, q: float = 1.0, seed: int = 12345
    ):
        assert self.cuda_available, "CUDA not available."
        targets = self.user_reachable_perms(u)
        if not targets:
            return {"user": u, "num_targets": 0, "mean_steps": 0.0, "median_steps": 0.0, "success_rate": 1.0,
                    "trials": trials}

        # start roles
        start_roles = [v for _, v in self.G_dir.out_edges(u) if self.G_dir.nodes[v]["kind"] == "R"]
        if not start_roles:
            return {"user": u, "num_targets": len(targets), "mean_steps": math.inf, "median_steps": math.inf,
                    "success_rate": 0.0, "trials": trials}

        torch.cuda.manual_seed(seed)

        # map to ids
        start_ids = self._to_ids(start_roles)
        target_ids = self._to_ids(targets)

        if len(start_ids) == 0 or len(target_ids) == 0:
            # user has roles/targets not present in G_ud (shouldn't happen, but be safe)
            return {"user": u, "num_targets": len(targets), "mean_steps": math.inf, "median_steps": math.inf,
                    "success_rate": 0.0, "trials": trials}

        indptr = self._indptr_cu
        indices = self._indices_cu
        device = indptr.device

        B = int(trials)
        # batch init: cycle through start roles
        cur = torch.as_tensor([start_ids[i % len(start_ids)] for i in range(B)], device=device, dtype=torch.long)
        prev = torch.full_like(cur, -1)

        target = torch.as_tensor(target_ids, device=device, dtype=torch.long)  # [T]
        seen = torch.zeros((B, target.numel()), device=device, dtype=torch.bool)
        done = torch.zeros(B, device=device, dtype=torch.bool)
        steps = torch.zeros(B, device=device, dtype=torch.int32)

        for t in range(max_steps):
            # record hits this step
            hit = (cur.unsqueeze(1) == target.unsqueeze(0))
            seen |= hit
            all_seen = seen.all(dim=1)
            newly_done = (~done) & all_seen
            steps[newly_done] = t
            done |= newly_done
            if done.all():
                break

            nxt = node2vec_next(prev, cur, indptr, indices, p=float(p), q=float(q))
            prev, cur = cur, nxt

        # final tally
        steps_host = steps.detach().cpu().numpy()
        done_host = done.detach().cpu().numpy()
        succ = float(done_host.mean())
        valid = steps_host[done_host]
        mean_steps = float(valid.mean()) if valid.size else float("inf")
        median_steps = float(np.median(valid)) if valid.size else float("inf")

        return {
            "user": u,
            "num_targets": int(target.numel()),
            "mean_steps": mean_steps,
            "median_steps": median_steps,
            "success_rate": succ,
            "trials": B,
        }


def nx_to_csr_tensors(G_ud):
    """
    Map nodes -> contiguous ids and build an undirected CSR on CUDA (rows sorted).
    Returns: nid (dict), nodes(list), indptr_t (CUDA), indices_t (CUDA)
    """
    nodes = list(G_ud.nodes())
    nid = {n: i for i, n in enumerate(nodes)}
    N = len(nodes)

    rows, cols = [], []
    for u, v in G_ud.edges():
        ui, vi = nid[u], nid[v]
        rows += [ui, vi]
        cols += [vi, ui]

    rows = np.asarray(rows, dtype=np.int64)
    cols = np.asarray(cols, dtype=np.int64)

    order = np.lexsort((cols, rows))
    rows, cols = rows[order], cols[order]

    indptr = np.zeros(N + 1, dtype=np.int64)
    np.add.at(indptr, rows + 1, 1)
    np.cumsum(indptr, out=indptr)

    indptr_t = torch.as_tensor(indptr, device="cuda")
    indices_t = torch.as_tensor(cols, device="cuda")
    return nid, nodes, indptr_t, indices_t


@torch.no_grad()
def node2vec_next(prev, cur, indptr, indices, p: float, q: float):
    """
    One batched node2vec step on CUDA.
    prev, cur: [B] int64 (prev = -1 means first step)
    indptr: [N+1], indices: [M] - CSR
    """
    B = cur.numel()
    row_start = indptr[cur]
    row_end   = indptr[cur + 1]
    deg       = row_end - row_start
    dead      = deg == 0

    # First step: uniform over neighbors
    u = torch.rand(B, device=cur.device)
    off = (u * torch.clamp(deg, min=1)).long()
    nxt = indices[row_start + off]  # provisional (uniform)

    has_prev = prev >= 0
    if has_prev.any():
        idx = torch.nonzero(has_prev, as_tuple=False).squeeze(1)
        cur_i  = cur[idx]
        prev_i = prev[idx]
        s_i = indptr[cur_i]
        e_i = indptr[cur_i + 1]
        deg_i = (e_i - s_i).tolist()

        # Flatten neighbor rows
        nbrs_flat = torch.cat([indices[s:e] for s, e in zip(s_i.tolist(), e_i.tolist())])  # [sum(deg_i)]
        seg = torch.repeat_interleave(
            torch.arange(idx.numel(), device=cur.device),
            torch.as_tensor(deg_i, device=cur.device)
        )

        # Default weight 1/q
        w = torch.full_like(nbrs_flat, 1.0 / q, dtype=torch.float32)

        # Case x == prev -> 1/p
        w[(nbrs_flat == torch.repeat_interleave(prev_i, torch.as_tensor(deg_i, device=cur.device)))] = 1.0 / p

        # Case (x, prev) is an edge -> 1
        # Check membership via CSR binary search inside N(x)
        x_s = indptr[nbrs_flat]
        x_e = indptr[nbrs_flat + 1]
        pos = torch.searchsorted(indices[x_s], prev_i[seg])
        pos = torch.minimum(pos, (x_e - x_s - 1).clamp_min(0))
        is_edge = (x_e > x_s) & (indices[x_s + pos] == prev_i[seg])
        w[is_edge] = 1.0

        # Sample one neighbor per row from w
        eps = 1e-12
        wsum = torch.zeros(idx.numel(), device=cur.device, dtype=torch.float32).index_add_(0, seg, w)
        probs = w / (wsum[seg] + eps)

        r = torch.rand(idx.numel(), device=cur.device)
        nxt_idx = []
        ptr = 0
        for k, d in enumerate(deg_i):
            if d == 0:
                nxt_idx.append(cur_i[k])
                continue
            slice_probs = probs[ptr:ptr + d]
            slice_nbrs  = nbrs_flat[ptr:ptr + d]
            c = torch.cumsum(slice_probs, dim=0)
            pick = slice_nbrs[torch.searchsorted(c, r[k])]
            nxt_idx.append(pick)
            ptr += d
        nxt_idx = torch.stack(nxt_idx)

        nxt[has_prev] = nxt_idx

    # stay if dead
    nxt = torch.where(dead, cur, nxt)
    return nxt





def run_random_walk(UR, RR, RP):
    users = {e[0] for e in UR}
    spec = RHSpec(user_role=UR, role_role=RR, role_perm=RP, inherit_senior_to_junior=True, lazy=True)
    A = RoleWalkAnalyzer(spec)

    # Show each user's reachable permissions
    # for u in users:
        # print(u, "authorizations:", sorted(A.user_reachable_perms(u)))

    # Estimate cover time to reach ALL of each user's permissions
    # out = A.estimate_for_all_users(trials=1, max_steps=200000)
    results = []
    print('Total: ', len(A.users))
    for u in sorted(A.users):
        # print('CUDA: ', A.cuda_available)
        if len(results) % 10 == 0:
            print('Completed: ', len(results))
        # A.cuda_available = False
        if A.cuda_available:
            # results.append(A.estimate_cover_time_for_user_gpu(u, trials=5, max_steps=100000, p=1.0, q=0.1))
            results.append(A.estimate_cover_time_for_user(u, trials=5, max_steps=100000))

        else:
            results.append(A.estimate_cover_time_for_user(u, trials=5, max_steps=100000))

    # print('RESULTS:')


    # pprint(results)
    median_steps_for_rh = 0
    num_unsuccessful = 0
    for row in results:
        if row['median_steps'] == np.inf and row['success_rate'] == 0:
            num_unsuccessful += 1
        else:
            median_steps_for_rh += row['median_steps']
        # paths = row['paths']
        u = row['user']
        # targets = A.user_reachable_perms(u)

        # pos = nx.spring_layout(A.G_ud, seed=3)
        # for path in paths:
        #     draw_walk_static(A.G_ud, path, targets=targets, pos=pos, title=f"Random walk for {u}")

        # print(row)
    median_steps_for_rh = median_steps_for_rh / len(results)
    print('median_steps for RH: ', median_steps_for_rh)
    print('# unsuccessful walks for RH: ', num_unsuccessful)
