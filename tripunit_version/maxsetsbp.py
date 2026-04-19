#! /usr/bin/python3

import sys
import time
import os
import datetime
import gurobipy as gp
from gurobipy import GRB
from gurobipy import LinExpr


prefix_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(f'{prefix_dir}')
sys.path.append(f'{prefix_dir}/..')
print(sys.path)

from readup import readup
from readup import uptopu
from removedominatorsbp import removedominators
from findcliquesbp import getedgeset
from findcliquesbp import find_bicliquesbp
from removedominatorsbp import saveem
from removedominatorsbp import readem
from removedominatorsbp import dmfromem
from removedominatorsbp import hasbeenremoved


def maxsetsbp(em, up, pu, infile):
    THRESHOLD = 3000000

    print('Getting edgeset...', end='')
    sys.stdout.flush()

    edgeset = getedgeset(em, up)

    print('done!')
    sys.stdout.flush()

    cliqueset = list()
    nc = 0

    timeone = time.time()
    timetwo = time.time()

    for c in find_bicliquesbp(em, up, pu, list()):
        cliqueset.append(c)
        # print('maximal biclique found:', c)
        nc += 1
        if nc > THRESHOLD:
            print('# cliques >', THRESHOLD, ', giving up...', end='')
            sys.stdout.flush()
            break
        if not (nc % 10000):
            timetwo = time.time()
            print(nc, ', Time:', timetwo - timeone)
            sys.stdout.flush()
            timeone = time.time()

    if nc > THRESHOLD:
        print('End time:', datetime.datetime.now())
        sys.stdout.flush()
        sys.exit()

    print('# cliques:', nc)
    sys.stdout.flush()

    env = gp.Env(empty=True)
    env.setParam("OutputFlag", 0)
    env.start()

    # construct and solve ILP instance

    print('Constructing Maxsets LP...')
    sys.stdout.flush()
    constrtimeone = time.time()

    m = gp.Model("maxset", env=env)
    pc = 0
    for snum in range(len(cliqueset)):
        m.addVar(name='v_' + str(snum), vtype=GRB.BINARY)
        pc += 1
        if not (pc % 10000):
            print('Added var', pc, '/', len(cliqueset), '...')
            sys.stdout.flush()
    m.update()

    pc = 0
    obj = LinExpr()
    for u in m.getVars():
        obj.addTerms(1.0, u)
        pc += 1
        if not (pc % 10000):
            print('Added term to objective', pc, '/', len(cliqueset), '...')
            sys.stdout.flush()
    m.setObjective(obj, GRB.MINIMIZE)
    m.update()

    """
    #First count the num constraints for progress-printing
    print('Figuring total # constraints...')
    sys.stdout.flush()

    nconstr = 0
    nu = 0
    for u in edgeset:
        nu += 1
        if not (nu % 1000):
            print('Edge #', nu, '/', len(edgeset), '...')
            sys.stdout.flush()
        #ns = 0
        for theset in cliqueset:
            #ns += 1
            #if not (ns % 100000):
                #print('Cliqueset #', ns, '/', len(cliqueset), '...')
                #sys.stdout.flush()
            if u in theset:
                nconstr += 1
                if not (nconstr % 100000):
                    print('Constraint #:', nconstr, '...')
                    sys.stdout.flush()
    print('done! # constraints:', nconstr)
    sys.stdout.flush()
    """

    print('Adding constraints...')
    sys.stdout.flush()

    pc = 0
    nu = 0
    timeone = time.time()
    timetwo = time.time()
    for u in edgeset:
        nu += 1
        if not (nu % 1000):
            timetwo = time.time()
            print('Edge #', nu, '/', len(edgeset), '; time taken:', timetwo - timeone, '...')
            sys.stdout.flush()
            timeone = time.time()
        c = LinExpr()
        for snum, theset in enumerate(cliqueset):
            if u in theset:
                c.addTerms(1.0, m.getVarByName('v_' + str(snum)))
                pc += 1
                if not (pc % 100000):
                    print('Added term to constraint', pc, '...')
                    sys.stdout.flush()
        m.addConstr(c >= 1, 'c_' + str(u[0]) + '_' + str(u[1]))

    m.update()

    timeone = time.time()
    print('Maxsets LP constructed, time:', timeone - constrtimeone)
    sys.stdout.flush()

    m.optimize()

    timetwo = time.time()
    print('Maxsets LP solved, time:', timetwo - timeone)
    sys.stdout.flush()

    if m.status != GRB.OPTIMAL:
        print('Weird. m.status != GRB.OPTIMAL for maxsets. Exiting...')
        sys.exit()

    print('Obj: %g' % obj.getValue())
    sys.stdout.flush()

    """
    csfile = infile+'-cs.txt'
    csf = open(csfile,'w')
    for snum, theset in enumerate(cliqueset):
        varname = 'v_'+str(snum)
        var = m.getVarByName(varname)
        if var.X:
            csf.write(str(set(theset))+'\n')
    csf.close()
    print('Solution max cliquesets written to', csfile)
    sys.stdout.flush()
    """

    """
    """
    # Update em
    print('Updating em', end='...')
    sys.stdout.flush()

    # Find highest seq num
    seq = 0
    for e in em:
        if seq < em[e][2]:
            seq = em[e][2]

    for snum, theset in enumerate(cliqueset):
        varname = 'v_' + str(snum)
        var = m.getVarByName(varname)
        if not var.X:
            continue
        firstedge = None
        for e in theset:
            if hasbeenremoved(e, em):
                continue
            seq += 1
            if not firstedge:
                em[e] = tuple((-1, -1, seq))
                firstedge = e
            else:
                em[e] = tuple((firstedge[0], firstedge[1], seq))
    print('done!')
    sys.stdout.flush()
    """
    """

    return obj.getValue()


