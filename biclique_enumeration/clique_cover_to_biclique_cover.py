import os
import subprocess
import sys
import time
from datetime import datetime
from pprint import pprint

import networkx as nx
from matplotlib import pyplot as plt

from minedgerolemining.findcliquesbp import getedgeset
from minedgerolemining.readup import uptopu
from minedgerolemining.removedominators import isneighbour

prefix_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(f'{prefix_dir}')
sys.path.append(f'{prefix_dir}/MBEA')
sys.path.append(f'{prefix_dir}/../..')
print(sys.path)

from Biclique import Biclique
from MBEA import find_bicliques
from readup import dumpup, readup_and_usermap_permmap


def induces_biclique(ul, ur, vl, vr, B):
    if ul in B and vl in B:
        # get neighbours of ul intersect neighbours of vl
        common_neighbours = B[ul].intersection(B[vl])
        if len(common_neighbours) > 0:
            return ur in common_neighbours and vr in common_neighbours
    return False


def check_adjacency(B: dict, G: dict, edgemap: dict):
    # for an edge (u, v) in G, biclique must be induced
    for u, V in G.items():
        u_str = str(u).replace("'", "")
        for v in V:
            v_str = str(v).replace("'", "")
            ul, ur = edgemap[u_str]
            vl, vr = edgemap[v_str]
            if ul in B and vl in B:
                # if (ul, ur) does not induce a biclique with (vl, vr), return False
                # if not (ur in B[ul] and vr in B[vl]) and (vr in B[ul] and ur in B[vl]):
                if not induces_biclique(ul, ur, vl, vr, B):
                    return False

    # for not an edge (u, v) in G, no biclique must exist
    U = G.keys()
    V = {v for u in G for v in G[u]}
    for u in U:
        u_str = str(u).replace("'", "")
        for v in V:
            v_str = str(v).replace("'", "")
            if v in G[u] or u == v:
                continue
            ul, ur = edgemap[u_str]
            vl, vr = edgemap[v_str]
            if ul in B and vl in B:
                # if (ul, ur) induces a biclique with (vl, vr), return False
                # if (ur in B[ul] and vr in B[vl]) and (vr in B[ul] or ur in B[vl]):
                if induces_biclique(ul, ur, vl, vr, B):
                    return False
    return True


def to_bipartite_graph(G: dict, merge_vertices: bool = True):
    L = '_L'
    R = '_R'
    # for every vertex in the directed graph, create an edge in the bipartite graph
    B = dict()
    edgemap = dict()
    for v in G:
        v_str = str(v).replace("'", "")
        vl = v_str + L
        vr = v_str + R
        if vl not in B:
            B[vl] = {vr}
        else:
            B[vl].add(vr)

    for u in G:
        u_str = str(u).replace("'", "")
        ul = u_str + L
        ur = u_str + R
        edgemap[u_str] = (ul, ur)

        for v in G[u]:
            v_str = str(v).replace("'", "")
            vl = v_str + L
            vr = v_str + R
            B[ul].add(vr)
            B[vl].add(ur)

    if not merge_vertices:
        return B, edgemap
    already_compared = set()
    # for every edge (u, v) in the undirected graph, check if
    for (u, V) in G.items():
        u_str = str(u).replace("'", "")
        for v in V:
            v_str = str(v).replace("'", "")
            # if (u, v) in already_compared:
            #     continue
            already_compared.add((u, v))
            already_compared.add((v, u))

            ul = edgemap[u_str][0]
            ur = edgemap[u_str][1]
            vl = edgemap[v_str][0]
            vr = edgemap[v_str][1]

            if ul not in B or vl not in B or (ul == vl or ur == vr):
                continue

            if ul.startswith(u_str) ^ ur.startswith(u_str) and vl.startswith(v_str) ^ vr.startswith(v_str):
                continue
            B_prime = B.copy()
            edgemap_curr = edgemap.copy()

            # combine ul and vl and check if we violate notion of adjacency
            B_prime[ul] = B_prime[ul].union(B_prime[vl])
            for x in edgemap_curr:
                if vl in edgemap[x]:
                    edgemap_curr[x] = (ul, edgemap[x][1])
            if vl in B_prime:
                B_prime.pop(vl)
            check = check_adjacency(B_prime, G, edgemap_curr)
            if not check:
                edgemap_curr = edgemap.copy()

                B_prime = B.copy()
                # combine ur and vr and check if we violate notion of adjacency
                # remove one of ur and vr. Let's remove vr
                for x in B_prime:
                    if vr in B_prime[x] and ur != vr:
                        B_prime[x] = B_prime[x].union({ur})
                        # B_prime_x_array = np.array(list(B_prime[x]))
                        # vr_array = np.array([vr])
                        # B_prime[x] = set(np.setdiff1d(B_prime_x_array, vr_array))
                        B_prime[x] = B_prime[x].difference({vr})

                # update edgemap
                # edgemap_curr[v_str] = (vl, ur)
                for x in edgemap_curr:
                    if vr in edgemap[x]:
                        edgemap_curr[x] = (edgemap[x][0], vr)
                check = check_adjacency(B_prime, G, edgemap_curr)
                if check:
                    B = B_prime
                    edgemap = edgemap_curr
            else:
                B = B_prime
                edgemap = edgemap_curr
    return B, edgemap


