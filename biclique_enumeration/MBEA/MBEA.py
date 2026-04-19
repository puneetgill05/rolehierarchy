import argparse
import os
import sys
from datetime import datetime, timedelta
from itertools import product
from typing import Set, List, Collection

from colorama import Style, Fore

from minedgerolemining.readup import readup_and_usermap_permmap

prefix_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(f'{prefix_dir}')
sys.path.append(f'{prefix_dir}/../..')
print(sys.path)

from readup import uptopu, readup
from removedominatorsbp import hasbeenremoved, neighbours, get_em

from Biclique import Biclique
from BipartiteGraph import BipartiteGraph
from Vertex import Vertex


def sort_by_common_neighbourhood_size(P: Collection[Vertex]) -> List[Vertex]:
    neighbourhood_size = dict()
    for v in P:
        neighbourhood_size[v] = len(v.neighbours)
    sortedP = sorted(neighbourhood_size, key=neighbourhood_size.get)
    return sortedP


# G: a bipartite graph G = ((U, V), E)
# L: set of vertices of U, that are common neighbours of vertices in R
# R: set of vertices of V belonging to the current biclique, initially empty
# P: set of vertices of V that can be added to R, initially P = V
# Q: set of vertices used to determine maximality, initially empty (set of vertices considered to add to R)
def mbea(G: BipartiteGraph, L: Set[Vertex], R: Set[Vertex], P: List[Vertex], Q: Set[Vertex],
         bicliques: Set[Biclique], em: dict, imbea=True):
    while len(P) > 0:
        P = sort_by_common_neighbourhood_size(P)
        # pick a candidate to add in R
        x = P.pop(0)
        R_prime = R.union({x})
        # Get the neighbours of x in L, update the L to L'
        L_prime = {u for u in L if u in x.neighbours}

        # iMBEA
        if imbea:
            L_star = L.difference(L_prime)
            C = {x}
        else:
            L_star = set()
            C = set()

        P_prime = list()
        Q_prime = set()

        # Observation 2: check maximality
        is_maximal = True
        # for all the vertices considered to be added to R but then rejected
        for v in Q:
            # Get all the neighbours of v in L_prime
            N_v = {u for u in L_prime if u in v.neighbours}

            # Observation 4: end of branch
            # if all the neighbours of v are in the new L, that is L', this needs to be pruned, that is why
            # is_maximal is set to False
            if len(N_v) == len(L_prime):
                is_maximal = False
                break
            # otherwise, update Q to Q' by adding v
            elif len(N_v) > 0:
                Q_prime.add(v)

        # At this point Q is updated
        if is_maximal:
            # check for other candidate vertices in P
            for v in P:
                if v == x:
                    continue
                # Get the neighbours of v in L'
                N_v = {u for u in L_prime if u in v.neighbours}

                # if this happens, we know that all neighbours of v are in the L' and we can add it to R,
                # so R is updated to R'
                if len(N_v) == len(L_prime):
                    R_prime.add(v)

                    # iMBEA
                    # Get all neighbours of v in L_star
                    if imbea:
                        S = {u for u in L_star if u in v.neighbours}
                        # iMBEA
                        if len(S) == 0:
                            C.add(v)

                # if this happens, there are neighbours of v which are not in L', we can add it back into P to try
                # again later
                elif len(N_v) > 0 and imbea:
                    # iMBEA
                    # Insert v into P_prime in non-decreasing order of common neighbourhood size
                    P_prime.append(v)
                    # P_prime = sort_by_common_neighbourhood_size(P_prime)

            # At this point, we have a maximal biclique (L', R')
            # print_biclique(L_prime, R_prime)
            # is_biclique_correct = True
            # for l in L_prime:
            #     for r in R_prime:
            #         if hasbeenremoved((l, r), em):
            #             is_biclique_correct = False
            # if is_biclique_correct:
            bc = Biclique(L_prime, R_prime)
            if bc not in bicliques:
                bicliques.add(bc)

            # if there are more candidate vertices that we can add, repeat
            if len(P_prime) > 0:
                mbea(G, L_prime, R_prime, P_prime, Q_prime, bicliques, em, imbea)

        # iMBEA
        if imbea:
            Q = Q.union(C)
            P = [v for v in P if v not in C]


def print_biclique(L: Set[Vertex], R: Set[Vertex]):
    # print('Biclique:')
    l = list(map(lambda l: str(l.label), L))
    r = list(map(lambda r: str(r.label), R))
    print((l, r))
    # print(r)


def getedgeset(em, up):
    edgeset = set()
    for u in up:
        for p in up[u]:
            e = (u, p)
            # if e not in em or (e in em and (-1, -1) == em[e][:2]):
            if hasbeenremoved(e, em):
                continue
            edgeset.add(e)
    return edgeset


