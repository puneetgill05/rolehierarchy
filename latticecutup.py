#! /usr/bin/python3

import sys
import time
import os
import datetime
import networkx as nx

from readup import readup_and_usermap_permmap
from removedominatorsbp import readem, saveem
from removedominatorsbp import dmfromem
from greedythenlattice import latticeshrink


def mergeem(emone, emtwo):
    # Merge everything from emtwo into emone
    for e in emtwo:
        if e in emone:
            continue
        emone[e] = emtwo[e]



def main():
    print('Start time:', datetime.datetime.now())
    sys.stdout.flush()

    if len(sys.argv) < 3:
        print('Usage: ', end='')
        print(sys.argv[0], end=' ')
        print('<up-file> <em-file-1> <em-file-2> ...')
        return

    print('Reading and merging ems...', end='')
    sys.stdout.flush()

    em = dict()
    upfilename = sys.argv[1]
    for fnum in range(2, len(sys.argv)):
        fname = sys.argv[fnum]
        if not os.path.exists(fname):
            print(fname, 'does not exist! Exiting...')
            sys.stdout.flush()
            sys.exit(0)

        thisem = readem(fname)
        mergeem(em, thisem)


    saveem(em, 'test-em.txt')
    print('done!')
    sys.stdout.flush()

    print('Creating rolesasperms...', end='')
    sys.stdout.flush()

    # Create roles as permissions
    rolesasperms = list()
    dm = dmfromem(em)
    G = nx.Graph()
    for e in dm:
        if e == tuple((-1, -1)):
            for f in dm[e]:
                G.add_node(f)
        else:
            for f in dm[e]:
                G.add_edge(e, f)

    # One role per connected component in G
    for c in nx.connected_components(G):
        r = set()  # our role as a set of permissions
        for t in c:
            r.add(t[1])
        rolesasperms.append(r)

    print('done! len(rolesasperms):', len(rolesasperms))
    sys.stdout.flush()

    latticeshrink(rolesasperms)

    print('After lattice-shrink, len(rolesasperms):', len(rolesasperms))
    sys.stdout.flush()

    up, usermap_orig, permmap_orig = readup_and_usermap_permmap(upfilename)

    roles_after_lattice = []
    for role in rolesasperms:
        role_as_edges = set()
        for u in up:
            perm_intersect = role & up[u]
            for p in perm_intersect:
                role_as_edges.add((u, p))
        roles_after_lattice.append(role_as_edges)

    edges_in_total_roles = set()
    num_edges = 0
    for role_edges in roles_after_lattice:
        edges_in_total_roles.update(role_edges)
        num_edges += len(role_edges)

    print(f'All roles: {len(roles_after_lattice)}')

    up_edges = {(u, p) for u in up for p in up[u]}

    missing_edges = up_edges.difference(edges_in_total_roles)
    print('Missing edges:', len(missing_edges))

    print(f'Total # roles: {len(roles_after_lattice)}')
    print(f'Total # edges in roles: {num_edges}')

    print('End time:', datetime.datetime.now())


if __name__ == '__main__':
    main()




