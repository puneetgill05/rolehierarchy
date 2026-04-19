import sys

import numpy as np
import numpy.typing as npt

from rich.pretty import pprint


def read_graph(filename: str) -> dict:
    with open(filename, 'r') as f:
        ret = dict()

        for line in f.readlines():
            if line.startswith('%'):
                continue
            else:
                line = line.strip()
                vertices = line.split()
                u = 'u' + (vertices[0].strip())
                p = 'p' + (vertices[1].strip())
                if u in ret:
                    ret[u].add(p)
                else:
                    ret[u] = {p}
    return ret


def to_adj_matrix(graph_dict: dict) -> npt.NDArray[np.int64]:
    nodes = list(graph_dict.keys())
    index_map = {node: i for i, node in enumerate(nodes)}

    n = len(nodes)
    adj_matrix = np.zeros((n, n), dtype=int)

    # Fill in adjacency matrix
    for src, neighbors in graph_dict.items():
        for dest in neighbors:
            i, j = index_map[src], index_map[dest]
            adj_matrix[i][j] = 1

    return adj_matrix

