
# role_walk_reproducible.py
# Reproducible random-walk cover-time estimator for Role Hierarchies (CPU/GPU).
# - Deterministic node/edge ordering
# - Single base_seed used across numpy & torch (explicit generators)
# - Optional CUDA path with deterministic torch.rand via generator
#
# Usage:
#   from role_walk_reproducible import RHSpec, RoleWalkAnalyzer, run_random_walk
#   results = run_random_walk(UR, RR, RP, base_seed=20251008)
#
#   # Or construct manually:
#   spec = RHSpec(user_role=UR, role_role=RR, role_perm=RP)
#   A = RoleWalkAnalyzer(spec, walk_mode="node2vec", p=1.0, q=0.25, base_seed=20251008)
#   out = A.estimate_for_all_users(trials=5, max_steps=100000)
#
from __future__ import annotations

import os
import math
import random
from dataclasses import dataclass
from typing import Dict, List, Tuple, Set, Optional

import numpy as np
import networkx as nx
import torch


# --- Types ---
User = ''
Role = None
Perm = ''


# --- Seeding helper ---
def set_global_seed(seed: int, deterministic_torch: bool = True):
    """Seed Python, NumPy, and Torch; enable deterministic Torch kernels where possible."""
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    if deterministic_torch:
        torch.use_deterministic_algorithms(True)
        try:
            import torch.backends.cudnn as cudnn
            cudnn.deterministic = True
            cudnn.benchmark = False
        except Exception:
            pass  # cudnn may be unavailable depending on build


@dataclass
class RHSpec:
    user_role: List[Tuple[User, Role]]
    role_role: List[Tuple[Role, Role]]  # default: (senior -> junior)
    role_perm: List[Tuple[Role, Perm]]
    inherit_senior_to_junior: bool = True  # flip if your edges are (junior->senior)
    lazy: bool = True


