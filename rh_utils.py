import json
from collections import defaultdict
from pathlib import Path
from typing import Dict

import networkx as nx


def RH_to_adj(RH: dict):
    adj = dict()
    for r in RH:
        for e in RH[r]:
            if isinstance(e, str):
                if e.startswith('u') or e.startswith('U'):
                    if e not in adj:
                        adj[e] = set()
                    adj[e].add(r)
                elif e.startswith('p') or e.startswith('P'):
                    if r not in adj:
                        adj[r] = set()
                        adj[e] = set()
                    adj[r].add(e)
            elif isinstance(e, int):
                if r not in adj:
                    adj[r] = set()
                adj[r].add(e)
    return adj


def adj_to_RH(adj: dict):
    RH = dict()
    for e in adj:
        for f in adj[e]:
            if isinstance(e, str) and (
                    e.startswith('u') or e.startswith('U') or e.startswith('p') or e.startswith('P')):
                if isinstance(f, int):
                    if f not in RH:
                        RH[f] = set()
                    RH[f].add(e)
            elif isinstance(e, int):
                if e not in RH:
                    RH[e] = set()
                RH[e].add(f)
    return RH


def dict_to_digraph(d: Dict, default_cap: float = 1.0) -> nx.DiGraph:
    G = nx.DiGraph()
    if not d:
        return G

    for u, nbrs in d.items():
        G.add_node(u)
        for v in nbrs:
            G.add_edge(u, v, capacity=float(default_cap))
    return G


def bucketize_by_value(d):
    buckets = defaultdict(list)
    for k, v in d.items():
        buckets[v].append(k)
    return dict(buckets)


def get_next_role(next_r, RH: dict, role_chain: list, visited: set, role_chains: list):
    visited.add(next_r)
    role_chain.append(next_r)
    roles_assigned_to_r = {x for x in RH[next_r] if isinstance(x, int) and not isinstance(x, bool)}
    diff = roles_assigned_to_r - visited
    if len(diff) == 0:
        role_chains.append(role_chain)
        # return role_chain
    else:
        for s in roles_assigned_to_r:
            get_next_role(s, RH, role_chain.copy(), visited.copy(), role_chains)
            # print('Completed role chain:', completed_role_chain)
            # role_chains.append(completed_role_chain)


def get_role_chains(start_r, RH: dict, visited: set):
    r = start_r
    role_chains = []
    visited.add(r)
    # role_chain.append(r)
    roles_assigned_to_r = {x for x in RH[r] if isinstance(x, int) and not isinstance(x, bool)}

    for s in roles_assigned_to_r:
        # completed_role_chain = get_role_chain(s, RH, role_chain.copy(), visited)
        get_next_role(s, RH, [r], visited.copy(), role_chains)

        # role_chains.append(completed_role_chain)
    if len(role_chains) == 0:
        role_chains.append([r])
    return role_chains



def read_rh_file(rh_file_path: Path) -> dict:
    RH = json.load(open(rh_file_path, 'r'))
    RH_new = dict()
    for r in RH.keys():
        if isinstance(r, str) and r.isdigit():
            RH_new[int(r)] = set(RH[r])

    for r in RH_new.keys():
        for v in RH_new[r]:
            if isinstance(v, str) and v.isdigit():
                RH_new[r].remove(v)
                RH_new[r].add(int(v))
    return RH_new


def read_rbac_file(rbac_file_path: str) -> dict:
    RBAC = json.load(open(rbac_file_path, 'r'))
    RBAC_new = dict()
    for r in RBAC.keys():
        if isinstance(r, str) and r.isdigit():
            if int(r) not in RBAC_new:
                RBAC_new[int(r)] = set()

            for e in RBAC[r]:
                RBAC_new[int(r)].add((int(e[0]), int(e[1])))
    return RBAC_new


