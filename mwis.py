#! /usr/bin/python3

import sys
import time
from minedgerolemining.readup import readup
from constructg import constructGNetworkx
import networkx
import gurobipy as gp
from gurobipy import GRB
from gurobipy import LinExpr

def printZs(z):
    print('Zs that are 1:')
    nonezs = 0
    for u in z:
        if z[u]:
            print('\t'+str(u))
            nonezs += 1

    print('\tCount:', nonezs)
    sys.stdout.flush()

def removedominators(G):
    domsremoved = 0
    nodes = set(G.nodes)
    fixpoint = False

    while not fixpoint:
        fixpoint = True
        for n in nodes:
            domsn = set()
            if n in G:
                nset = set(G[n])
                nset.add(n)
                for m in G[n]:
                    mset = set(G[m])
                    mset.add(m)
                    if nset.issubset(mset):
                        domsn.add(m)
            if domsn:
                fixpoint = False
            for m in domsn:
                G.remove_node(m)
                domsremoved += 1

    print('Dominators removed:', domsremoved)
    sys.stdout.flush()
    return

def verticesbydegree(G):
    vdeg = list(G.degree)
    vdeg.sort(key=lambda t : t[1])
    return vdeg

def constructfirstcliqueset(G, vdeg, maxcliques):
    #print('constructfirstcliqueset')
    #sys.stdout.flush()

    cliqueset = list() # return value
    S = set() # vertices already included in cliqueset

    n = vdeg[0][0]

    #print('find_cliques:', n, end='')
    #sys.stdout.flush()

    maxcliques[n] = networkx.find_cliques(G, [n])

    for c in maxcliques[n]:
        cliqueset.append(c)
        S.update(c)
        break

    #print('done!')
    #sys.stdout.flush()

    for u in vdeg:
        if u[0] not in S:
            #print('find_cliques:', u[0], end='')
            #sys.stdout.flush()

            maxcliques[u[0]] = networkx.find_cliques(G, [u[0]])

            for c in maxcliques[u[0]]:
                cliqueset.append(c)
                S.update(c)
                break

            #print('done!')
            #sys.stdout.flush()

    return cliqueset

def constructcliqueset(cliqueset, G, maxcliques, z):
    cliquesetchanged = False
    for n in z:
        if z[n] == 1:
            if n not in maxcliques:
                maxcliques[n] = networkx.find_cliques(G, [n])
            for c in maxcliques[n]:
                if c not in cliqueset:
                    cliqueset.append(c)
                    cliquesetchanged = True
                break
    return cliquesetchanged

def constructcliquesetaggressive(cliqueset, G, maxcliques, z):
    cliquesetchanged = False
    for n in z:
        if z[n] == 1:
            if n not in maxcliques:
                maxcliques[n] = networkx.find_cliques(G, [n])
            for c in maxcliques[n]:
                if c not in cliqueset:
                    cliqueset.append(c)
                cliquesetchanged = True
    return cliquesetchanged