def check_if_induces_biclique(G: dict, edgemap: dict, B: dict):
    V = set(G.keys())
    check = True
    for x in V:
        x_str = str(x).replace("'", "")
        Nx = set(G[x]).difference({x})
        for nx in Nx:
            nx_str = str(nx).replace("'", "")

            if x_str in edgemap and nx_str in edgemap:
                xl, xr = edgemap[x_str]
                nxl, nxr = edgemap[nx_str]
                check &= induces_biclique(xl, xr, nxl, nxr, B)
    return check


def check_if_does_not_induce_biclique(G: dict, edgemap: dict, B: dict):
    V = set(G.keys())
    check = True
    for x in V:
        x_str = str(x).replace("'", "")
        nonNx = V.difference(G[x]).difference({x})
        for non_nx in nonNx:
            non_nx_str = str(non_nx).replace("'", "")

            if x_str in edgemap and non_nx_str in edgemap:
                xl, xr = edgemap[x_str]
                non_nxl, non_nxr = edgemap[non_nx_str]
                check &= not induces_biclique(xl, xr, non_nxl, non_nxr, B)
    return check


def add_to_B(Bdict, k, val):
    if k not in Bdict:
        Bdict[k] = set()
    Bdict[k].add(val)


def to_bipartite_graph_merge_seq(G: dict):
    L = '_L'
    R = '_R'
    B = dict()
    edgemap = dict()

    u_ctr = 0
    start_time = time.time()
    for u in G:
        u_ctr += 1
        if u_ctr % 10 == 0:
            end_time = time.time()
            print('time taken so far: ', end_time - start_time)
            print(u_ctr)
        new_slack_edges = set()
        u_str = str(u).replace("'", "")
        ul = u_str + L
        ur = u_str + R

        Nu = set(G[u]).difference({u})
        nonNu = set(G.keys()).difference(Nu).difference({u})

        # check if any neighbour exists in edgemap
        neighbour_found = False
        for n in Nu:
            n_str = str(n).replace("'", "")
            if n_str in edgemap:
                neighbour_found = True
                break

        # if no neighbour_found, then create ul, ur and add an edge between them, update edgemap
        if not neighbour_found:
            # ul --- ur
            add_to_B(B, ul, ur)
            edgemap[u_str] = (ul, ur)
        else:
            u_found_a_good_neighbour = False

            sortedNu = sorted(Nu, key=lambda x: len(G[x]))

            for n in Nu:
                n_str = str(n).replace("'", "")
                if n_str in edgemap:
                    nl, nr = edgemap[n_str]
                    # add edge between nl, ur
                    add_to_B(B, nl, ur)
                    edgemap[u_str] = (nl, ur)

                    # update ul, ur based on what appears in edgemap
                    ul, ur = edgemap[u_str]

                    # add slack edges between all neighbours of u
                    Nu_minus_n = Nu.difference({n})
                    for w in Nu_minus_n:
                        w_str = str(w).replace("'", "")
                        if w_str in edgemap:
                            wl, wr = edgemap[w_str]
                            # add slack edges (wl, ur), (ul, wr) to create a biclique

                            if ul not in B or wr not in B[ul]:
                                new_slack_edges.add((ul, wr))
                                add_to_B(B, ul, wr)

                            if wl not in B or ur not in B[wl]:
                                new_slack_edges.add((wl, ur))
                                add_to_B(B, wl, ur)

                    # check if all neighbours in G induce a biclique in B
                    neighbours_biclique_check = check_if_induces_biclique(G, edgemap, B)

                    # check if all non-neighbours in G do not induce a biclique in B
                    non_neighbours_biclique_check = check_if_does_not_induce_biclique(G, edgemap, B)

                    if not neighbours_biclique_check or not non_neighbours_biclique_check:
                        # print('Check failed')
                        # remove edge (nl, ur), remove u from edgemap
                        ul, ur = edgemap[u_str]
                        B[ul].remove(ur)

                        main_edges = {edgemap[e] for e in edgemap}

                        # remove slack edges (wl, ur), (ul, wr)
                        for w in Nu_minus_n:
                            w_str = str(w).replace("'", "")
                            if w_str in edgemap:
                                wl, wr = edgemap[w_str]
                                if ul in B and wr in B[ul]:
                                    if (ul, wr) not in main_edges and (ul, wr) in new_slack_edges:
                                        B[ul].remove(wr)
                                if wl in B and ur in B[wl]:
                                    if (wl, ur) not in main_edges and (wl, ur) in new_slack_edges:
                                        B[wl].remove(ur)

                        # remove u from edgemap
                        if u_str in edgemap:
                            edgemap.pop(u_str)
                        # try next neighbour
                    else:
                        # u found a good neighbour that satisfies all constraints, move to next u
                        u_found_a_good_neighbour = True
                        break
            # if no good neighbour found for u, then create a new ul, ur and edge between them and slack edges
            # between its neighbours
            if not u_found_a_good_neighbour:
                ul = u_str + L
                ur = u_str + R
                add_to_B(B, ul, ur)
                # update edgemap
                edgemap[u_str] = (ul, ur)

                # add slack edges between u and neighbours of u
                for w in Nu:
                    w_str = str(w).replace("'", "")
                    if w_str in edgemap:
                        wl, wr = edgemap[w_str]
                        # ul --- wr
                        add_to_B(B, ul, wr)
                        # wl --- ur
                        add_to_B(B, wl, ur)
    return B, edgemap