def is_in_biclique(bipartiteG: BipartiteGraph, e: tuple, f: tuple) -> bool:
    el = bipartiteG.get_vertex_from_L(e[0])
    er = bipartiteG.get_vertex_from_R(e[1])

    fl = bipartiteG.get_vertex_from_L(f[0])
    fr = bipartiteG.get_vertex_from_R(f[1])

    return el in fr.neighbours and fl in er.neighbours


def update_up(up, em):
    pu = uptopu(up)

    def add_edge_to_up(g, new_up):
        if g[1] in up[g[0]] and g in edgeset:
            if g[0] not in new_up:
                new_up[g[0]] = {g[1]}
            else:
                new_up[g[0]].add(g[1])

    new_up = dict()
    edgeset = getedgeset(em, up)
    for e in edgeset:
        add_edge_to_up(e, new_up)
        for f in neighbours(e, em, up, pu):
            if e != f:
                add_edge_to_up(f, new_up)
                add_edge_to_up((e[0], f[1]), new_up)
                add_edge_to_up((f[0], e[1]), new_up)
    return new_up


def maximize_bicliques(bicliques: list[Biclique], origBicliques: list[Biclique]):
    ret_bicliques = []
    for b in bicliques:
        for ob in origBicliques:
            if b.L.issubset(ob.L) and b.R.issubset(ob.R):
                ret_bicliques.append(ob)
                # break
    return ret_bicliques


def add_adj_info_back(bipartiteG: BipartiteGraph, up: dict, pu: dict, em: dict):
    edgeset = getedgeset(em, up)
    adj = {u: {v for v in neighbours(u, em, up, pu) if v != u} for u in edgeset}

    def add_to_dict(e: tuple, em: dict, up: dict, tmp: dict):
        if e[1] in up[e[0]]:
            if e[0] not in tmp:
                tmp[e[0]] = {e[1]}
            else:
                tmp[e[0]].add(e[1])
        return tmp

    tmp = dict()
    for e in adj:
        tmp = add_to_dict(e, em, up, tmp)
        for f in adj[e]:
            tmp = add_to_dict((f[0], e[1]), em, up, tmp)
        #     tmp = add_to_dict((e[0], f[1]), em, up, tmp)

    num_edges = 0
    for u in tmp:
        num_edges += len(tmp[u])
    bipartiteG = BipartiteGraph.from_dict(tmp)
    # for e in adj:
    #     el = bipartiteG.get_vertex_from_L(e[0])
    #     er = bipartiteG.get_vertex_from_R(e[1])
    #     for f in adj[e]:
    #         fl = bipartiteG.get_vertex_from_L(f[0])
    #         fr = bipartiteG.get_vertex_from_R(f[1])
    #         if f[1] in up[e[0]]:
    #             el.add_neighbour_symmetric(fr)
    #         if e[1] in up[f[0]]:
    #             fl.add_neighbour_symmetric(er)
    bipartiteG.update()
    return bipartiteG


def find_bicliques(upfilename: str, run_remove_dominators: bool = True):
    print(Fore.BLUE)
    start_time = datetime.now()
    # up = utils.read_graph(args.input_file)
    up = readup(upfilename)
    pu = uptopu(up)
    em = get_em(upfilename)
    new_up = update_up(up, em)
    if not run_remove_dominators:
        new_up = up

    # networkx_up = {'u1122': {'p241'}, 'u3376': {'p241', 'p586'}, 'u2344': {'p1216', 'p241'}, 'u2759': {'p229', 'p241'}, 'u3379': {'p265'}, 'u532': {'p277'}, 'u2612': {'p289', 'p230'}, 'u731': {'p264'}, 'u520': {'p254'}, 'u3377': {'p190'}, 'u1934': {'p900', 'p287'}, 'u3011': {'p900', 'p281'}, 'u2311': {'p288', 'p828'}, 'u2316': {'p288', 'p287', 'p281'}, 'u2183': {'p586', 'p281'}, 'u2170': {'p285'}, 'u3041': {'p229', 'p586'}, 'u2350': {'p1216', 'p586'}, 'u3300': {'p349'}, 'u3189': {'p1328'}, 'u3111': {'p345'}, 'u2432': {'p259', 'p287'}, 'u2100': {'p218', 'p828'}, 'u2285': {'p218'}, 'u1812': {'p239'}, 'u2392': {'p237'}, 'u2775': {'p289'}, 'u2393': {'p230', 'p285'}, 'u3289': {'p313'}}

    bipartiteG = BipartiteGraph.from_dict(new_up)

    final_up = dict()
    for l in bipartiteG.L:
        if l not in final_up:
            final_up[l.label] = {r.label for r in l.neighbours}
        else:
            final_up[l.label] = final_up[l.label].union({r.label for r in l.neighbours})

    bicliques = set()

    mbea(G=bipartiteG, L=bipartiteG.L, R=set(), P=list(bipartiteG.R), Q=set(), bicliques=bicliques, em=em, imbea=True)
    return bicliques, final_up

