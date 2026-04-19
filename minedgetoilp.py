#! /usr/bin/python3

import sys
import time
import datetime
import signal

import gurobipy as gp
from gurobipy import GRB
from gurobipy import LinExpr

from readup import readup
from readup import uptopu


def sighandler(signum, frame):
        raise Exception("timeout")

def minedgetoilp(up, perSolveTime):
    TIMELIMIT = perSolveTime # seconds

    signal.alarm(0)

    pu = uptopu(up)

    nu = len(up.keys())
    np = len(pu.keys())
    nr = 2*max(nu, np)

    timeone = time.time()
    timetwo = time.time()

    env = gp.Env(empty=True)
    env.setParam("OutputFlag", 0)
    env.start()
    
    #construct and solve ILP instance
    
    #print('Constructing LP...')
    sys.stdout.flush()

    m = gp.Model("minedge", env=env)

    # Variables
    # For each user i, for each role r, a variable c_i_r
    # For each perm j, for each role r, a variable d_j_r

    print('Adding variables and objective...', end='')
    sys.stdout.flush()

    signal.signal(signal.SIGALRM, sighandler)
    signal.alarm(TIMELIMIT)

    try:
        for r in range(nr):
            for u in up:
                m.addVar(name='c_'+str(u)+'_'+str(r), vtype=GRB.BINARY)
            for p in pu:
                m.addVar(name='d_'+str(p)+'_'+str(r), vtype=GRB.BINARY)
        m.update()

        # For each perm j possessed by a user i, a variable a_i_j
        for u in up:
            for p in up[u]:
                m.addVar(name='a_'+str(u)+'_'+str(p), vtype=GRB.BINARY)

                # For each role r, a variable b_i_j_r
                for r in range(nr):
                    m.addVar(name='b_'+str(u)+'_'+str(p)+'_'+str(r), vtype=GRB.BINARY)
        m.update()
        
        #print('Adding objective...', end='')
        #sys.stdout.flush()

        m.update()
        m.ModelSense = GRB.MINIMIZE

        obj = LinExpr()
        obj_role_perm_edges = LinExpr()
        for r in range(nr):
            for u in up:
                obj.addTerms(1.0, m.getVarByName('c_'+str(u)+'_'+str(r)))
            for p in pu:
                obj.addTerms(1.0, m.getVarByName('d_'+str(p)+'_'+str(r)))
        # for r in range(nr):
        #     for p in pu:
        #         obj_role_perm_edges.addTerms(1.0, m.getVarByName('d_'+str(p)+'_'+str(r)))
        m.setObjectiveN(obj, index=0, priority=1)
        m.update()
        # m.setObjectiveN(obj_role_perm_edges, index=1, priority=0)

        # m.setObjective(obj, GRB.MINIMIZE)
        m.update()
    except Exception as e:
        print('time out!', end = ' ')
        sys.stdout.flush()
        signal.alarm(0)
        timetwo = time.time()
        print('Time taken (seconds): ', round(timetwo - timeone))
        return -1, None, None

    timetwo = time.time()
    print('done! Time taken (seconds): ', round(timetwo - timeone))
    sys.stdout.flush()

    signal.alarm(TIMELIMIT) # Renew alarm

    print('Adding constraints...', end='')
    sys.stdout.flush()

    timeone = time.time()
    try:
        # For each perm p possessed by user u
        for u in up:
            for p in up[u]:
                c = LinExpr()
                c.addTerms(1.0, m.getVarByName('a_'+str(u)+'_'+str(p)))
                m.addConstr(c >= 1)

                c = LinExpr()
                c.addTerms(-1.0, m.getVarByName('a_'+str(u)+'_'+str(p)))
                for r in range(nr):
                    c.addTerms(1.0, m.getVarByName('b_'+str(u)+'_'+str(p)+'_'+str(r)))
                m.addConstr(c >= 0)

                for r in range(nr):
                    c = LinExpr()
                    c.addTerms(-1.0, m.getVarByName('b_'+str(u)+'_'+str(p)+'_'+str(r)))
                    c.addTerms(1.0, m.getVarByName('a_'+str(u)+'_'+str(p)))
                    m.addConstr(c >= 0)

                    c = LinExpr()
                    c.addTerms(-1.0, m.getVarByName('b_'+str(u)+'_'+str(p)+'_'+str(r)))
                    c.addTerms(1.0, m.getVarByName('c_'+str(u)+'_'+str(r)))
                    m.addConstr(c >= 0)

                    c = LinExpr()
                    c.addTerms(-1.0, m.getVarByName('b_'+str(u)+'_'+str(p)+'_'+str(r)))
                    c.addTerms(1.0, m.getVarByName('d_'+str(p)+'_'+str(r)))
                    m.addConstr(c >= 0)

                    c = LinExpr()
                    c.addTerms(1.0, m.getVarByName('b_'+str(u)+'_'+str(p)+'_'+str(r)))
                    c.addTerms(-1.0, m.getVarByName('c_'+str(u)+'_'+str(r)))
                    c.addTerms(-1.0, m.getVarByName('d_'+str(p)+'_'+str(r)))
                    m.addConstr(c >= -1)
        m.update()

        #print('Adding constraints, Set 2...', end='')
        #sys.stdout.flush()

        # For each perm p NOT possessed by a user u
        for u in up:
            notpset = set(pu.keys()) - up[u]
            for p in notpset:
                for r in range(nr):
                    c = LinExpr()
                    c.addTerms(-1.0, m.getVarByName('c_'+str(u)+'_'+str(r)))
                    c.addTerms(-1.0, m.getVarByName('d_'+str(p)+'_'+str(r)))
                    m.addConstr(c >= -1)

        m.update()
    except Exception as e:
        print('time out!', end = ' ')
        sys.stdout.flush()
        signal.alarm(0)
        timetwo = time.time()
        print('Time taken (seconds): ', round(timetwo - timeone))
        return -1, None, None

    timetwo = time.time()
    print('done! Time taken (seconds): ', round(timetwo - timeone))
    sys.stdout.flush()


    timeone = time.time()
    print('About to call m.optimize()...', end='')
    sys.stdout.flush()

    signal.alarm(0) # Cancel any alarms; we'll rely on gurobi 
                    # for the time limit

    m.setParam(GRB.Param.TimeLimit, float(TIMELIMIT))

    try:
        m.optimize()
    except Exception as e:
        print('time out!', end = ' ')
        sys.stdout.flush()
        signal.alarm(0)
        m.terminate()
        timetwo = time.time()
        print('Time taken (seconds): ', round(timetwo - timeone))
        return -1, None, None

    # else
    signal.alarm(0)
    if m.status == GRB.OPTIMAL:
        print('success!', end=' ')
    elif m.status == GRB.TIME_LIMIT:
        print('time out!', end=' ')
    timetwo = time.time()
    print('Time taken (seconds): ', round(timetwo - timeone))
    sys.stdout.flush()

    timetwo = time.time()
    #print('LP solved, time:', timetwo - timeone)
    #sys.stdout.flush()
    
    if m.status != GRB.OPTIMAL and m.status != GRB.TIME_LIMIT:
        print('Weird. m.status != (GRB.OPTIMAL, GRB.TIME_LIMIT). Exiting...')
        sys.exit()
    
    if m.SolCount > 0:
        print('Obj: %g' % obj.getValue())
        sys.stdout.flush()

        roletousersmap = dict()
        roletopermsmap = dict()

        for r in range(nr):
            for u in up:
                v = m.getVarByName('c_'+str(u)+'_'+str(r))
                if v.getAttr(GRB.Attr.X):
                    if r not in roletousersmap:
                        roletousersmap[r] = set()
                    (roletousersmap[r]).add(u)
            for p in pu:
                v = m.getVarByName('d_'+str(p)+'_'+str(r))
                if v.getAttr(GRB.Attr.X):
                    if r not in roletopermsmap:
                        roletopermsmap[r] = set()
                    (roletopermsmap[r]).add(p)
        return int(obj.getValue()), roletousersmap, roletopermsmap
    else:
        print('m.SolCount:', m.SolCount)
        return -1, None, None

def main():
    print('Start time:', datetime.datetime.now())
    sys.stdout.flush()

    if len(sys.argv) != 3:
        print('Usage: ', end = '')
        print(sys.argv[0], end = ' ')
        print('<input-up-file> <solve-time>')
        return

    up = readup(sys.argv[1])
    if not up:
        return

    solveTime = int(sys.argv[2])

    obj, rtoumap, rtopmap = minedgetoilp(up, solveTime)

    print('obj:', obj)
    print('rtoumap:', rtoumap)
    print('rtopmap:', rtopmap)

    print('End time:', datetime.datetime.now())
    sys.stdout.flush()

if __name__ == '__main__':
    main()
