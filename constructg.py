#! /usr/bin/python3

import sys
import time
#from readup import readup
import networkx as nx
from pyvis.network import Network
import re

def findrole(e, em):
    while em[e][0] >= 0:
        e = em[e]
    return e

def visualizerbac(infile, outfile):
    nt = Network('1000px', '1800px', layout=True)
    nt.toggle_physics(False)
    nt.select_menu = True
    nt.show_buttons(filter_=['physics'])

    f = open(infile, 'r')
    em = dict()
    for line in f:
        r = re.findall(r'-?\d+\.?\d*', line)
        em[tuple((int(r[0]), int(r[1])))] = tuple((int(r[2]), int(r[3])))
    f.close()

    perms = set()
    users = set()
    roles = set()
    for e in em:
        perms.add(e[1])
        users.add(e[0])
        if em[e][0] < 0:
            roles.add(tuple((e[0], e[1])))

    G = nx.Graph()
    for p in perms:
        nt.add_node('p' + str(p), color='green', level=3)

    for u in users:
        nt.add_node('u' + str(u), color='red', level=1)

    for r in roles:
        nt.add_node('r' + str(r), color='blue', level=2)

    for e in em:
        r = findrole(e, em)
        nt.add_edge('u' + str(e[0]), 'r' + str(r))
        nt.add_edge('p' + str(e[1]), 'r' + str(r))

    nt.save_graph(outfile)

    return

def visualizeup(up, filename):
    nt = Network('1000px', '1800px', layout=True)
    nt.toggle_physics(False)
    nt.select_menu = True
    nt.show_buttons(filter_=['physics'])

    perms = set()
    for u in up:
        perms = perms.union(up[u])

    G = nx.Graph()
    for p in perms:
        nt.add_node('p' + str(p), color='green', level=2)

    for u in up:
        nt.add_node('u' + str(u), color='red', level=1)

    for u in up:
        for p in up[u]:
            nt.add_edge('u' + str(u), 'p' + str(p))

    nt.save_graph(filename)

    return

def visualizeG(G, filename):
    nt = Network('1000px', '1800px')
    nt.toggle_physics(False)
    nt.select_menu = True
    nt.show_buttons(filter_=['physics'])

    H = nx.Graph()
    for e in G:
        H.add_node(str(e), color='red')

    for e in G:
        for f in G[e]:
            H.add_edge(str(e), str(f), color='green')

    nt.from_nx(H)
    nt.save_graph(filename)

    return

def constructGNetworkx(up):
    G = nx.Graph()
    for u in up:
        for p in up[u]:
            v = tuple((u,p))
            G.add_node(v)

    for v in G:
        for w in G:
            if v == w:
                continue
            if w[1] in up[v[0]] and v[1] in up[w[0]]:
                G.add_edge(v, w)

    return G

def constructGwithWeights(up, em):
    G = dict()
    for u in up:
        for p in up[u]:
            v = tuple((u,p))
            if tuple((u,p)) in em:
                continue
            G[v] = set()

    for v in G:
        for w in G:
            if v == w:
                continue
            if w[1] in up[v[0]] and v[1] in up[w[0]]:
                (G[v]).add(tuple((w, 1)))

    return G

def constructGnoWeights(up, em):
    nedges = 0
    for u in up:
        nedges += len(up[u])

    ne = 0
    G = nx.Graph()
    for u in up:
        for p in up[u]:
            ne += 1
            if not (ne % 10000):
                print('constructGnoweights(): for loop #1, # edges:', ne, '/', nedges)
                sys.stdout.flush()
            v = tuple((u,p))
            if tuple((u,p)) in em:
                continue
            G.add_node(v)

    ne = 0
    for v in G.nodes:
        for w in G.nodes:
            ne += 1
            if not (ne % 10000000):
                print('constructGnoweights(): for loop #2, # edges:', ne, '/', len(G.nodes)*len(G.nodes))
                sys.stdout.flush()
            if v == w:
                continue
            if w[1] in up[v[0]] and v[1] in up[w[0]]:
                (G).add_edge(v, w)

    return G

"""
def main():
    starttime = time.time()
    if len(sys.argv) != 2:
        print('Usage: ', end = '')
        print(sys.argv[0], end = ' ')
        print('<input-file>')
        return

    up = readup(sys.argv[1])
    if not up:
        return

    G = constructGwithWeights(up, dict())
    endtime = time.time()

    print('G constructed. Time taken:', endtime-starttime)
    sys.stdout.flush()

    print('size of G:', (sys.getsizeof(G))//1000, 'kbytes')
    #print('G:')
    #for u in G:
    #    print(u, ':', G[u])

    #visualizeG(G, "G.html")
    #print('Dumped to G.html.')

if __name__ == '__main__':
    main()
"""
