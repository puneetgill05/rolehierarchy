import copy
from typing import List, Set, Dict

import networkx as nx

from rh_utils import dict_to_digraph


def build_subset_dag(sets: list) -> dict:
    """
    Build a directed acyclic graph (as adjacency list) where:
      edge i -> j  iff  sets[i] ⊂ sets[j]  (proper subset)

    Returns:
        graph: dict mapping node index -> list of node indices it can go to
    """
    graph = {i: [] for i in range(len(sets))}
    for i, A in enumerate(sets):
        for j, B in enumerate(sets):
            if i == j:
                continue
            if A < B:
            # if A.issubset(B):
            #     to avoid cycles
                graph_copy = copy.deepcopy(graph)
                G_copy = dict_to_digraph(graph_copy)
                if nx.is_directed_acyclic_graph(G_copy):
                # if i not in graph[j]:
                    graph[i].append(j)
    return graph


def all_maximal_chains(sets: List[Set]) -> List[List[int]]:
    graph = build_subset_dag(sets)
    chains_idx: List[List[int]] = []

    def dfs(path: List[int]):
        last = path[-1]

        # Candidates that strictly contain the last set
        extensions = [nxt for nxt in graph[last] if nxt not in path]

        if not extensions:
            # No way to go higher -> this path is maximal
            chains_idx.append(path[:])
            return

        for nxt in extensions:
            dfs(path + [nxt])

    # Start DFS from every node, since the poset may have multiple minima
    for start in range(len(sets)):
        dfs([start])

    # Deduplicate chains that are identical by content, not by index identity
    # (Two different DFS starts might lead to exactly the same ordered sequence of sets.)
    seen = set()
    unique_idx_chains = []
    for chain in chains_idx:
        key = tuple(frozenset(sets[i]) for i in chain)
        if key not in seen:
            seen.add(key)
            unique_idx_chains.append(chain)
        else:
            #print(f'Duplicate chain: {key}')
            #print('Duplicate chain')
            pass

    return unique_idx_chains


def chains_as_sets(sets: list) -> list:
    idx_chains = all_maximal_chains(sets)
    return [[sets[i] for i in chain] for chain in idx_chains]


def pretty_print_chains(sets: List[Set]) -> list:
    """
    Print each maximal chain in a readable "A ⊂ B ⊂ C" style.
    """
    # for chain in chains_as_sets(sets):
    #     parts = [str(s) for s in chain]
    #     print(" ⊂ ".join(parts))
    return chains_as_sets(sets)


if __name__ == "__main__":
    sets_input = [
        {"u1"},
        {"u1", "u2"},
        {"u1", "u2", "u3"},
        {"u2"},
        {"u1", "u2", "u3", "u4"},
        {"x"},
        {"x", "y"},
    ]

    print("Maximal chains (strict containment):")
    pretty_print_chains(sets_input)