class RoleWalkAnalyzer:
    def __init__(
        self,
        spec: RHSpec,
        walk_mode: str = "uniform",
        p: float = 1.0,
        q: float = 0.25,
        base_seed: int = 12345,
        torch_deterministic: bool = True,
    ):
        self.spec = spec
        self.walk_mode = walk_mode  # "uniform" or "node2vec"
        self.p = float(p)
        self.q = float(q)
        self.base_seed = int(base_seed)

        # Seed all libs and store per-class RNGs
        set_global_seed(self.base_seed, deterministic_torch=torch_deterministic)
        self._np_rng = np.random.default_rng(self.base_seed)

        self.G_dir = nx.DiGraph()

        # Deterministic node ordering (stringify types + values)
        keyf = lambda x: (str(type(x)), str(x))
        self.users: List[User] = sorted({u for u, _ in spec.user_role}, key=keyf)
        self.roles: List[Role] = sorted(
            {r for _, r in spec.user_role} | {a for a, _ in spec.role_role} | {b for _, b in spec.role_role},
            key=keyf,
        )
        self.perms: List[Perm] = sorted({p for _, p in spec.role_perm}, key=keyf)

        # Tag nodes
        for u in self.users:
            self.G_dir.add_node(u, kind="U")
        for r in self.roles:
            self.G_dir.add_node(r, kind="R")
        for p_ in self.perms:
            self.G_dir.add_node(p_, kind="P")

        # Edges
        self.G_dir.add_edges_from(spec.user_role)
        if spec.inherit_senior_to_junior:
            self.G_dir.add_edges_from(spec.role_role)
        else:
            self.G_dir.add_edges_from([(jr, sr) for (sr, jr) in spec.role_role])
        self.G_dir.add_edges_from(spec.role_perm)

        # Role descendants (R-only)
        self._downstream_roles: Dict[Role, Set[Role]] = {}
        R_only = self.G_dir.subgraph([x for x, d in self.G_dir.nodes(data=True) if d["kind"] == "R"])
        for r in R_only.nodes():
            self._downstream_roles[r] = set(nx.descendants(R_only, r)) | {r}

        # Undirected exploration graph
        self.G_ud = nx.Graph()
        for u in self.users:
            self.G_ud.add_node(u, kind="U")
        for r in self.roles:
            self.G_ud.add_node(r, kind="R")
        for p_ in self.perms:
            self.G_ud.add_node(p_, kind="P")

        # R<->R
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

        # Deterministic neighbors
        self._neighbors = {
            n: np.array(sorted(self.G_ud.neighbors(n), key=keyf))
            for n in self.G_ud.nodes()
        }
        self._deg = {n: len(self._neighbors[n]) for n in self.G_ud.nodes()}

        # Torch generator (explicit)
        self.cuda_available = torch.cuda.is_available()
        if self.cuda_available:
            self._torch_gen = torch.Generator(device="cuda").manual_seed(self.base_seed)
        else:
            self._torch_gen = torch.Generator(device="cpu").manual_seed(self.base_seed)

        # GPU CSR (deterministic)
        if self.cuda_available:
            self._nid, self._nodes_rev, self._indptr_cu, self._indices_cu = nx_to_csr_tensors(self.G_ud)
            self._id_users = {self._nid[n] for n in self.users if n in self._nid}
            self._id_roles = {self._nid[n] for n in self.roles if n in self._nid}
            self._id_perms = {self._nid[n] for n in self.perms if n in self._nid}
        else:
            self._nid, self._nodes_rev, self._indptr_cu, self._indices_cu = None, None, None, None

    # --- Walk transitions ---
    def _transition_node2vec(self, prev, cur, rng: np.random.Generator):
        nbrs = self._neighbors[cur]
        if nbrs.size == 0:
            return cur
        if prev is None:
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

    # --- Public APIs ---
    def user_reachable_perms(self, u: User) -> Set[Perm]:
        assert u in self.users, f"Unknown user {u}"
        assigned_roles = [v for _, v in self.G_dir.out_edges(u)]
        perms: Set[Perm] = set()
        for r in assigned_roles:
            for r2 in self._downstream_roles.get(r, {r}):
                for _, p in self.G_dir.out_edges(r2):
                    if self.G_dir.nodes[p]["kind"] == "P":
                        perms.add(p)
        return perms

    def estimate_cover_time_for_user(
        self,
        u: User,
        trials: int = 128,
        max_steps: int = 1_000_000,
        seed: Optional[int] = None,
    ) -> Dict[str, float | int]:
        # Optional reseed for this call
        if seed is not None:
            self._np_rng = np.random.default_rng(int(seed))

        targets: Set[Perm] = self.user_reachable_perms(u)
        if not targets:
            return {"user": u, "num_targets": 0, "mean_steps": 0.0, "median_steps": 0.0, "success_rate": 1.0, "trials": trials}

        start_roles = [v for _, v in self.G_dir.out_edges(u) if self.G_dir.nodes[v]["kind"] == "R"]
        if not start_roles:
            return {"user": u, "num_targets": len(targets), "mean_steps": math.inf, "median_steps": math.inf, "success_rate": 0.0, "trials": trials}

        target_idx = {t: i for i, t in enumerate(sorted(targets, key=lambda x: (str(type(x)), str(x))))}
        visited_mask = np.zeros(len(targets), dtype=bool)

        steps_list: List[Optional[int]] = []
        for _ in range(trials):
            rng = np.random.default_rng(self._np_rng.integers(0, 2**63 - 1))
            cur = rng.choice(start_roles)
            prev = None
            visited_mask[:] = False
            steps = 0
            if cur in targets:
                visited_mask[target_idx[cur]] = True
            while steps < max_steps and not visited_mask.all():
                nxt = self._next_step(prev, cur, rng)
                prev, cur = cur, nxt
                if isinstance(cur, str) and not (cur.startswith('U') or cur.startswith('u') or cur.startswith('P') or cur.startswith('p')):
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
            "trials": trials,
        }

    @torch.no_grad()
    def estimate_cover_time_for_user_gpu(
        self, u: User, trials: int = 5, max_steps: int = 10000,
        p: float = 1.0, q: float = 1.0, seed: int = 12345
    ):
        assert self.cuda_available, "CUDA not available."
        targets = self.user_reachable_perms(u)
        if not targets:
            return {"user": u, "num_targets": 0, "mean_steps": 0.0, "median_steps": 0.0, "success_rate": 1.0, "trials": trials}

        start_roles = [v for _, v in self.G_dir.out_edges(u) if self.G_dir.nodes[v]["kind"] == "R"]
        if not start_roles:
            return {"user": u, "num_targets": len(targets), "mean_steps": math.inf, "median_steps": math.inf, "success_rate": 0.0, "trials": trials}

        torch.cuda.manual_seed(seed)

        # map to ids
        start_ids = self._to_ids(start_roles)
        target_ids = self._to_ids(targets)

        if len(start_ids) == 0 or len(target_ids) == 0:
            return {"user": u, "num_targets": len(targets), "mean_steps": math.inf, "median_steps": math.inf, "success_rate": 0.0, "trials": trials}

        indptr = self._indptr_cu
        indices = self._indices_cu
        device = indptr.device

        B = int(trials)
        cur = torch.as_tensor([start_ids[i % len(start_ids)] for i in range(B)], device=device, dtype=torch.long)
        prev = torch.full_like(cur, -1)

        target = torch.as_tensor(target_ids, device=device, dtype=torch.long)  # [T]
        seen = torch.zeros((B, target.numel()), device=device, dtype=torch.bool)
        done = torch.zeros(B, device=device, dtype=torch.bool)
        steps = torch.zeros(B, device=device, dtype=torch.int32)

        for t in range(max_steps):
            hit = (cur.unsqueeze(1) == target.unsqueeze(0))
            seen |= hit
            all_seen = seen.all(dim=1)
            newly_done = (~done) & all_seen
            steps[newly_done] = t
            done |= newly_done
            if done.all():
                break

            nxt = node2vec_next(prev, cur, indptr, indices, p=float(p), q=float(q), gen=self._torch_gen)
            prev, cur = cur, nxt

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

    def estimate_for_all_users(self, **kw) -> List[Dict[str, float | int]]:
        return [self.estimate_cover_time_for_user(u, **kw) for u in self.users]

    def _to_ids(self, nodes_iterable):
        if not self.cuda_available:
            raise RuntimeError("CUDA not available; cannot map ids for GPU walk.")
        return [self._nid[n] for n in nodes_iterable if n in self._nid]