def find_bicliques_old(upfilename: str, run_remove_dominators: bool = True):
    print(Fore.BLUE)
    start_time = datetime.now()
    # up = utils.read_graph(args.input_file)
    up = readup(upfilename)
    pu = uptopu(up)
    em = get_em(upfilename)
    new_up = update_up(up, em)
    if not run_remove_dominators:
        new_up = up

    # networkx_up = {'u1122': {'p241'}, 'u3376': {'p241', 'p586'}, 'u2344': {'p1216', 'p241'}, 'u2759': {'p229', 'p241'}, 'u3379': {'p265'}, 'u532': {'p277'}, 'u2612': {'p289', 'p230'}, 'u731': {'p264'}, 'u520': {'p254'}, 'u3377': {'p190'}, 'u1934': {'p900', 'p287'}, 'u3011': {'p900', 'p281'}, 'u2311': {'p288', 'p828'}, 'u2316': {'p288', 'p287', 'p281'}, 'u2183': {'p586', 'p281'}, 'u2170': {'p285'}, 'u3041': {'p229', 'p586'}, 'u2350': {'p1216', 'p586'}, 'u3300': {'p349'}, 'u3189': {'p1328'}, 'u3111': {'p345'}, 'u2432': {'p259', 'p287'}, 'u2100': {'p218', 'p828'}, 'u2285': {'p218'}, 'u1812': {'p239'}, 'u2392': {'p237'}, 'u2775': {'p289'}, 'u2393': {'p230', 'p285'}, 'u3289': {'p313'}}

    bipartiteG = BipartiteGraph.from_dict(new_up)
    origBipartiteG = BipartiteGraph.from_dict(up)
    # bipartiteG = add_adj_info_back(bipartiteG, up, pu, em)

    final_up = dict()
    for l in bipartiteG.L:
        if l not in final_up:
            final_up[l.label] = {r.label for r in l.neighbours}
        else:
            final_up[l.label] = final_up[l.label].union({r.label for r in l.neighbours})

    L = bipartiteG.L
    R = set()
    P = list(bipartiteG.R)
    Q = set()
    bicliques = []
    origBicliques = []

    mbea(G=bipartiteG, L=bipartiteG.L, R=set(), P=list(bipartiteG.R), Q=set(), bicliques=bicliques, em=em, imbea=True)
    mbea(G=origBipartiteG, L=origBipartiteG.L, R=set(), P=list(origBipartiteG.R), Q=set(), bicliques=origBicliques, em=em,
         imbea=True)

    retBicliques = maximize_bicliques(bicliques, origBicliques)
    # retBicliques = origBicliques
    # retBicliques = bicliques


    end_time = datetime.now()
    print(f'Time taken to compute maximal bicliques: {timedelta(seconds=(end_time - start_time).total_seconds())}')
    num_bicliques = 0
    max_biclique = Biclique(set(), set())

    ret_bicliques = []
    # for bc in bicliques:
    for bc in retBicliques:
        if len(bc.L) + len(bc.R) > len(max_biclique.L) + len(max_biclique.R):
            max_biclique = bc
        # print_biclique(bc.L, bc.R)
        biclique = list()
        for l, r in list(product(bc.L, bc.R)):
            biclique.append((l.label, r.label))
        ret_bicliques.append(biclique)
        num_bicliques += 1
    print('# bicliques: ', num_bicliques)
    print(f'Max biclique size: {len(max_biclique.L), len(max_biclique.R)}')
    print(Style.RESET_ALL)
    return ret_bicliques, new_up, final_up


def main():
    parser = argparse.ArgumentParser(description="Read input graph file")
    parser.add_argument("input_file", type=str, help="Input graph file")

    args = parser.parse_args()

    # up = {
    #     1: {7, 8},
    #     2: {8, 9},
    #     3: {7, 8, 9},
    #     4: {7, 8, 9},
    #     5: {7, 8, 9},
    #     6: {7, 8, 9}
    # }
    start_time = datetime.now()
    upfilename = args.input_file

    bicliques, _ = find_bicliques(upfilename, run_remove_dominators=False)
    up, usermap, permmap = readup_and_usermap_permmap(upfilename)

    new_bicliques = set()
    for bc in bicliques:
        L = set()
        for l in bc.L:
            for u in usermap:
                if l.label == usermap[u]:
                    L.add(Vertex(u))
        R = set()
        for r in bc.R:
            for p in permmap:
                if r.label == permmap[p]:
                    R.add(Vertex(p))
        new_bicliques.add(Biclique(L, R))

    for bc in new_bicliques:
        print_biclique(bc.L, bc.R)
    # print('Bicliques ', new_bicliques)
    print('# bicliques ', len(bicliques))
    end_time = datetime.now()
    print(f'Time taken: {(end_time - start_time).total_seconds()} seconds')


if __name__ == "__main__":
    main()