def main():
    print('Start time:', datetime.datetime.now())
    sys.stdout.flush()

    if len(sys.argv) != 2:
        print('Usage: ', end='')
        print(sys.argv[0], end=' ')
        print('<input-file>')
        return

    up = readup(sys.argv[1])
    if not up:
        return

    # up = mapup(up, sys.argv[1])

    pu = uptopu(up)

    nedges = 0
    for u in up:
        nedges += len(up[u])

    print('Total # edges:', nedges)
    sys.stdout.flush()

    timeone = time.time()
    timetwo = time.time()

    seq = 0
    em = dict()
    dm = dict()

    """
    """
    emfilename = sys.argv[1] + '-em.txt'

    if not os.path.isfile(emfilename):
        print('Removing doms + zero-neighbour edges...')
        sys.stdout.flush()
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
        sys.stdout.flush()
        print('Determining dm and seq', end=' ')
        sys.stdout.flush()
        dm = dmfromem(em)
        for e in em:
            if seq < em[e][2]:
                seq = em[e][2]
        print('done!')
        sys.stdout.flush()

    print("Original # edges:", nedges)

    # Need to count doms and zero-neigh in my up set
    nmydom = 0
    nmyzerodeg = 0
    for e in em:
        u = e[0]
        p = e[1]

        if u in up and p in up[u]:
            if em[e][0] < 0:
                nmyzerodeg += 1
            else:
                nmydom += 1

    print('# my dominators + zero neighbour edges removed:', nmydom + nmyzerodeg)
    print('# edges with -1 annotation:', nmyzerodeg)
    """
    """

    obj = 0
    if nmydom + nmyzerodeg < nedges:
        obj = int(maxsetsbp(em, up, pu, sys.argv[1]))
        # save em
        print('Saving em to', emfilename, end='...')
        sys.stdout.flush()
        saveem(em, emfilename)
        print('done!')

    else:
        print('Nothing more to be done.')
        sys.stdout.flush()

    print('Final solution:', nmyzerodeg + obj)

    print('End time:', datetime.datetime.now())
    sys.stdout.flush()


if __name__ == '__main__':
    main()
