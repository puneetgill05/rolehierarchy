import datetime
import math
import os
import sys
from enum import Enum
from pprint import pprint


prefix_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(f'{prefix_dir}/..')
sys.path.append(f'{prefix_dir}/../hierarchical_miner')
print(sys.path)

from utils import bicliques_to_roles_as_edges, get_roles_mapped, check_roles
from readup import readup

class GreedyStrategy(Enum):
    FEWEST_UNCOVERED_EDGES = 1
    MOST_UNCOVERED_EDGES = 2

def get_neighbours(v: str, up_formatted: dict, pu_formatted: dict):
    neighs = set()
    if v.startswith('u_'):
        neighs = neighs.union(up_formatted[v])
    elif v.startswith('p_'):
        neighs = neighs.union(pu_formatted[v])
    return neighs

def get_adjacent_vertices_to_neighbours(neighs: set, up_formatted: dict, pu_formatted: dict):
    all_adjacent_vertices = set()
    all_adjacent_vertices = (all_adjacent_vertices.union(up_formatted.keys())
                            .union(pu_formatted.keys()))

    for n in neighs:
        adjacent_vertices = set()
        if n.startswith('u_'):
            adjacent_vertices = adjacent_vertices.union(up_formatted[n])
        elif n.startswith('p_'):
            adjacent_vertices = adjacent_vertices.union(pu_formatted[n])
        all_adjacent_vertices = all_adjacent_vertices.intersection(adjacent_vertices)
    return all_adjacent_vertices


def next_vertex(V: set, up_formatted: dict, pu_formatted: dict, vertices_explored: set, strategy: GreedyStrategy):
    def get_vertex(opt_num_edges: float):
        num_edges = 0
        opt_vertex = None
        for v in V.difference(vertices_explored):
            if v.startswith('u_'):
                num_edges = len(up_formatted[v])
            elif v.startswith('p_'):
                num_edges = len(pu_formatted[v])
            if strategy == GreedyStrategy.MOST_UNCOVERED_EDGES:
                if num_edges > 0 and num_edges > opt_num_edges:
                    opt_num_edges = num_edges
                    opt_vertex = v
            elif strategy == GreedyStrategy.FEWEST_UNCOVERED_EDGES:
                if 0 < num_edges < opt_num_edges:
                    opt_num_edges = num_edges
                    opt_vertex = v
        return opt_vertex

    opt_v = None
    if strategy == GreedyStrategy.MOST_UNCOVERED_EDGES:
        opt_v = get_vertex(0)
    elif strategy == GreedyStrategy.FEWEST_UNCOVERED_EDGES:
        opt_v = get_vertex(math.inf)
    return opt_v


def run_greedy(upfilename: str):
    up = readup(upfilename)

    def inverse_map(mymap: dict):
        inv_map = dict()
        for k in mymap:
            for val in mymap[k]:
                if val not in inv_map:
                    inv_map[val] = {k}
                else:
                    inv_map[val].add(k)
        return inv_map

    up_formatted = dict()
    for u in up:
        up_formatted[f'u_{u}'] = {f'p_{p}' for p in up[u]}

    print('UP formatted:')
    pprint(up_formatted)
    pu_formatted = inverse_map(up_formatted)
    print('PU formatted:')
    pprint(pu_formatted)

    V = set(up_formatted.keys())
    for u in up_formatted:
        V = V.union(up_formatted[u])
    print('All vertices:')
    pprint(V)

    vertices_explored = set()
    bicliques = set()
    while True:
        # v = random.choice(list(V))
        v = next_vertex(V, up_formatted, pu_formatted, vertices_explored, strategy=GreedyStrategy.FEWEST_UNCOVERED_EDGES)

        print('Random vertex: ', v)
        neighs = get_neighbours(v, up_formatted, pu_formatted)
        # print('Neighbours:')
        # pprint(neighs)

        adjacent_vertices = get_adjacent_vertices_to_neighbours(neighs, up_formatted, pu_formatted)

        biclique = tuple(neighs.union(adjacent_vertices))

        bicliques.add(biclique)
        roles_as_edges = bicliques_to_roles_as_edges(bicliques)
        vertices_explored.add(v)

        if check_roles(roles_as_edges, up):
            break
    print('Bicliques:')
    pprint(bicliques)
    print('Number of bicliques: ', len(bicliques))

    # print('Roles as edges:')
    # pprint(roles_as_edges)
    # roles_mapped = get_roles_mapped(roles_as_edges)
    # print('Roles:')
    # pprint(roles_mapped)
    return roles_as_edges


def main():
    print('Start time:', datetime.datetime.now())
    sys.stdout.flush()

    if len(sys.argv) != 2:
        print('Usage: ', end='')
        print(sys.argv[0], end=' ')
        print('<input-file>')
        return

    upfilename = sys.argv[1]
    run_greedy(upfilename)



if __name__ == '__main__':
    main()
