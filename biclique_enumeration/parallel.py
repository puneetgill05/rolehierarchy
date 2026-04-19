import argparse
import concurrent
import math
import os
import sys
from concurrent.futures import ThreadPoolExecutor, wait
from datetime import datetime
from multiprocessing import Process
from typing import Set

import numpy as np
from numba import cuda

prefix_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(f'{prefix_dir}')
sys.path.append(f'{prefix_dir}/MBEA')
sys.path.append(f'{prefix_dir}/MBEA/Utils')
sys.path.append(f'{prefix_dir}/../..')
print(sys.path)

from Biclique import Biclique
from BipartiteGraph import BipartiteGraph
from Vertex import Vertex
from NetworkxBicliqueEnum import update_up
from readup import readup, uptopu
from removedominatorsbp import get_em


@cuda.jit
def compute_degrees(edge_list, degree_array):
    idx = cuda.grid(1)
    if idx < edge_list.shape[0]:
        u = edge_list[idx, 0]
        v = edge_list[idx, 1]
        cuda.atomic.add(degree_array, u, 1)
        cuda.atomic.add(degree_array, v, 1)


def generate_dense_graph(num_nodes, edge_prob=0.8, seed=42):
    np.random.seed(seed)
    # Generate upper triangle (excluding diagonal)
    upper = np.triu(np.random.rand(num_nodes, num_nodes) < edge_prob, k=1)
    adj_matrix = upper + upper.T  # make symmetric (undirected)

    # Extract edge list
    edge_list = np.column_stack(np.where(adj_matrix))
    return edge_list.astype(np.int32)


# Example usage
# num_nodes = 10000  # Large graph
# edges = generate_dense_graph(num_nodes)
#
# num_edges = edges.shape[0]
#
# # Copy data to device
# d_edges = cuda.to_device(edges)
# d_degrees = cuda.to_device(np.zeros(num_nodes, dtype=np.int32))
#
#
# # Launch kernel
# threads_per_block = 64
# blocks = (num_edges + threads_per_block - 1) // threads_per_block
# compute_degrees[blocks, threads_per_block](d_edges, d_degrees)
#
# # Copy result back
# degrees = d_degrees.copy_to_host()
# print("Node degrees:", degrees)


#
# from multiprocessing import Pool
#
# def task(i):
#     return i * i
#
# with Pool(processes=4) as pool:
#     results = pool.map(task, range(10))
#
# print("Results:", results)

# def tail(X: set[Vertex]):
#     for x in X:


def gamma(v: Vertex):
    return v.neighbours


def gamma_set(X: Set[Vertex]):
    LX = list(X)
    if len(LX) == 0:
        return set()
    ret = LX[0].neighbours
    for v in LX:
        ret = ret.intersection(v.neighbours)
    return ret


def sort_vertices(X: dict):
    return dict(sorted(X.items(), key=lambda item: item[1]))


def rank(v: Vertex):
    return len(v.neighbours)


def seqMBC(X: set[Vertex], gammaX: set[Vertex], tailX: set[Vertex], ms: int, B: set[Biclique]):
    M = dict()

    # if len(X) == 1 and ms == 1:
    #     Y = pivot_vertex.neighbours
    #     for v in gammaX:
    #         tmp = Y.intersection(v.neighbours)
    #         Y = tmp
    #         if len(Y) == 0:
    #             break
    #     if len(X) == len(Y):
    #         print(X, Y)
    #         return

    # Lines 1-3
    # set of vertices where the number of "common" neighbours < ms
    removed_v = set()
    for v in tailX:
        # all "common" neighbours of X and v
        intersect = gammaX.intersection(v.neighbours)
        intersect_size = len(intersect)
        if intersect_size < ms:
            removed_v.add(v)

    # remove all vertices in removed_v
    tailX = tailX.difference(removed_v)

    # Lines 4-5
    if len(X) + len(tailX) < ms:
        return

    # Lines 6
    # sort vertices of tailX into ascending order of neighbours(X + v)
    tailX_dict = dict()
    for v in tailX:
        tailX_dict[v] = len(gammaX.intersection(v.neighbours))
    sorted_tailX = sort_vertices(tailX_dict)

    # Lines 7-14
    removed_v = set()
    for v in sorted_tailX:
        removed_v.add(v)
        tailX = set(sorted_tailX.keys()).difference(removed_v)
        if len(X.union({v})) + len(tailX) > ms:
            Y = gamma_set(gamma_set(X.union({v})))
            # Y.difference(X.union({v}))
            if Y.difference(X.union({v})).issubset(tailX):
                if len(Y) >= ms:
                    bc = Biclique(Y, gammaX.intersection(v.neighbours))
                    B.add(bc)
                seqMBC(Y, gamma_set(X.union({v})), tailX.difference(Y), ms, B)


