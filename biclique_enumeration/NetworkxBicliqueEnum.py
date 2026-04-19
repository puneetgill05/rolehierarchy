import argparse
import os
import sys
from datetime import datetime

from minedgerolemining import readup
from minedgerolemining.readup import uptopu
from minedgerolemining.removedominators import neighbours
from minedgerolemining.removedominatorsbp import get_em, hasbeenremoved

prefix_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(f'{prefix_dir}')
sys.path.append(f'{prefix_dir}/..')
print(sys.path)


def getedgeset(em, up):
    # set of all edges
    edgeset = set()
    for u in up:
        for p in up[u]:
            e = tuple((u, p))
            if len(edgeset) % 10000 == 0:
                print(f'Added edges: {len(edgeset)}')
                pass
            if hasbeenremoved(e, em):
                continue
            edgeset.add(e)

    return edgeset


def update_up(up, em):
    pu = uptopu(up)

    def add_edge_to_up(g, new_up):
        if g[0] not in new_up:
            new_up[g[0]] = {g[1]}
        else:
            new_up[g[0]].add(g[1])

    new_up = dict()
    for e in getedgeset(em, up):
        add_edge_to_up(e, new_up)
        for f in neighbours(e, em, up, pu):
            if e != f:
                add_edge_to_up(f, new_up)
    return new_up


def nx_find_bicliquesbp(em, up, pu, nodes):
    # Adapted from networkx.find_cliques
    # Presumably dominators and zero-neighbour vertices have been
    # removed. But that's not a necessary condition

    if len(up) == 0:
        return

    edgeset = getedgeset(em, up)

    adj = {u: {v for v in neighbours(u, dict(), up, pu) if v != u} for u in edgeset}


    # Initialize Q with the given nodes and subg, cand with their nbrs
    Q = nodes[:] if nodes is not None else []
    cand = edgeset
    for node in Q:
        if node not in cand:
            raise ValueError(f"The given `nodes` {nodes} do not form a clique")
        cand &= adj[node]

    if not cand:
        yield Q[:]
        return

    subg = cand.copy()
    stack = []
    Q.append(None)

    u = max(subg, key=lambda u: len(cand & adj[u]))
    ext_u = cand - adj[u]

    try:
        while True:
            if ext_u:
                q = ext_u.pop()
                cand.remove(q)
                Q[-1] = q
                adj_q = adj[q]
                subg_q = subg & adj_q
                if not subg_q:
                    yield Q[:]
                else:
                    cand_q = cand & adj_q
                    if cand_q:
                        stack.append((subg, cand, ext_u))
                        Q.append(None)
                        subg = subg_q
                        cand = cand_q
                        u = max(subg, key=lambda u: len(cand & adj[u]))
                        ext_u = cand - adj[u]
            else:
                Q.pop()
                subg, cand, ext_u = stack.pop()
    except IndexError:
        pass


def print_biclique(biclique_edges: set):
    L = set()
    R = set()
    for e in biclique_edges:
        L.add(e[0])
        R.add(e[1])
    # print('Biclique')
    print((list(L), list(R)), end=',')


def run(upfilename: str):
    num_bicliques = 0
    start_time = datetime.now()
    up = readup.readup(upfilename)
    pu = readup.uptopu(up)
    em = get_em(upfilename)
    bicliques_found = list()
    for c in nx_find_bicliquesbp(em, up, pu, list()):
        if len(c) > 0:
            bicliques_found.append(c)
            print_biclique(c)
            # print('Biclique: ' + str(c))
            num_bicliques += 1
    print('# bicliques: ', num_bicliques)
    end_time = datetime.now()
    print(f'Time taken: {(end_time - start_time).total_seconds()} seconds')
    return bicliques_found


def main():
    parser = argparse.ArgumentParser(description="Read input graph file")
    parser.add_argument("input_file", type=str, help="Input UP graph file")

    args = parser.parse_args()
    upfilename = args.input_file
    run(upfilename)


if __name__ == "__main__":
    main()
