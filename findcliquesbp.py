#! /usr/bin/python3
import os
import time
import datetime
import sys


from collections import Counter

sys.path.append('/home/puneet/Projects/minedgerolemining/minedgerolemining')
from readup import readup, uptopu
from removedominatorsbp import removedominators, hasbeenremoved, neighbours, saveem, readem


def getedgeset(em, up):
    # set of all edges
    edgeset = set()
    for u in up:
        for p in up[u]:
            e = tuple((u, p))
            if len(edgeset) % 10000 == 0:
                # print(f'Added edges: {len(edgeset)}')
                pass
            if hasbeenremoved(e, em):
                continue
            edgeset.add(e)
    return edgeset


def add_edge_to_up(g, new_up):
    if g[0] not in new_up:
        new_up[g[0]] = {g[1]}
    else:
        new_up[g[0]].add(g[1])


def find_bicliquesbp(em, up, pu, nodes):
    #Adapted from networkx.find_cliques
    #Presumably dominators and zero-neighbour vertices have been
    #removed. But that's not a necessary condition

    if len(up) == 0:
        return

    edgeset = getedgeset(em, up)

    adj = {u: {v for v in neighbours(u, em, up, pu) if v != u} for u in edgeset}

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


def find_bicliquesbp2(em, up, pu, nodes):
    if len(up) == 0:
        return

    edgeset = getedgeset(em, up)
    cliques = []

    adj = {u: {v for v in neighbours(u, em, up, pu) if v != u} for u in edgeset}

    # Initialize Q with the given nodes and subg, cand with their nbrs
    Q = nodes[:] if nodes is not None else []
    cand = edgeset
    for node in Q:
        if node not in cand:
            raise ValueError(f"The given `nodes` {nodes} do not form a clique")
        cand &= adj[node]

    # if not cand:
    #     yield Q[:]
    #     return

    subg = cand.copy()
    stack = []
    Q.append(None)

    u = max(subg, key=lambda u: len(cand & adj[u]))
    ext_u = cand - adj[u]

    calls = 0
    # try:
    while True:
        calls += 1
        if ext_u:
            q = ext_u.pop()
            cand.remove(q)
            Q[-1] = q
            adj_q = adj[q]
            t1 = time.time()
            subg_q = subg & adj_q
            t2 = time.time()
            # print('Elapsed time for set intersection: {}'.format(t2-t1))
            if not subg_q:
                # print('Q: ', Q)
                # yield Q[:]
                cliques.append(Q[:])
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
            if len(stack) == 0:
                return cliques
            subg, cand, ext_u = stack.pop()
    # except IndexError:
    #     pass
    print('# calls: ', calls)


def getPivot(cand: set, cand_union_fini: set, adj: dict):
    return max(cand_union_fini, key=lambda u: len(cand & adj[u]))


def TTT_loop2(em, up, pu):
    num_cliques = 0
    calls = 0
    stack = []
    K = []
    cand = set()
    fini = set()

    if len(up) == 0:
        return

    edgeset = getedgeset(em, up)
    adj = {u: {v for v in neighbours(u, em, up, pu) if v != u} for u in edgeset}

    cand = edgeset

    cand_union_fini = cand.union(fini)
    pivot = getPivot(cand, cand_union_fini, adj)
    pivot_neighbours = adj[pivot]
    ext = cand - pivot_neighbours

    stack.append((K[:], set(cand), set(fini), set(ext)))
    cliques_seen = []

    while True:
        if not stack:
            break

        if ext:
            calls += 1
            if calls % 100000 == 0:
                print(f"Number of calls: {calls}")

            q = next(iter(ext))
            ext.remove(q)

            if q in fini:
                continue

            K.append(q)
            cand.discard(q)
            fini.add(q)
            q_neighbours = adj[q]
            cand_q = cand & q_neighbours
            fini_q = fini & q_neighbours

            stack.append((K[:], set(cand), set(fini), set(ext)))

            cand = cand_q
            fini = fini_q
            if not cand:
                continue
            pivot = getPivot(cand, cand, adj)
            if pivot in adj:
                pivot_neighbours = adj[pivot]
            else:
                print(f"Pivot {pivot}")
            ext = cand - pivot_neighbours
        else:
            if not cand and not fini and K:
                if K not in cliques_seen:
                    cliques_seen.append(K[:])
                    num_cliques += 1
                    if num_cliques % 1000 == 0:
                        print(f"Number of maximal cliques so far: {num_cliques}")
                else:
                    print("clique already seen")

            while not ext or not cand:
                if not stack:
                    break
                K, cand, fini, ext = stack.pop()

                K = [v for v in K if v not in fini]
                ext = {v for v in ext if v not in fini}

    print(f"Number of maximal cliques: {num_cliques}")
    print(f"maximal cliques: {cliques_seen}")