#
# import sys
# import os
# import datetime
# import networkx as nx
#
# from readup import readup_and_usermap_permmap
# from removedominatorsbp import readem, saveem, dmfromem
# from greedythenlattice import latticeshrink
#
#
# def mergeem(emone, emtwo):
#     # Merge everything from emtwo into emone
#     for e in emtwo:
#         if e in emone:
#             continue
#         emone[e] = emtwo[e]
#
#
# def update_em(cut_em: dict, cut_usermap: dict, cut_permmap: dict, full_usermap: dict, full_permmap: dict):
#     inv_cut_usermap = {v: k for k, v in cut_usermap.items()}
#     inv_cut_permmap = {v: k for k, v in cut_permmap.items()}
#
#     new_em = dict()
#     for e in cut_em:
#         u = e[0]
#         p = e[1]
#         U = inv_cut_usermap[u]
#         P = inv_cut_usermap[p]
#         new_u = full_usermap[U]
#         new_p = full_permmap[P]
#
#         du = cut_em[e][0]
#         dp = cut_em[e][1]
#         if du == -1 and dp == -1:
#             new_em[(new_u, new_p)] = cut_em[e]
#
#
# def main():
#     print('Start time:', datetime.datetime.now())
#     sys.stdout.flush()
#
#     if len(sys.argv) < 2:
#         print('Usage: ', end='')
#         print(sys.argv[0], end=' ')
#         print('<cut-file-1> <cut-file-2> ...')
#         return
#
#     print('Reading and merging ems...', end='')
#     sys.stdout.flush()
#
#     em = dict()
#     usermap = dict()
#     permmap = dict()
#
#     for fnum in range(1, len(sys.argv)):
#         fname = sys.argv[fnum]
#         upmap_fname = f'{fname}-upmap.txt'
#         em_fname = f'{fname}-em.txt'
#         if not os.path.exists(fname) or not os.path.exists(upmap_fname) or not os.path.exists(em_fname):
#             print(f'{fname} or {upmap_fname} or {em_fname} does not exist! Exiting...')
#             sys.stdout.flush()
#             sys.exit(0)
#
#         cut_up, cut_usermap, cut_permmap = readup_and_usermap_permmap(fname)
#         inv_cut_usermap = {v: k for k, v in cut_usermap.items()}
#         inv_cut_permmap = {v: k for k, v in cut_permmap.items()}
#
#         for u in cut_usermap:
#             if u not in usermap:
#                 usermap[u] = cut_usermap[u]
#         for p in cut_permmap:
#             if p not in permmap:
#                 permmap[p] = cut_permmap[p]
#
#         thisem = readem(em_fname)
#
#         # mergeem(em, thisem)
#
#     saveem(em, 'inputsup/combined-em.txt')
#
#     print('done!')
#     sys.stdout.flush()
#
#     print('Creating rolesasperms...', end='')
#     sys.stdout.flush()
#
#     # Create roles as permissions
#     rolesasperms = list()
#     dm = dmfromem(em)
#     G = nx.Graph()
#     for e in dm:
#         if e == tuple((-1, -1)):
#             for f in dm[e]:
#                 G.add_node(f)
#         else:
#             for f in dm[e]:
#                 G.add_edge(e, f)
#
#     # One role per connected component in G
#     for c in nx.connected_components(G):
#         r = set()  # our role as a set of permissions
#         for t in c:
#             r.add(t[1])
#         rolesasperms.append(r)
#
#     print('done! len(rolesasperms):', len(rolesasperms))
#     sys.stdout.flush()
#
#     latticeshrink(rolesasperms)
#
#     print('After lattice-shrink, len(rolesasperms):', len(rolesasperms))
#     sys.stdout.flush()
#
#     print('End time:', datetime.datetime.now())
#
#
# def main_OLD():
#     print('Start time:', datetime.datetime.now())
#     sys.stdout.flush()
#
#     if len(sys.argv) < 2:
#         print('Usage: ', end='')
#         print(sys.argv[0], end=' ')
#         print('<em-file-1> <em-file-2> ...')
#         return
#
#     print('Reading and merging ems...', end='')
#     sys.stdout.flush()
#
#     em = dict()
#     for fnum in range(1, len(sys.argv)):
#         fname = sys.argv[fnum]
#         if not os.path.exists(fname):
#             print(fname, 'does not exist! Exiting...')
#             sys.stdout.flush()
#             sys.exit(0)
#
#         thisem = readem(fname)
#         mergeem(em, thisem)
#
#     saveem(em, 'inputsup/combined-em.txt')
#
#     print('done!')
#     sys.stdout.flush()
#
#     print('Creating rolesasperms...', end='')
#     sys.stdout.flush()
#
#     # Create roles as permissions
#     rolesasperms = list()
#     dm = dmfromem(em)
#     G = nx.Graph()
#     for e in dm:
#         if e == tuple((-1, -1)):
#             for f in dm[e]:
#                 G.add_node(f)
#         else:
#             for f in dm[e]:
#                 G.add_edge(e, f)
#
#     # One role per connected component in G
#     for c in nx.connected_components(G):
#         r = set()  # our role as a set of permissions
#         for t in c:
#             r.add(t[1])
#         rolesasperms.append(r)
#
#     print('done! len(rolesasperms):', len(rolesasperms))
#     sys.stdout.flush()
#
#     latticeshrink(rolesasperms)
#
#     print('After lattice-shrink, len(rolesasperms):', len(rolesasperms))
#     sys.stdout.flush()
#
#     print('End time:', datetime.datetime.now())
#
#
# if __name__ == '__main__':
#     main_OLD()