def seqMBE(G: BipartiteGraph, ms: int):
    bicliques = set()
    for v in G.L:
        X = {v}
        gammaX = gamma(v)
        tailX = set()
        for w in gamma(v):
            for y in gamma(w):
                if rank(y) > rank(v) or (rank(y) == rank(v) and y.label > v.label):
                    tailX = tailX.union({y})
        seqMBC(X, gammaX, tailX, ms, B=bicliques)
    # print('Bicliques:')
    # print_bicliques = lambda x: [print(b) for b in x]
    # print_bicliques(bicliques)
    print('# Bicliques: ', len(bicliques))


def run_gamma_w(v: Vertex, y: Vertex, tailX: set[Vertex]):
    if rank(y) > rank(v) or (rank(y) == rank(v) and y.label > v.label):
        tailX = tailX.union({y})
    return tailX


def run_gamma_v(v: Vertex, w: Vertex, tailX: set[Vertex]):
    # with ProcessPoolExecutor(max_workers=4) as executor:
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(run_gamma_w, v, y, tailX) for y in gamma(w)]
        results = [f.result() for f in futures]
        for r in results:
            tailX = tailX.union(r)
    return tailX


def runMBE(args: tuple):
    v_dict = args[0]
    ms = args[1]
    bicliques = args[2]
    v = Vertex.from_dict(v_dict)
    X = {v}
    gammaX = gamma(v)

    # with ProcessPoolExecutor(max_workers=4) as executor:
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(run_gamma_v, v, w, tailX=set()) for w in gamma(v)]
        tailXs = [f.result() for f in futures]
        seqMBC(X, gammaX, tailX=tailXs[-1], ms=ms, B=bicliques)
    return bicliques


def parMBE(G: BipartiteGraph, ms: int):
    with concurrent.futures.ProcessPoolExecutor() as executor:
        # with ThreadPoolExecutor(max_workers=2) as executor:
        # futures = [executor.submit(runMBE, v, 1, set()) for v in G.L]
        # results = [f.result() for f in futures]
        params = [(v.to_dict(), 1, set()) for v in G.L]
        results = list(executor.map(runMBE, params))
        num_bicliques = 0
        for bicliques in results:
            if len(bicliques) == 0:
                continue
            num_bicliques += len(bicliques)

        print('# Bicliques: ', num_bicliques)

    # print('Bicliques:')
    # print_bicliques = lambda x: [print(b) for b in x]
    # print_bicliques(bicliques)
    # print('# Bicliques: ', len(bicliques))


def main():
    parser = argparse.ArgumentParser(description="Read input graph file")
    parser.add_argument("input_file", type=str, help="Input graph file")

    args = parser.parse_args()

    start_time = datetime.now()
    upfilename = args.input_file
    up = readup(upfilename)
    pu = uptopu(up)
    em = get_em(upfilename)
    new_up = update_up(up, em)

    bipartiteG = BipartiteGraph.from_dict(new_up)
    # print(bipartiteG)
    # seqMBE(bipartiteG, ms=1)
    parMBE(bipartiteG, ms=1)

    end_time = datetime.now()
    print(f'Time taken: {end_time - start_time}')


if __name__ == '__main__':
    main()