def biclique_as_edges(biclique: Biclique):
    return {(l.label, r.label) for l in biclique.L for r in biclique.R}


def remove_slack_edges(B: dict, edgemap: dict):
    B_prime = dict()
    for e in edgemap:
        e_val = edgemap[e]
        l = e_val[0]
        r = e_val[1]
        if l not in B_prime:
            B_prime[l] = {r}
        else:
            B_prime[l].add(r)
    return B_prime

    # pass


def filter_bicliques(bicliques: list, edgemap: dict, usermap: dict, permmap: dict):
    new_edgemap = dict()
    for e in edgemap:
        new_edgemap[e] = (usermap[edgemap[e][0]], permmap[edgemap[e][1]])
    orig_edges = {new_edgemap[e] for e in new_edgemap}
    # orig_edges = {e for e in edgemap}

    bicliques_to_consider = list()
    for bc in bicliques:
        num_edges_from_edgemap = 0
        edges_in_bc = biclique_as_edges(bc)
        for e in edges_in_bc:
            if e in orig_edges:
                num_edges_from_edgemap += 1
        if num_edges_from_edgemap > 1:
            bicliques_to_consider.append(bc)

    edges_covered_by_bicliques = dict()
    for bc in bicliques_to_consider:
        edges_in_bc = set()
        bcL = {v.label for v in bc.L}
        bcR = {v.label for v in bc.R}
        for e in new_edgemap:
            if new_edgemap[e][0] in bcL and new_edgemap[e][1] in bcR:
                edges_in_bc.add(new_edgemap[e])
        if len(edges_in_bc) > 0:
            edges_covered_by_bicliques[tuple(edges_in_bc)] = bc

    edges_to_remove = set()
    for e in edges_covered_by_bicliques:
        for f in edges_covered_by_bicliques:
            if set(e).issubset(set(f)) and e != f:
                edges_to_remove.add(e)
    for e in edges_to_remove:
        edges_covered_by_bicliques.pop(e)
    final_bicliques = [e for e in edges_covered_by_bicliques]

    def get_u(x):
        for u in usermap:
            if usermap[u] == x:
                return u

    def get_p(x):
        for p in permmap:
            if permmap[p] == x:
                return p

    final_bicliques = {tuple((get_u(e[0]), get_p(e[1])) for e in bc) for bc in final_bicliques}

    return final_bicliques
    # return bicliques