def findcliquesBP_Par(up: dict, em: dict, pu: dict, nodes: list):

    if len(up) == 0:
        return

    edgeset = getedgeset(em, up)
    cliques = []

    adj = {u: {v for v in neighbours(u, em, up, pu) if v != u} for u in edgeset}

    # Initialize Q with the given nodes and subg, cand with their nbrs
    Q = nodes[:] if nodes is not None else []
    cand = edgeset
    for node in Q:
        if node not in cand:
            raise ValueError(f"The given `nodes` {nodes} do not form a clique")
        cand &= adj[node]


    subg = cand.copy()
    stack = []
    Q.append(None)

    u = max(subg, key=lambda u: len(cand & adj[u]))
    ext_u = cand - adj[u]

    calls = 0
    # try:
    while True:
        calls += 1
        if ext_u:
            q = ext_u.pop()
            cand.remove(q)
            Q[-1] = q
            adj_q = adj[q]
            t1 = time.time()
            subg_q = subg & adj_q
            t2 = time.time()
            # print('Elapsed time for set intersection: {}'.format(t2-t1))
            if not subg_q:
                # print('Q: ', Q)
                # yield Q[:]
                cliques.append(Q[:])
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
            if len(stack) == 0:
                return cliques
            subg, cand, ext_u = stack.pop()
    # except IndexError:
    #     pass
    print('# calls: ', calls)





def run(upfilename):
    up = readup(upfilename)
    if not up:
        return
    emfilename = upfilename +'-em.txt'
    pu = uptopu(up)

    if os.path.isfile(emfilename):
        em = readem(emfilename)
    else:
        print('Removing doms...', end='')
        sys.stdout.flush()

        timeone = time.time()
        em = dict()
        dm = dict()
        seq = 0
        seq = removedominators(em, dm, up, seq)
        timetwo = time.time()

        print('done! Time taken:', timetwo - timeone)
        sys.stdout.flush()

        nedges = 0
        for u in up:
            nedges += len(up[u])

        print("Original # edges:", nedges)
        print('# dominators removed:', seq)
        #print('edge-marks:')
        #for e in em:
        #   print('\t'+str(e)+': '+str(em[e]))

        print('Saving em to', emfilename, end='...')
        sys.stdout.flush()
        saveem(em, emfilename)

    # em = set()
    nzerodeg = 0
    for u in up:
        for p in up[u]:
            e = tuple((u, p))

            if hasbeenremoved(e, em):
                continue

            if not neighbours(e, em, up, pu):
                nzerodeg += 1

    print('# edges with no neighbours:', nzerodeg)


    # up_pieces = find_partitions(up)
    # print('# connected components: ', len(up_pieces))
    # Enumerate 'cliques'
    num_bicliques = 0
    print('Enumerating cliques:')
    start_time = datetime.datetime.now()
    print('Start time:', start_time)

    # for up_piece in up_pieces:
    #     pu_piece = uptopu(up_piece)

    max_bc_size = 0
    sum_biclique_sizes = 0
    bicliques = list()
    for c in find_bicliquesbp(em, up, pu, list()):
        if len(c) > 0:
            bicliques.append(len(c))
            c_users = {item[0] for item in c}
            c_perms = {item[1] for item in c}
            #print(c_users, c_perms)
            # sys.stdout.flush()
            num_bicliques += 1
            sum_biclique_sizes += len(c)
            if len(c) > max_bc_size:
                max_bc_size = len(c)
    counts_bcs = Counter(bicliques)
    top_10 = counts_bcs.most_common(len(counts_bcs.keys()))
    print("Top 10 most frequent entries:")
    for item, count in top_10:
        print(f"- {item}: {count} occurrences")

    print('Average size of maximal biclique', sum_biclique_sizes / num_bicliques)
    print('# bicliques: ', num_bicliques)
    print('Size of largest maximal biclique', max_bc_size)
    end_time = datetime.datetime.now()
    print('Time taken:', (end_time - start_time).total_seconds())


def main():
    print('Start time:', datetime.datetime.now())
    sys.stdout.flush()

    if len(sys.argv) != 2:
        print('Usage: ', end = '')
        print(sys.argv[0], end = ' ')
        print('<input-file>')
        return
    run(sys.argv[1])


if __name__ == '__main__':
    main()
