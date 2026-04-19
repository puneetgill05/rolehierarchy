#! /usr/bin/python3

import sys
import time
from readup import readup
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
    return

"""
if len(sys.argv) != 2:
    print('Usage: ', end = '')
    print(sys.argv[0], end = ' ')
    print('<input-file>')
    sys.exit()

up = readup(sys.argv[1])
if not up:
    sys.exit()

starttime = time.time()
G = constructGNetworkx(up)
endtime = time.time()
print('G constructed. Time taken:', endtime-starttime)
sys.stdout.flush()
"""

G = networkx.Graph()
G.add_edge(1,2)
G.add_edge(1,3)
G.add_edge(1,4)
G.add_edge(2,3)
G.add_edge(2,5)
G.add_edge(3,6)
G.add_edge(4,6)

cliqueset = list()
for c in networkx.find_cliques(G):
    cliqueset.append(c)

print('cliqueset before pop():', cliqueset)
cliqueset.pop(0)
print('cliqueset after pop():', cliqueset)

z = dict()

env = gp.Env(empty=True)
env.setParam("OutputFlag", 0)
env.start()

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

for u in G.nodes:
    c = LinExpr()
    for snum, theset in enumerate(cliqueset):
        if u in theset:
            c.addTerms(1.0, m.getVarByName('v_'+str(snum)))
    #print('u:', u, ', c.size():', c.size())
    m.addConstr(c >= 1, 'c_'+str(u))

for u in m.getVars():
    m.addConstr(u >= 0, 'c_'+u.getAttr("VarName"))

m.update()

savedmaxsets = m.copy()

m.optimize()

if m.status != GRB.OPTIMAL:
    print('Weird. m.status != GRB.OPTIMAL for maxsets. Exiting...')
    sys.exit()

print('Obj: %g' % obj.getValue())

print('Vars:')
for u in m.getVars():
    print('\t', u.VarName, ':', u.X)

#setup the mwis LP instance
duals = dict()
for c in m.getConstrs():
    duals[c.getAttr("ConstrName")] = c.Pi

print('duals:', duals)

m = gp.Model("mwis", env=env)
for u in G.nodes:
    m.addVar(name='z_'+str(u), vtype=GRB.BINARY)
m.update()

for u in G.nodes:
    for v in G.nodes:
        if v != u and v not in G[u]:
            m.addConstr(m.getVarByName('z_'+str(u)) +
                        m.getVarByName('z_'+str(v)) <= 1,
                        'c_'+str(u)+'_'+str(v))

m.update()

savedmwis = m.copy()

obj = LinExpr()
for u in G.nodes:
    d = duals['c_'+str(u)]
    if d:
        obj.addTerms(d, m.getVarByName('z_'+str(u)))
m.setObjective(obj, GRB.MAXIMIZE)
m.update()

m.optimize()

if (m.Status != GRB.OPTIMAL):
    print('Weird. m.status != GRB.OPTIMAL for mwis. Exiting...')
    sys.exit()

print('Obj: %g' % obj.getValue())

for v in m.getVars():
    l = (v.VarName).split('_')
    z[int(l[1])] = int(v.X)

printZs(z)

if obj.getValue() <= 1.0:
    print('Obj <= 1.0, exiting...')
    sys.exit()

#else
print('Obj > 1.0, continuing...')

m = savedmaxsets.copy()
cliqueset.append([1,2,3])

print('New cliqueset:', cliqueset)

snum = cliqueset.index([1,2,3])
m.addVar(name='v_'+str(snum), vtype=GRB.CONTINUOUS)
m.update()

obj = m.getObjective()
u = m.getVarByName('v_'+str(snum))
obj.addTerms(1.0, u)
m.setObjective(obj, GRB.MINIMIZE)
m.update()

for u in cliqueset[snum]:
    c = m.getConstrByName('c_'+str(u))
    l = m.getRow(c)
    #r = l.size()
    #print('old l.size():', r)
    #for i in range(r):
    #    print('old l[', i ,']:', l.getVar(i).VarName, ',', l.getCoeff(i))

    l.addTerms(1.0, m.getVarByName('v_'+str(snum)))
    m.remove(c)
    m.addConstr(l >= 1, 'c_'+str(u))

    #c = m.getConstrByName('c_'+str(u))
    #l = m.getRow(c)
    #r = l.size()
    #print('new l.size():', r)
    #for i in range(r):
    #    print('new l[', i ,']:', l.getVar(i).VarName, ',', l.getCoeff(i))

m.update()
m.optimize()

if m.status != GRB.OPTIMAL:
    print('Weird. m.status != GRB.OPTIMAL for maxsets. Exiting...')
    sys.exit()

print('Obj: %g' % obj.getValue())

print('Vars:')
for u in m.getVars():
    print('\t', u.VarName, ':', u.X)

#setup the mwis LP instance
duals = dict()
for c in m.getConstrs():
    duals[c.getAttr("ConstrName")] = c.Pi

print('duals:', duals)

m = savedmwis.copy()

obj = LinExpr()
for u in G.nodes:
    d = duals['c_'+str(u)]
    if d:
        obj.addTerms(d, m.getVarByName('z_'+str(u)))
m.setObjective(obj, GRB.MAXIMIZE)
m.update()

m.optimize()

if (m.Status != GRB.OPTIMAL):
    print('Weird. m.status != GRB.OPTIMAL for mwis. Exiting...')
    sys.exit()

print('Obj: %g' % obj.getValue())

for v in m.getVars():
    l = (v.VarName).split('_')
    z[int(l[1])] = int(v.X)

printZs(z)

if obj.getValue() <= 1.0:
    print('Obj <= 1.0, exiting...')
    sys.exit()

#else
print('Obj > 1.0, continuing...')