# def verify(B: dict, G: dict, edgemap: dict):
#     # CLIQUES
#     GG = nx.Graph(G)
#     cliques = list(nx.find_cliques(GG))
#     print(f'# cliques in G: {len(cliques)}')
#     print('Cliques: ', cliques)
#
#     # BICLIQUES
#     dumpup(B, 'bipartite_graph_domino_before.txt', include_prefixes=False)
#     ret_bicliques, final_up = find_bicliques('bipartite_graph_domino_before.txt', False)
#     print(ret_bicliques)
#     up, usermap, permmap = readup_and_usermap_permmap('bipartite_graph_domino_before.txt')
#     start_time = datetime.now()
#     # final_bicliques = filter_bicliques(ret_bicliques, edgemap, usermap, permmap)
#     final_bicliques = ret_bicliques
#     end_time = datetime.now()
#     print(f'Time taken to filter bicliques: {end_time - start_time}')
#
#     print(Fore.RED)
#
#     bicliques_as_edges = list()
#     for bc in final_bicliques:
#         bicliques_as_edges.append([(l.label, r.label) for l in bc.L for r in bc.R])
#
#     final_bicliques = bicliques_as_edges
#
#     def get_u(x):
#         for u in usermap:
#             if usermap[u] == x:
#                 return u
#
#     def get_p(x):
#         for p in permmap:
#             if permmap[p] == x:
#                 return p
#
#     final_bicliques = {tuple((get_u(e[0]), get_p(e[1])) for e in bc) for bc in final_bicliques}
#
#     def get_vertex_from_edgemap(x):
#         for e in edgemap:
#             if edgemap[e] == x:
#                 # remove ( and ) from the string, then remove whitespace
#                 e = e.strip('(').strip(')').split(',')
#                 if len(e) == 2:
#                     e = (e[0].strip(), e[1].strip())
#                 else:
#                     e = e[0].strip()
#                 return e
#
#     # final_bicliques = [list(get_vertex_from_edgemap(v) for v in bc) for bc in final_bicliques]
#
#     # for bc in final_bicliques:
#     #     # left = list({u for e in bc for u in usermap if usermap[u] == e[0]})
#     #     left = list({u for e in bc.L for u in usermap if usermap[u] == e.label})
#     #     # right = list({p for e in bc for p in permmap if permmap[p] == e[1]})
#     #     right = list({p for e in bc.R for p in permmap if permmap[p] == e.label})
#     #     # right = {v.label for v in bc.R}
#     #     print(left, ':', right)
#     #
#     # print(f'# bicliques in B: {len(final_bicliques)}')
#
#     print(Style.RESET_ALL)


