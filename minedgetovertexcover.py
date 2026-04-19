#! /usr/bin/python3

import sys
import time
import datetime

from minedgerolemining.readup import readup
from minedgerolemining.readup import uptopu

def addclause(clauses, c):
    clauses.append(c)

def addliteraltoclause(c, l):
    c.add(l)

def newclause():
    return set()

def notconsistent(l, m):
    # literal l is not consistent with literal m
    if (l[0] != '-' and m[0] != '-') or (l[0] == '-' and m[0] == '-'):
        return False
    if l.lstrip('-') == m.lstrip('-'):
        return True
    return False

def minedgetovertexcover(upfilename, nr):
    up = readup(sys.argv[1])
    if not up:
        return

    pu = uptopu(up)

    nu = len(up.keys())
    np = len(pu.keys())

    print('nu:', nu, ', np:', np, ', nr:', nr)
    sys.stdout.flush()

    npermsassigned = 0
    for u in up:
        npermsassigned += len(up[u])
    print('npermsassigned:', npermsassigned)
    sys.stdout.flush()

    clauses = list()

    # Variables
    # For each user i, for each role r, a variable c_i_r
    # For each perm j, for each role r, a variable d_j_r
    # For each perm j possessed by a user i, a variable a_i_j
    # For each role r, a variable b_i_j_r

    # Now we add the clauses

    # For each perm p possessed by user u
    for u in up:
        for p in up[u]:
            c = newclause()
            addliteraltoclause(c, 'a_'+str(u)+'_'+str(p))
            addclause(clauses, c)

            c = newclause()
            addliteraltoclause(c, '-a_'+str(u)+'_'+str(p))
            for r in range(nr):
                addliteraltoclause(c, 'b_'+str(u)+'_'+str(p)+'_'+str(r))
            addclause(clauses, c)

            for r in range(nr):
                c = newclause()
                addliteraltoclause(c, '-b_'+str(u)+'_'+str(p)+'_'+str(r))
                addliteraltoclause(c, 'a_'+str(u)+'_'+str(p))
                addclause(clauses, c)

                c = newclause()
                addliteraltoclause(c, '-b_'+str(u)+'_'+str(p)+'_'+str(r))
                addliteraltoclause(c, 'c_'+str(u)+'_'+str(r))
                addclause(clauses, c)

                c = newclause()
                addliteraltoclause(c, '-b_'+str(u)+'_'+str(p)+'_'+str(r))
                addliteraltoclause(c, 'd_'+str(p)+'_'+str(r))
                addclause(clauses, c)

                c = newclause()
                addliteraltoclause(c, 'b_'+str(u)+'_'+str(p)+'_'+str(r))
                addliteraltoclause(c, '-c_'+str(u)+'_'+str(r))
                addliteraltoclause(c, '-d_'+str(p)+'_'+str(r))
                addclause(clauses, c)

    print('Clauses generated for u-p that exist.')
    sys.stdout.flush()

    # For each perm p NOT possessed by a user u
    for u in up:
        notpset = set(pu.keys()) - up[u]
        for p in notpset:
            for r in range(nr):
                c = newclause()
                addliteraltoclause(c, '-c_'+str(u)+'_'+str(r))
                addliteraltoclause(c, '-d_'+str(p)+'_'+str(r))
                addclause(clauses, c)

    print('Clauses generated for u-p that do not exist.')
    sys.stdout.flush()

    print('Total # hard clauses:', len(clauses))
    sys.stdout.flush()

    vtolitmap = dict() # vertex -> literal
    vtoclausenummap = dict() # vertex -> clause num

    nrelaxable = nu*nr + np*nr # num relaxable clauses
    print('Total # relaxable clauses:', nrelaxable)
    sys.stdout.flush()

    v = 0
    clausenum = 0

    # hard clauses
    for iter in range(nrelaxable+1):
        for c in clauses:
            for l in c:
                vtolitmap[v] = l
                vtoclausenummap[v] = clausenum
                v += 1
            clausenum += 1

    print('Vertices generated for hard clauses.')
    sys.stdout.flush()
    
    # relaxable clauses
    relaxableclausenumstart = clausenum
    for r in range(nr):
        for u in up:
            l = '-c_'+str(u)+'_'+str(r)
            vtolitmap[v] = l
            vtoclausenummap[v] = clausenum
            v += 1
            clausenum += 1
        for p in pu:
            l = '-d_'+str(u)+'_'+str(r)
            vtolitmap[v] = l
            vtoclausenummap[v] = clausenum
            v += 1
            clausenum += 1

    print('Vertices generated for relaxable clauses.')
    sys.stdout.flush()

    print('Total # vertices:', v)
    sys.stdout.flush()
    
    # now construct the graph G, which is a list of lists
    # each inner list at index i is the adjacent vertices to i
    G = list()
    timeone = time.time()
    for u in range(v):
        adju = list()
        for w in range(v):
            if w == u:
                continue
            if vtoclausenummap[u] == vtoclausenummap[w]:
                # Add an edge
                adju.append(w)
                continue
            
            if notconsistent(vtolitmap[u], vtolitmap[w]):
                adju.append(w)
                continue
        G.append(adju)
        if u%1000 == 0:
            timetwo = time.time()
            print('adj list for vertex', u, 'done. Time taken:', timetwo - timeone, 'seconds')
            timeone = time.time()
            sys.stdout.flush()

    vcfilename = upfilename + "-minedgetovertexcover.txt"
    f = open(vcfilename, 'w')

    print('Writing to file', vcfilename, end='...')
    sys.stdout.flush()

    for u in range(len(G)):
        f.write(str(u)+':')
        for i in range(len(G[u])):
            f.write(str(G[u][i]))
            if i < len(G[u]) - 1:
                f.write(',')
        f.write('\n')
    f.close()

    print('done!')
    sys.stdout.flush()

def main():
    print('Start time:', datetime.datetime.now())
    sys.stdout.flush()

    if len(sys.argv) != 3:
        print('Usage: ', end = '')
        print(sys.argv[0], end = ' ')
        print('<input-up-file> <max # roles>')
        return

    minedgetovertexcover(sys.argv[1], int(sys.argv[2]))

    print('End time:', datetime.datetime.now())
    sys.stdout.flush()

if __name__ == '__main__':
    main()