def nx_to_csr_tensors(G_ud):
    """Deterministic CSR (node & edge order sorted)."""
    keyf = lambda x: (str(type(x)), str(x))
    nodes = sorted(G_ud.nodes(), key=keyf)
    nid = {n: i for i, n in enumerate(nodes)}
    N = len(nodes)

    rows, cols = [], []
    for u, v in sorted(G_ud.edges(), key=lambda e: (str(type(e[0])), str(e[0]), str(type(e[1])), str(e[1]))):
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
def node2vec_next(prev, cur, indptr, indices, p: float, q: float, gen: torch.Generator):
    """One batched node2vec step on CUDA with explicit generator for determinism."""
    B = cur.numel()
    row_start = indptr[cur]
    row_end   = indptr[cur + 1]
    deg       = row_end - row_start
    dead      = deg == 0

    # First step: uniform over neighbors
    u = torch.rand(B, device=cur.device, generator=gen)
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

        nbrs_flat = torch.cat([indices[s:e] for s, e in zip(s_i.tolist(), e_i.tolist())])
        seg = torch.repeat_interleave(
            torch.arange(idx.numel(), device=cur.device),
            torch.as_tensor(deg_i, device=cur.device)
        )

        w = torch.full_like(nbrs_flat, 1.0 / q, dtype=torch.float32)
        w[(nbrs_flat == torch.repeat_interleave(prev_i, torch.as_tensor(deg_i, device=cur.device)))] = 1.0 / p

        x_s = indptr[nbrs_flat]
        x_e = indptr[nbrs_flat + 1]
        pos = torch.searchsorted(indices[x_s], prev_i[seg])
        pos = torch.minimum(pos, (x_e - x_s - 1).clamp_min(0))
        is_edge = (x_e > x_s) & (indices[x_s + pos] == prev_i[seg])
        w[is_edge] = 1.0

        eps = 1e-12
        wsum = torch.zeros(idx.numel(), device=cur.device, dtype=torch.float32).index_add_(0, seg, w)
        probs = w / (wsum[seg] + eps)

        r = torch.rand(idx.numel(), device=cur.device, generator=gen)
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

    nxt = torch.where(dead, cur, nxt)
    return nxt


# --- Convenience runner ---
def run_random_walk(UR, RR, RP, base_seed: int = 20251008, trials: int = 5, max_steps: int = 100000,
                    walk_mode: str = "node2vec", p: float = 1.0, q: float = 0.25):
    """
    Returns list of per-user dicts with mean/median/success_rate. Deterministic given base_seed.
    """
    spec = RHSpec(user_role=UR, role_role=RR, role_perm=RP, inherit_senior_to_junior=True, lazy=True)
    A = RoleWalkAnalyzer(spec, walk_mode=walk_mode, p=p, q=q, base_seed=base_seed)

    results = []
    for u in A.users:
        # Prefer CPU deterministic path; uncomment GPU if desired.
        if A.cuda_available:
            results.append(A.estimate_cover_time_for_user_gpu(u, trials=trials, max_steps=max_steps, p=p, q=q, seed=base_seed))
        else:
            results.append(A.estimate_cover_time_for_user(u, trials=trials, max_steps=max_steps))

    return results


if __name__ == "__main__":
    # Minimal smoke test with a tiny RH
    UR = [("U1", "R_admin"), ("U2", "R_viewer")]
    RR = [("R_admin", "R_editor"), ("R_editor", "R_viewer")]
    RP = [("R_viewer", "P_read"), ("R_editor", "P_write"), ("R_admin", "P_delete")]

    res = run_random_walk(UR, RR, RP, base_seed=20251008, trials=3, max_steps=10000, walk_mode="node2vec", p=1.0, q=0.25)
    for r in res:
        print(r)