def get_bipartite_graph_and_bicliques(G: dict):
    # A, edgemap = to_bipartite_graph(G, merge_vertices=True)
    A, edgemap = to_bipartite_graph_merge_seq(G)
    # B = remove_slack_edges(A, edgemap)
    B = A
    # BICLIQUES
    dumpup(B, 'bipartite_graph_domino_before.txt', include_prefixes=False)
    ret_bicliques, up = find_bicliques('bipartite_graph_domino_before.txt', run_remove_dominators=False)
    up, usermap, permmap = readup_and_usermap_permmap('bipartite_graph_domino_before.txt')
    final_bicliques = filter_bicliques(ret_bicliques, edgemap, usermap, permmap)

    def get_vertex_from_edgemap(x):
        for e in edgemap:
            if edgemap[e] == x:
                # remove ( and ) from the string, then remove whitespace
                e = e.strip('(').strip(')').split(',')
                e = (e[0].strip(), e[1].strip())
                return e

    final_bicliques = [list(get_vertex_from_edgemap(v) for v in bc) for bc in final_bicliques]

    return B, final_bicliques


def get_bipartite_graph_and_bicliques_parallel(G: dict):
    # A, edgemap = to_bipartite_graph(G, merge_vertices=True)
    start_time = time.time()
    A, edgemap = to_bipartite_graph_merge_seq(G)
    end_time = time.time()
    print('Time taken to reduce clique -> bipartite graph:', end_time - start_time)
    # B = remove_slack_edges(A, edgemap)
    B = A
    # BICLIQUES
    plot_B(B, edgemap)
    dumpup(B, 'bipartite_graph.txt', include_prefixes=False)

    up, usermap, permmap = readup_and_usermap_permmap('bipartite_graph.txt')
    linearize_up(up, 'linearized_bipartite_graph.txt')

    # ret_bicliques, up = find_bicliques('bipartite_graph_domino_before.txt', run_remove_dominators=False)
    # up, usermap, permmap = readup_and_usermap_permmap('bipartite_graph_domino_before.txt')
    # final_bicliques = filter_bicliques(ret_bicliques, edgemap, usermap, permmap)

    def get_vertex_from_edgemap(x):
        for e in edgemap:
            if edgemap[e] == x:
                # remove ( and ) from the string, then remove whitespace
                e = e.strip('(').strip(')').split(',')
                e = (e[0].strip(), e[1].strip())
                return e

    # final_bicliques = [list(get_vertex_from_edgemap(v) for v in bc) for bc in final_bicliques]

    result = subprocess.run(["./biclique_enumeration/parmbe", "linearized_bipartite_graph.txt"], capture_output=True,
                            text=True)
    print('Parallel MBE')
    print(result.stdout)

    return B


def create_bipartite_graph(G: dict):
    B = dict()
    # For every vertex v in G, create 2 new vertices (v_L, v_R) in B and add an edge between them.
    for v in G:
        v_str = str(v).replace("'", "")
        vL = v_str + '_L'
        vR = v_str + '_R'
        B[vL] = {vR}

    edgemap = dict()

    # For every edge (u, v) in G, create two new vertices (u, v)_L and (u, v)_R. Also add an edge between them.
    for u in G:
        u_str = str(u).replace("'", "")
        for v in G[u]:
            v_str = str(v).replace("'", "")
            if (u, v) not in edgemap:
                e_L = f'({u_str} {v_str})_L'
                e_R = f'({u_str} {v_str})_R'
                B[e_L] = {e_R}
                edgemap[(u, v)] = (e_L, e_R)
                edgemap[(v, u)] = (e_L, e_R)

    # Add adjacency information:
    # 1) Add an edge between vertex u and all edges of the form (u, v) or (v, u)

    for u in G:
        u_str = str(u).replace("'", "")
        uL = u_str + '_L'
        for v in G[u]:
            uvR = edgemap[(u, v)][1]
            # add an edge
            B[uL].add(uvR)

    # for u in G:
    #     u_str = str(u).replace("'", "")
    #     uL = u_str + '_L'
    #     for e in edgemap:
    #         # add an edge
    #         e_set = set(e)
    #         neighbours_u = G[u]
    #         if e_set.issubset(neighbours_u):
    #             # add an edge
    #             uvR = edgemap[e][1]
    #             B[uL].add(uvR)

    return B