def main():
    if len(sys.argv) != 2:
        print('Usage: ', end = '')
        print(sys.argv[0], end = ' ')
        print('<input-file>')
        sys.exit()
    
    up = readup(sys.argv[1])
    if not up:
        sys.exit()
    
    timeone = time.time()
    G = constructGNetworkx(up)
    timetwo = time.time()
    print('G constructed. Time taken:', timetwo-timeone)
    sys.stdout.flush()
    
    #n vertices
    print('# vertices before dom removal:', len(G))
    sys.stdout.flush()
    
    #remove dominators
    removedominators(G)
    timeone = time.time()
    print('Time to remove dom:', timeone - timetwo)
    sys.stdout.flush()
    
    #n vertices
    print('# vertices after dom removal:', len(G))
    sys.stdout.flush()
    
    # Vertices sorted by degree
    vdeg = verticesbydegree(G)
    
    #remove 0 degree vertices
    nzerodeg = 0 
    for i, u in enumerate(vdeg):
        if u[1] == 0:
            G.remove_node(u[0])
            nzerodeg += 1
    
    print('nzerodeg removed:', nzerodeg)

    if not G:
        print('Empty graph remains. Exiting...')
        return

    for i in range(nzerodeg):
        vdeg.pop(0)
    
    print('Min degree vertex:', vdeg[0][0])
    print('Min degree:', vdeg[0][1])
    sys.stdout.flush()
    
    vdeg.reverse()
    print('Max degree vertex:', vdeg[0][0])
    print('Max degree:', vdeg[0][1])
    sys.stdout.flush()
    
    maxcliques = dict()
    
    cliqueset = constructfirstcliqueset(G, vdeg, maxcliques)
    timetwo = time.time()
    print('First cliqueset constructed, time:', timetwo - timeone)
    sys.stdout.flush()
    
    z = dict()
    
    env = gp.Env(empty=True)
    env.setParam("OutputFlag", 0)
    env.start()
    
    done = False # set when max objective < 1 or cliqueset has all maxsets.
    
    while not done:
        print('cliqueset size:', len(cliqueset))
        #print('cliqueset: ', cliqueset)
        sys.stdout.flush()
    
        #construct and solve ILP instance
    
        m = gp.Model("maxset", env=env)
        for snum in range(len(cliqueset)):
            m.addVar(name='v_'+str(snum), vtype=GRB.CONTINUOUS)
        m.update()
    
        obj = LinExpr()
        for u in m.getVars():
            obj.addTerms(1.0, u)
        m.setObjective(obj, GRB.MINIMIZE)
        m.update()
    
        for u in vdeg:
            c = LinExpr()
            for snum, theset in enumerate(cliqueset):
                if u[0] in theset:
                    c.addTerms(1.0, m.getVarByName('v_'+str(snum)))
            m.addConstr(c >= 1, 'c_'+str(u[0][0])+'_'+str(u[0][1]))
    
        for u in m.getVars():
            m.addConstr(u >= 0, 'c_'+u.getAttr("VarName"))
    
        m.update()
        #print('Model maxsets built! About to solve...')
        #sys.stdout.flush()

        timeone = time.time()
        print('Maxsets LP constructed, time:', timeone - timetwo)
        sys.stdout.flush()
    
        m.optimize()

        timetwo = time.time()
        print('Maxsets LP solved, time:', timetwo - timeone)
        sys.stdout.flush()
    
        if m.status != GRB.OPTIMAL:
            print('Weird. m.status != GRB.OPTIMAL for maxsets. Exiting...')
            sys.exit()
    
        print('Obj: %g' % obj.getValue())
        #print('Obj: %g' % obj.getValue())
        sys.stdout.flush()
    
        #setup the mwis LP instance
        duals = dict()
        #print('Pi values: ', end='')
       # sys.stdout.flush()
        for c in m.getConstrs():
            duals[c.getAttr("ConstrName")] = c.Pi
            #print(c.Pi, end=' ')
            #sys.stdout.flush()
        #print()
        #sys.stdout.flush()
    
        m = gp.Model("mwis", env=env)
        for u in vdeg:
            m.addVar(name='z_'+str(u[0][0])+'_'+str(u[0][1]), vtype=GRB.BINARY)
        m.update()
    
        obj = LinExpr()
        for u in vdeg:
            obj.addTerms(duals['c_'+str(u[0][0])+'_'+str(u[0][1])], m.getVarByName('z_'+str(u[0][0])+'_'+str(u[0][1])))
    
        m.setObjective(obj, GRB.MAXIMIZE)
        m.update()
    
        for u in G.nodes:
            for v in G.nodes:
                if v != u and v not in G[u]:
                    #if not m.getConstrByName('c_'+str(v[0])+'_'+str(v[1])+'_'+str(u[0])+'_'+str(u[1])):
                    m.addConstr(m.getVarByName('z_'+str(u[0])+'_'+str(u[1])) +
                                m.getVarByName('z_'+str(v[0])+'_'+str(v[1])) <= 1,
                                'c_'+str(u[0])+'_'+str(u[1])+'_'+str(v[0])+'_'+str(v[1]))
    
        m.update()

        timeone = time.time()
        print('MWIS LP constructed, time:', timeone - timetwo)
        sys.stdout.flush()
    
        #print('Model mwis built! About to solve...')
        #sys.stdout.flush()
    
        m.optimize()

        timetwo = time.time()
        print('MWIS LP solved, time:', timetwo - timeone)
        sys.stdout.flush()
    
        if (m.Status != GRB.OPTIMAL):
            print('Weird. m.status != GRB.OPTIMAL for mwis. Exiting...')
            sys.exit()
    
        print('Obj: %g' % obj.getValue())
    
        if obj.getValue() <= 1.0:
            print('Obj <= 1.0, exiting...')
            done = True
            continue
    
        for v in m.getVars():
            l = (v.VarName).split('_')
            z[tuple((int(l[1]), int(l[2])))] = int(v.X)
    
        printZs(z)
    
        oldcliquesetsize = len(cliqueset)
        cliquesetchanged = True
    
        while cliquesetchanged and len(cliqueset) < 2 * oldcliquesetsize:
            cliquesetchanged = constructcliqueset(cliqueset, G, maxcliques, z)
            #print("Iter:", len(cliqueset), oldcliquesetsize, ', cliquesetchanged:', cliquesetchanged)

        timeone = time.time()
        print('New cliquesetconstructed, time:', timeone - timetwo)
        sys.stdout.flush()
        timetwo = time.time()

        print('len(cliqueset):', len(cliqueset), ', oldcliquesetsize:', oldcliquesetsize, ', len(cliqueset) - oldcliquesetsize:', len(cliqueset) - oldcliquesetsize)
        sys.stdout.flush()
    
        if len(cliqueset) - oldcliquesetsize > 0:
            cliquesetchanged = True
    
        if not cliquesetchanged:
            print('cliqueset unchanged; exiting loop...')
            done = True
            continue

if __name__ == '__main__':
    main()
