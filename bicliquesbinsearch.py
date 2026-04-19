#! /usr/bin/python3

import datetime
import sys
import time

from readup import readup, uptopu
from removedominatorsbp import removedominators, isneighbour
import gurobipy as gp
from gurobipy import GRB
from gurobipy import LinExpr

def bicliquesbinsearch(em, up, pu):
    totaltime = 0.0

    nusers = len(up)
    nperms = len(pu)
    eset = set()
    for u in up:
        for p in up[u]:
            t = tuple((u,p))
            if t in em:
                continue
            eset.add(t)

    nedges = len(eset)

    hi = nusers
    if hi > nperms:
        hi = nperms
    if hi > nedges:
        hi = nedges
    lo = 1
    sol = hi

    while lo <= hi:
        mid = (lo + hi)//2
        timeone = time.time()
        env = gp.Env(empty=True)
        env.setParam("OutputFlag", 0)
        env.start()

        #construct and solve ILP instance
        print('Constructing bicliques LP with mid:', mid)
        sys.stdout.flush()

        m = gp.Model("maxset", env=env)

        print('Adding variables...', end='')
        sys.stdout.flush()
        for e in eset:
            for i in range(mid):
                m.addVar(name='x_'+str(e[0])+'_'+str(e[1])+'_'+str(i), vtype=GRB.BINARY)
        m.update()

        print('done!')
        sys.stdout.flush()

        # Constraints 1: every edge in at least 1 biclique
        print('Adding Constraints 1...', end='')
        sys.stdout.flush()
        for e in eset:
            l = LinExpr()
            for i in range(mid):
                u = m.getVarByName('x_'+str(e[0])+'_'+str(e[1])+'_'+str(i))
                l.addTerms(1.0, u)
            m.addConstr(l >= 1, 'c_1_'+str(e[0])+'_'+str(e[1]))
        print('done!')
        sys.stdout.flush()

        # Constraints 2: non-adjacent edges not in same biclique
        print('Adding Constraints 2...', end='')
        sys.stdout.flush()
        for e in eset:
            for f in eset:
                if e >= f or isneighbour(e, f, up):
                    continue
                for i in range(mid):
                    u = m.getVarByName('x_'+str(e[0])+'_'+str(e[1])+'_'+str(i))
                    v = m.getVarByName('x_'+str(f[0])+'_'+str(f[1])+'_'+str(i))
                    m.addConstr(u + v <= 1, 'c_2_'+str(e[0])+'_'+str(e[1])+'_'+str(f[0])+'_'+str(f[1]))
        m.update()
        print('done! Solving...')
        sys.stdout.flush()

        m.optimize()
        #m.write('irreducible_binsearch.lp')
        timetwo = time.time()
        totaltime += timetwo - timeone

        print('Status for mid = ', mid, ':', m.status)
        print('Time taken:', timetwo - timeone, '; totaltime:', totaltime)
        sys.stdout.flush()

        if m.status == GRB.OPTIMAL:
            sol = mid
            print('New sol:', sol)
            sys.stdout.flush()
            hi = mid - 1
        else:
            lo = mid + 1

    return sol

def main():
    print('Start time:', datetime.datetime.now())
    sys.stdout.flush()

    if len(sys.argv) != 2:
        print('Usage: ', end = '')
        print(sys.argv[0], end = ' ')
        print('<input-file>')
        return
    run(sys.argv[1])


def run(upfilename: str):
    up = readup(upfilename)
    if not up:
        return

    pu = uptopu(up)

    """
    em = dict()
    emfilename = sys.argv[1]+'-em.txt'

    if not os.path.isfile(emfilename):
        print('Removing doms + zero-neighbour edges...')
        sys.stdout.flush()

        timeone = time.time()
        em = dict()
        dm = dict()
        seq = 0
        seq = removedominators(em, dm, up, seq)
        timetwo = time.time()

        print('done! Time taken:', timetwo - timeone)
        sys.stdout.flush()

        print('Saving em to', emfilename, end=' ')
        sys.stdout.flush()
        saveem(em, emfilename)
        print('done!')
        sys.stdout.flush()
    else:
        print('Reading em from', emfilename, end=' ')
        sys.stdout.flush()
        em = readem(emfilename)
        print('done!')
        print('Determining em and seq', end=' ')
        sys.stdout.flush()
        dm = dmfromem(em)
        seq = 0
        for e in em:
            if seq < em[e][2]:
                seq = em[e][2]
        print('done!')
        sys.stdout.flush()
    """

    print('Removing dominators + 0-deg...', end='')
    sys.stdout.flush()
    em = dict()
    dm = dict()
    seq = 0
    seq = removedominators(em, dm, up, seq)
    print('done!')
    sys.stdout.flush()

    nedges = 0
    for u in up:
        nedges += len(up[u])

    print("Original # edges:", nedges)
    print('# dominators + zero neighbour edges removed:', seq)
    print('# remaining edges:', nedges - seq)

    """
    print('em:')
    for e in em:
        print('\t'+str(e)+': '+str(em[e]))

    print('dm:')
    for d in dm:
        print('\t'+str(d)+': '+str(dm[d]))
    """

    nzerodeg = 0
    for e in em:
        if em[e][0] < 0:
            nzerodeg += 1

    print('# edges with no neighbours:', nzerodeg)
    sys.stdout.flush()

    if nedges - seq > 0:
        # em = dict()
        obj = int(bicliquesbinsearch(em, up, pu))
    else:
        obj = 0

    print('Obj:', obj)
    print('Final solution:', nzerodeg + obj)

    print('End time:', datetime.datetime.now())


if __name__ == '__main__':
    main()