def linearize_up(up, linearized_upfilename):
    s = ''
    for u in up:
        for p in up[u]:
            s += u + ' ' + p + '\n'

    # for p in pu:
    #     for u in pu[p]:
    #         s += p + ' ' + u + '\n'

    with open(linearized_upfilename, "w") as f:
        f.write(s)


def plot_B(B: dict, edgemap: dict):
    main_edges = {edgemap[e] for e in edgemap}
    GG = nx.Graph()

    top_nodes = list({v for v in B})
    bottom_nodes = list({v for u in B for v in B[u]})
    top_nodes.sort()
    bottom_nodes.sort()
    edges = {(u, v) for u in B for v in B[u]}

    GG.add_nodes_from(top_nodes, bipartite=0)
    GG.add_nodes_from(bottom_nodes, bipartite=1)
    for (u, v) in edges:
        if (u, v) in main_edges:
            GG.add_edge(u, v, color='black')
        else:
            GG.add_edge(u, v, color='red')

    edge_colors = [GG[u][v]['color'] for u, v in GG.edges()]

    pos = nx.bipartite_layout(GG, top_nodes)  # Layout separates the two sets
    nx.draw(GG, pos, with_labels=True, edge_color=edge_colors, node_color=['lightgray'], node_size=100)
    plt.show()


'''
Description: Convert bipartite graph B after dominator edges are removed, to bipartite graph C, which has the 
adjacency information.

Input:  B: bipartite graph
        em: dominator edges 
Output: C: bipartite graph + adjacency 


For every vertex in B, introduce a vertex in C
For every edge in B, introduce an edge in C
For every pair of edges <e,f> in B, if e if adjacent to f in B (while incorporating em):
    - Check if e is already adjacent to f in C. If yes, do nothing.
    - If not, create new vertices/edges as needed to make e adjacent to f in C
'''


def B_to_C(B: dict, em: dict):
    edgeset = getedgeset(em, B)
    C = dict()

    for e in edgeset:
        u = e[0]
        p = e[1]
        if u in C:
            C[u].add(p)
        else:
            C[u] = {p}

    for e in edgeset:
        for f in edgeset:
            if e == f: continue
            if isneighbour(e, f, B):
                if isneighbour(e, f, C): continue

                # add slack edges
                C[e[0]].add(f[1])
                C[f[0]].add(e[1])

    dumpup(C, 'bipartite_graph_C.txt', include_prefixes=False)
    linearize_up(C, 'linearized_bipartite_graph_C.txt')

    result = subprocess.run(["./biclique_enumeration/parmbe", "linearized_bipartite_graph_C.txt"],
                            capture_output=True, text=True)

    print('B_to_C')
    print(result.stdout)
    return C

    # all_edges =


def main():
    # undirected graph
    # G = {
    #     '1': {'2', '3', '4'},
    #     '2': {'1', '3'},
    #     '3': {'1', '2', '4'},
    #     '4': {'1', '3'}
    # }

    # GG = nx.erdos_renyi_graph(n=20, p=0.5)
    # G = nx.to_dict_of_lists(GG)
    # nx.draw(GG, with_labels=True)
    # plt.show()
    #
    G = {
        0: [1, 2, 3, 4],
        1: [0, 2, 4],
        2: [0, 1, 4],
        3: [0, 4],
        4: [0, 1, 2],
        5: [3, 4],
        6: [2, 3, 4, 5]
    }

    # G = {0: [5, 6, 10, 13, 15, 16, 17, 18],
    #  1: [3, 4, 5, 8, 9, 10, 11, 12, 19],
    #  2: [5, 7, 8, 9, 14, 15, 17, 18, 19],
    #  3: [1, 5, 7, 8, 9, 11, 12, 14, 15, 16, 18],
    #  4: [1, 5, 7, 11, 12, 14, 15, 17, 18],
    #  5: [0, 1, 2, 3, 4, 7, 8, 9, 11, 12, 13, 14, 15, 16, 18, 19],
    #  6: [0, 10, 12, 14, 15, 16, 19],
    #  7: [2, 3, 4, 5, 9, 11, 12, 13, 14, 19],
    #  8: [1, 2, 3, 5, 9, 10, 12, 14, 16, 17],
    #  9: [1, 2, 3, 5, 7, 8, 13, 15, 19],
    #  10: [0, 1, 6, 8, 12, 14, 15, 16],
    #  11: [1, 3, 4, 5, 7, 14, 15, 17, 18],
    #  12: [1, 3, 4, 5, 6, 7, 8, 10, 13, 17, 18, 19],
    #  13: [0, 5, 7, 9, 12, 17],
    #  14: [2, 3, 4, 5, 6, 7, 8, 10, 11, 15, 18, 19],
    #  15: [0, 2, 3, 4, 5, 6, 9, 10, 11, 14],
    #  16: [0, 3, 5, 6, 8, 10],
    #  17: [0, 2, 4, 8, 11, 12, 13, 18, 19],
    #  18: [0, 2, 3, 4, 5, 11, 12, 14, 17],
    #  19: [1, 2, 5, 6, 7, 9, 12, 14, 17]}

    G = {
        0: [1],
        1: [0, 2, 3],
        2: [1, 3],
        3: [1, 2],
        4: [2, 3]
    }

    G = {
        0: [1, 3, 4],
        1: [0, 3],
        2: [3, 4],
        3: [0, 1, 2],
        4: [0, 2]
    }

    G = {
        0: [1, 2, 3, 4, 5],
        1: [0, 3, 4, 5],
        2: [0, 4],
        3: [0, 1, 5],
        4: [0, 1, 2],
        5: [0, 1, 3]
    }

    G = {
        0: [1, 2, 3, 4, 5],
        1: [0, 4],
        2: [0, 3],
        3: [0, 2, 4],
        4: [0, 1, 5],
        5: [0, 4]
    }

    G = {
        0: [3, 4],
        1: [2, 3],
        2: [1, 4],
        3: [0, 1, 4],
        4: [0, 2, 3]
    }

    G = {
        0: [1, 2, 4],
        1: [0, 4],
        2: [0, 4],
        4: [0, 1, 2]
    }

    # GG = nx.erdos_renyi_graph(n=10, p=0.7)
    # G = nx.to_dict_of_lists(GG)
    GG = nx.Graph(G)
    nx.draw(GG, with_labels=True, node_color=['lightgray'], node_size=500)
    plt.show()
    pprint(G)

    start_time = datetime.now()
    B, edgemap = to_bipartite_graph(G, merge_vertices=True)
    num_edges = 0
    for b in B:
        num_edges += len(B[b])
    print(f'# main edges: {len(edgemap.keys())}, # slack edges: {num_edges - len(edgemap.keys())}')
    plot_B(B, edgemap)
    B, edgemap = to_bipartite_graph_merge_seq(G)
    num_edges = 0
    for b in B:
        num_edges += len(B[b])
    print(f'# main edges: {len(edgemap.keys())}, # slack edges: {num_edges - len(edgemap.keys())}')

    plot_B(B, edgemap)

    end_time = datetime.now()
    print(f'Time taken to compute bipartite graph: {end_time - start_time}')

    dumpup(B, 'bipartite_graph_domino_before.txt', include_prefixes=False)

    up, usermap, permmap = readup_and_usermap_permmap('bipartite_graph_domino_before.txt')
    pu = uptopu(up)
    linearize_up(up, 'linearized_bipartite_graph.txt')

    start_time = time.time()
    ret_bicliques, up = find_bicliques('bipartite_graph_domino_before.txt', False)
    end_time = time.time()
    print(f'iMBEA (python) Elapsed time: {end_time - start_time} seconds')
    for bc in ret_bicliques:
        left = list({u for l in bc.L for u in usermap if usermap[u] == l.label})
        right = list({p for r in bc.R for p in permmap if permmap[p] == r.label})
        print(left, ':', right)
    #
    print(f'# bicliques in B: {len(ret_bicliques)}')

    result = subprocess.run(["./parmbe", "linearized_bipartite_graph.txt"], capture_output=True, text=True)
    print(result.stdout)


if __name__ == '__main__':
    main()
