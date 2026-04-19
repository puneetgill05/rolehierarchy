import os
import random
import sys
import time
from datetime import datetime
import json
from enum import Enum
from itertools import combinations
from typing import List

import gurobipy as gp
# import networkx as nx

from gurobipy import GRB

prefix_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(f'{prefix_dir}/..')
sys.path.append(f'{prefix_dir}')
print(sys.path)

from createILP import get_nroles, reduce_to_ilp
# from matplotlib import pyplot as plt

from threadutils import MyTask

from readup import readup_and_usermap_permmap
from utils import (calculate_number_of_edges, get_roles_as_edges, find_partitions, break_up, check_roles,
                   get_unique_items, getResults, bicliques_to_roles_as_edges, get_roles_mapped,
                   calculate_number_of_edges_in_up)

'''
Reduce the BicliqueCoverToILP problem.
Asks the following questions:
Decision version: Does there exist a biclique in the input bipartite graph G with k1 users and k2 permissions?

Binary Variables:
u_i = 1 if user i is in the biclique
u_i = 0 otherwise

p_j = 1 if permission j is in the biclique
p_j = 0 otherwise

Constraints:
1) If there is no edge between user i and permission j then
    - at most 1 of user i or permission j must be in the biclique

    for (i, j) where user i does not have an edge to permission j in the input G:
        u_i + p_j <= 1

2) We require that the number of users in the biclque be at least k1
    - u_1 + u_2 + ... + u_m >= k1
    where the number of users in the input G is m
       
3) We require that the number of permissions in the biclque be at least k2
    - p_1 + p_2 + ... + p_n >= k2
    where the number of permissions in the input G is n

Example:
u1: [p1, p2]
u2: [p1, p2, p3]

k1: 2, k2: 2

Binary variables:
u_1, u_2,
p_1, p_2, p3

Constraints:
1) If there is no edge between user i and permission j then
    - at most 1 of user i or permission j must be in the biclique
    u_1 + p_3 <= 1

2) We require that the number of users in the biclque be at least k1
    u_1 + u_2 >= k1

3) We require that the number of permissions in the biclque be at least k2
    p_1 + p_2 _ p_3 >= k2

Solution:
    k1 = 1, k2 = 3
    u_1 = 1, u_2 = 0, p_1 = 1, p_2 = 1, p_3 = 1
    
    k1 = 2, k2 = 2
    u_1 = 1, u_2 = 1, p_1 = 1, p_2 = 1, p_3 = 0
    
    k1 = 2, k2 = 3
    No Solution

Params:
G: Bipartite graph representing the user-permission mapping
k1: number of users in the biclique
k2: number of permissions in the biclique
'''


def bicliqueCoverToILP_decide(up, k1, k2):
    users = set()
    perms = set()
    for u in up:
        users.add(u)
        perms = perms.union(up[u])

    m = gp.Model("bicliquetoilp_decide")

    for u in users:
        u_str = 'u_{user}'.format(user=u)
        m.addVar(vtype=GRB.BINARY, name=u_str)

    for p in perms:
        p_str = 'p_{perm}'.format(perm=p)
        m.addVar(vtype=GRB.BINARY, name=p_str)

    m.update()
    for u in users:
        for p in perms:
            # if there is no edge between this user and permission, then only one of them can be in the biclique
            if p not in up[u]:
                u_str = 'u_{user}'.format(user=u)
                p_str = 'p_{perm}'.format(perm=p)
                m.addConstr(m.getVarByName(u_str) + m.getVarByName(p_str) <= 1, 'no_edge_constr')
    m.update()

    # min k1 users in the biclique
    sum_users_expr = gp.LinExpr()
    for u in users:
        u_str = 'u_{user}'.format(user=u)
        sum_users_expr += m.getVarByName(u_str)
    m.addConstr(sum_users_expr >= k1, 'min_num_users_k1')

    # min k2 permissions in the biclique
    sum_perms_expr = gp.LinExpr()
    for p in perms:
        p_str = 'p_{perm}'.format(perm=p)
        sum_perms_expr += m.getVarByName(p_str)
    m.addConstr(sum_perms_expr >= k2, 'min_num_perms_k2')

    m.setObjective(0, GRB.MAXIMIZE)
    m.update()
    m.write('test_decide.lp')
    m.optimize()
    m.write('test_decide.sol')


'''
Reduce the BicliqueCoverToILP problem.
Asks the following questions:
Optimization version: What is the maximum biclique in the input bipartite graph G?
Objective function: Maximize the number of users and permissions in the biclique 

Binary Variables:
u_i = 1 if user i is in the biclique
u_i = 0 otherwise

p_j = 1 if permission j is in the biclique
p_j = 0 otherwise

Objective:
    Maximize u_1 + u_2 + ... + u_m + p_1 + p_2 + ... + p_n

Constraints:
1) If there is no edge between user i and permission j then
    - at most 1 of user i or permission j must be in the biclique

    for (i, j) where user i does not have an edge to permission j in the input G:
        u_i + p_j <= 1

Example:
u1: [p1, p2]
u2: [p1, p2, p3]

k1: 2, k2: 2

Binary variables:
u_1, u_2,
p_1, p_2, p3

Objective:
    Maximize u_1 + u_2 + p_1 + p_2 + p_3

Constraints:
1) If there is no edge between user i and permission j then
    - at most 1 of user i or permission j must be in the biclique
    u_1 + p_3 <= 1
    
This constraint makes sure that (user, permission) pair which do not have an edge, not both are included in the 
biclique.

The objective function is maximizing the addition of users and permissions to the biclique, so combined with the 
constraint it will force the assignment to the binary variables such that only users and permissions that form a 
biclique are included.

Solution:
    u_1 = 1, u_2 = 1, p_1 = 1, p_2 = 1, p_3 = 0
Objective: 4

Params:
G: Bipartite graph representing the user-permission mapping
'''


class ObjType(Enum):
    VERTICES = 1
    EDGES = 2


def bicliqueCoverToILP_opt(up: dict, objType: ObjType):
    num_users, num_perms, num_edges = get_stats(up)
    users = set()
    perms = set()
    for u in up:
        users.add(u)
        perms = perms.union(up[u])

    m = gp.Model("bicliquetoilp_opt")

    usermap = dict()
    permmap = dict()
    for u in users:
        u_str = 'u_{user}'.format(user=u)
        m.addVar(vtype=GRB.BINARY, name=u_str)
        usermap[u] = u_str

    for p in perms:
        p_str = 'p_{perm}'.format(perm=p)
        m.addVar(vtype=GRB.BINARY, name=p_str)
        permmap[p] = p_str

    m.update()
    for u in users:
        for p in perms:
            # if there is no edge between this user and permission, then only one of them can be in the biclique
            if p not in up[u]:
                u_str = 'u_{user}'.format(user=u)
                p_str = 'p_{perm}'.format(perm=p)
                m.addConstr(m.getVarByName(u_str) + m.getVarByName(p_str) <= 1, 'no_edge_constr')
    m.update()

    # maximize the number of user and permissions in the biclique
    if objType == ObjType.VERTICES:
        objective = gp.LinExpr()
        for var in m.getVars():
            objective += var
        m.setObjective(objective, GRB.MAXIMIZE)
    elif objType == ObjType.EDGES:
        sum_users = gp.LinExpr()
        sum_perms = gp.LinExpr()
        for var in m.getVars():
            if var.VarName.startswith('u_'):
                sum_users += var
            if var.VarName.startswith('p_'):
                sum_perms += var
        objective = sum_users * sum_perms
        m.setObjective(objective, GRB.MAXIMIZE)

    m.update()
    # m.write('test_opt.lp')
    m.optimize()
    # m.write('test_opt.sol')

    vars_included_in_sol = set()
    for var in json.loads(m.getJSONSolution())['Vars']:
        vars_included_in_sol.add(var['VarName'])
    print('Number of variables: ', len(vars_included_in_sol))

    sol = json.loads(m.getJSONSolution())['SolutionInfo']['ObjVal']
    print('Solution so far: ', sol)
    print('Biclique created with the following: ', vars_included_in_sol)
    return sol, {0: vars_included_in_sol}


def bicliqueToILP_decide_orig(up, k1, k2):
    users = set()
    perms = set()
    for u in up:
        users.add(u)
        perms = perms.union(up[u])

    m = gp.Model("bicliquetoilp_decide_orig")

    for j in range(k1):
        for u in users:
            u_str = 'u_{user}_{j}'.format(user=u, j=j)
            m.addVar(vtype=GRB.BINARY, name=u_str)

    for l in range(k2):
        for p in perms:
            p_str = 'p_{perm}_{l}'.format(perm=p, l=l)
            m.addVar(vtype=GRB.BINARY, name=p_str)

    m.update()

    # 1) at least 1 vertex from U for each of the k1 positions
    for j in range(k1):
        atleast_1_user_per_position_expr = gp.LinExpr()
        for u in users:
            u_str = 'u_{user}_{j}'.format(user=u, j=j)
            atleast_1_user_per_position_expr += m.getVarByName(u_str)
        m.addConstr(atleast_1_user_per_position_expr >= 1)

    # 2a) no user is assigned to more than 1 position
    for u in users:
        positions = [(j, j_prime) for j in range(k1) for j_prime in range(k1) if j != j_prime]
        already_added = set()
        for j, j_prime in positions:
            if (j, j_prime) in already_added or (j_prime, j) in already_added:
                continue

            u_str1 = 'u_{user}_{j}'.format(user=u, j=j)
            u_str2 = 'u_{user}_{j}'.format(user=u, j=j_prime)
            m.addConstr(m.getVarByName(u_str1) + m.getVarByName(u_str2) <= 1, name='2a')

            already_added.add((j, j_prime))
    m.update()

    # 2b) no permission is assigned to more than 1 position
    for p in perms:
        positions = [(l, l_prime) for l in range(k2) for l_prime in range(k2) if l != l_prime]
        already_added = set()

        for l, l_prime in positions:
            if (l, l_prime) in already_added or (l_prime, l) in already_added:
                continue
            p_str1 = 'p_{perm}_{l}'.format(perm=p, l=l)
            p_str2 = 'p_{perm}_{l}'.format(perm=p, l=l_prime)
            m.addConstr(m.getVarByName(p_str1) + m.getVarByName(p_str2) <= 1, name='2b')
            already_added.add((l, l_prime))

    m.update()

    # 3) at least 1 vertex from P for each of the k2 positions
    for l in range(k2):
        atleast_1_perm_per_position_expr = gp.LinExpr()
        for p in perms:
            p_str = 'p_{perm}_{l}'.format(perm=p, l=l)
            atleast_1_perm_per_position_expr += m.getVarByName(p_str)
        m.addConstr(atleast_1_perm_per_position_expr >= 1)
    m.update()

    # 4) if two vertices are not connected, then the variables representing these vertices cannot be both satisfied
    for u in users:
        for p in perms:
            # if there is no edge between this user and permission, then only one of them can be in the biclique
            if p not in up[u]:
                for j in range(k1):
                    for l in range(k2):
                        u_str = 'u_{user}_{j}'.format(user=u, j=j)
                        p_str = 'p_{perm}_{l}'.format(perm=p, l=l)
                        m.addConstr(m.getVarByName(u_str) + m.getVarByName(p_str) <= 1, 'no_edge_constr')
    m.update()

    m.setObjective(0, GRB.MAXIMIZE)
    m.update()
    m.write('test_decide_orig.lp')
    m.optimize()
    m.write('test_decide_orig.sol')


# def createGraph(up: dict):
#     G = nx.Graph()
#     for u in up:
#         G.add_node('u_{u}'.format(u=u))
#         for p in up[u]:
#             G.add_node('p_{p}'.format(p=p))
#             G.add_edge('u_{u}'.format(u=u), 'p_{p}'.format(p=p))
#     return G


# Run the exact algorithm with a timelimit
def runILPModel(up, users, perms, nroles, timelimit):
    m = gp.Model("minedgesILP")
    m.Params.TimeLimit = timelimit
    print('Running exact ILP algorithm')

    m = reduce_to_ilp(up, users, perms, nroles, m)
    m.optimize()
    return m


# Algorithm to run greedy and exact in conjunction and compare the results
def greedyBicliqueAndExact(up, sol, multiplier):
    num_users, num_perms, num_edges = get_stats(up)
    print('Solution so far greedy + exact: ', sol)

    users = set(up.keys())
    perms = {p for u in up for p in up[u]}
    nroles = get_nroles(up, users, perms, num_edges)
    # print('# roles:', nroles)

    if num_users == 0 or num_perms == 0:
        print('Solution found: ', sol)
        return sol

    m1 = runILPModel(up, users, perms, nroles, multiplier * 300)
    print('m1 status: ', m1.status)

    if m1.status == GRB.OPTIMAL:
        sol += m1.getObjective().getValue()
        print('Objective value: ', sol)
        return sol
    elif m1.status == GRB.SUBOPTIMAL or m1.status == GRB.TIME_LIMIT:
        try:
            subOptimalObj1 = m1.getObjective().getValue()
            print('Non-Optimal Objective value from ILP: ', subOptimalObj1)

            print('Running greedy algorithm')
            up_prime, sol_prime, role_created = greedyBicliqueToILP_opt(up)
            print("Greedy solution found: ", sol_prime)
            _, _, num_edges_prime = get_stats(up_prime)

            users_prime = set(up_prime.keys())
            perms_prime = {p for u in up_prime for p in up_prime[u]}
            nroles_prime = get_nroles(up_prime, users_prime, perms_prime, num_edges_prime)

            m2 = runILPModel(up_prime, users_prime, perms_prime, nroles_prime, multiplier * 300)
            print('m2 status: ', m2.status)
            if m2.status == GRB.SUBOPTIMAL or m2.status == GRB.OPTIMAL or m2.status == GRB.TIME_LIMIT:
                try:
                    obj2 = m2.getObjective().getValue()
                    print("Objective 2 value on up_prime: ", obj2)
                    print('Comparing: {sol} + {obj1} < {sol} + {sol_prime} + {obj2}'.format(sol=sol,
                                                                                            obj1=subOptimalObj1,
                                                                                            sol_prime=sol_prime,
                                                                                            obj2=obj2))
                    if sol + subOptimalObj1 < sol + sol_prime + obj2:
                        # continue with up and run the algorithm (in the recursive call, run ILP solver) for longer
                        return greedyBicliqueAndExact(up, sol, 2 * multiplier)
                    else:
                        # continue with up' and run the algorithm with up' and sol' added to the sol
                        multiplier = 1
                        return greedyBicliqueAndExact(up_prime, sol + sol_prime, multiplier)
                except:
                    print('Non-Optimal Objective value from ILP not reached')
                    return greedyBicliqueAndExact(up, sol, 2 * multiplier)
            else:
                return greedyBicliqueAndExact(up, sol, 2 * multiplier)
        except:
            print('Non-Optimal Objective value from ILP not reached')
            return greedyBicliqueAndExact(up, sol, 2 * multiplier)
    else:
        try:
            print('Non-Optimal Objective value from ILP: ', m1.getObjective().getValue())
        except:
            print('Non-Optimal Objective value from ILP not reached')
        return greedyBicliqueAndExact(up, sol, 2 * multiplier)


# Greedy Algorithm
# Problem: Given an input bipartite graph G_up of users and permissions, find a biclique with maximum number of vertices
# Objective: Maximize the number of users and permissions in the biclique
def greedyBicliqueToILP_opt(up: dict) -> (dict, int, set):
    if len(up) == 0:
        return {}, 0, set()
    users = set()
    perms = set()
    for u in up:
        users.add(u)
        perms = perms.union(up[u])

    m = gp.Model("greedyBicliqueToILP_opt")
    usermap = dict()
    permmap = dict()
    for u in users:
        u_str = 'u_{user}'.format(user=u)
        m.addVar(vtype=GRB.BINARY, name=u_str)
        usermap[u] = u_str

    for p in perms:
        p_str = 'p_{perm}'.format(perm=p)
        m.addVar(vtype=GRB.BINARY, name=p_str)
        permmap[p] = p_str

    m.update()
    for u in users:
        for p in perms:
            # if there is no edge between this user and permission, then only one of them can be in the biclique
            if p not in up[u]:
                u_str = 'u_{user}'.format(user=u)
                p_str = 'p_{perm}'.format(perm=p)
                m.addConstr(m.getVarByName(u_str) + m.getVarByName(p_str) <= 1, 'no_edge_constr')
    m.update()

    # maximize the number of user and permissions in the biclique
    sum_users = gp.LinExpr()
    sum_perms = gp.LinExpr()
    for var in m.getVars():
        if var.VarName.startswith('u_'):
            sum_users += var
        if var.VarName.startswith('p_'):
            sum_perms += var

    num_edges_var = m.addVar(vtype=GRB.CONTINUOUS, name='num_edges')
    m.addConstr(sum_users >= 1, 'atleast_1_biclique1')
    m.addConstr(sum_perms >= 1, 'atleast_1_biclique2')
    m.addConstr(num_edges_var == sum_users * sum_perms, 'quadratic_constraint_num_edges')

    m.update()
    m.ModelSense = GRB.MAXIMIZE
    objective = num_edges_var - (sum_users + sum_perms)
    m.setObjectiveN(objective, index=0, priority=1)
    # m.setObjective(objective, GRB.MAXIMIZE)
    m.update()
    m.setObjectiveN((sum_users + sum_perms), index=1, priority=0)
    m.update()
    # m.write('test_opt1.lp')
    m.optimize()

    new_up = dict()
    vars_included_in_sol = set()
    for var in json.loads(m.getJSONSolution())['Vars']:
        if var['VarName'].startswith('u_') or var['VarName'].startswith('p_'):
            vars_included_in_sol.add(var['VarName'])
    print('Number of variables: ', len(vars_included_in_sol))

    for u in up:
        for p in up[u]:
            if usermap[u] in vars_included_in_sol and permmap[p] in vars_included_in_sol:
                continue
            if u in new_up:
                new_up[u].add(p)
            else:
                new_up[u] = {p}

    sol = len(vars_included_in_sol)
    print('Solution so far during greedy: ', sol)
    print('Role created with the following: ', vars_included_in_sol)
    return new_up, sol, vars_included_in_sol


# Description: Recursively call this function to greedily find a Biclique with ((the)) maximum difference between the
# number of edges and vertices
def greedyBicliqueToILP_opt_recursive(up, sol, roles_created):
    if len(up) == 0:
        return up, sol, roles_created
    users = set()
    perms = set()
    for u in up:
        users.add(u)
        perms = perms.union(up[u])

    m = gp.Model("greedyBicliqueToILP_opt_recursive")
    m.setParam("Presolve", 1)

    usermap = dict()
    permmap = dict()
    for u in users:
        u_str = 'u_{user}'.format(user=u)
        m.addVar(vtype=GRB.BINARY, name=u_str)
        usermap[u] = u_str

    for p in perms:
        p_str = 'p_{perm}'.format(perm=p)
        m.addVar(vtype=GRB.BINARY, name=p_str)
        permmap[p] = p_str

    m.update()
    for u in users:
        for p in perms:
            # if there is no edge between this user and permission, then only one of them can be in the biclique
            if p not in up[u]:
                u_str = 'u_{user}'.format(user=u)
                p_str = 'p_{perm}'.format(perm=p)
                m.addConstr(m.getVarByName(u_str) + m.getVarByName(p_str) <= 1, 'no_edge_constr')
    m.update()

    # maximize the number of user and permissions in the biclique
    sum_users = gp.LinExpr()
    sum_perms = gp.LinExpr()
    for var in m.getVars():
        if var.VarName.startswith('u_'):
            sum_users += var
        if var.VarName.startswith('p_'):
            sum_perms += var

    num_edges_var = m.addVar(vtype=GRB.CONTINUOUS, name='num_edges')
    m.addConstr(sum_users >= 1, 'atleast_1_biclique1')
    m.addConstr(sum_perms >= 1, 'atleast_1_biclique2')
    m.addConstr(num_edges_var == sum_users * sum_perms, 'quadratic_constraint_num_edges')
    m.update()

    m.ModelSense = GRB.MAXIMIZE

    objective = num_edges_var - (sum_users + sum_perms)
    m.setObjectiveN(objective, index=0, priority=0)
    # m.setObjective(objective, GRB.MAXIMIZE)
    m.update()
    m.setObjectiveN((sum_users + sum_perms), index=1, priority=0)
    m.update()
    m.optimize()
    # m.write('test_opt.sol')

    new_up = dict()
    vars_included_in_sol = set()
    for var in json.loads(m.getJSONSolution())['Vars']:
        if var['VarName'].startswith('p_') or var['VarName'].startswith('u_'):
            vars_included_in_sol.add(var['VarName'])
            print('Variable value: ', var['VarName'], ' -> ', var)
        else:
            print('Number of edges in the biclique: ', var)
    print('Number of variables: ', len(vars_included_in_sol))
    print('Variables: ', vars_included_in_sol)

    for u in up:
        for p in up[u]:
            if usermap[u] in vars_included_in_sol and permmap[p] in vars_included_in_sol:
                continue
            if u in new_up:
                new_up[u].add(p)
            else:
                new_up[u] = {p}

    newsol = len(vars_included_in_sol)
    print('Role created with the following: ', vars_included_in_sol)
    roles_created[len(roles_created)] = vars_included_in_sol
    print('Solution so far during greedy: ', sol)

    return greedyBicliqueToILP_opt_recursive(new_up, sol + newsol, roles_created)


def get_stats(up):
    perms = set()
    num_users = 0
    num_edges = 0
    for u in up:
        num_users += 1
        for p in up[u]:
            num_edges += 1
            perms.add(p)
    num_perms = len(perms)
    print('Number of users: ', num_users)
    print('Number of permissions: ', num_perms)
    print('Number of edges: ', num_edges)
    return num_users, num_perms, num_edges


def preprocess(up: dict, num_edges_threshold: int) -> list:
    up_components = find_partitions(up)

    up_components_new = list()
    for up in up_components:
        num_edges = calculate_number_of_edges_in_up(up)
        if num_edges > num_edges_threshold:
            broken_ups = break_up(up, num_edges_threshold)
            up_components_new.extend(broken_ups)
        else:
            up_components_new.append(up)
    return up_components_new

def run_greedy_delta(upfilepath: str, threshold: int):

    print('Reading file ', upfilepath)
    up_orig, usermap, permmap = readup_and_usermap_permmap(upfilepath)


    if not up_orig:
        return

    up_components_new = preprocess(up_orig, threshold)

    roles_as_edges = list()
    for up in up_components_new:
        bicliques = set()
        new_up = up
        while True:
            print('Size of up: ', len(new_up))
            if len(new_up) == 0:  # or new_up in up_computed_already:
                break
            # up_computed_already.append(new_up)
            new_up, sol, biclique = greedyBicliqueToILP_opt(new_up)
            bicliques.add(tuple(biclique))

        roles_as_edges_in_this_iter = bicliques_to_roles_as_edges(bicliques)
        roles_as_edges.extend(roles_as_edges_in_this_iter)
    if check_roles(roles_as_edges, up_orig):
        print('RBAC holds')
        total_num_roles, total_num_edges = getResults(roles_as_edges)
        print('Total # roles: ', total_num_roles)
        print('Total # edges: ', total_num_edges)
        return roles_as_edges
    else:
        print('RBAC failed')
        return None

def main():
    print('Start time:', datetime.now())
    sys.stdout.flush()

    if len(sys.argv) != 3:
        print('Usage: ', end='')
        print(sys.argv[0], end=' ')
        print('<input-file> <threshold>')
        return

    upfilepath = sys.argv[1]
    threshold = int(sys.argv[2])

    timeone = time.time()
    roles_as_edges = run_greedy_delta(upfilepath, threshold)
    timetwo = time.time()

    print('done! Time taken:', timetwo - timeone)
    sys.stdout.flush()


class GreedyDeltaTask(MyTask):
    up_orig = None
    roles_as_edges = list()

    def pre_execute(self, args):
        upfilepath = args[0]
        threshold = args[1]
        print('Reading file ', upfilepath)
        up_orig, usermap, permmap = readup_and_usermap_permmap(upfilepath)

        self.up_orig = up_orig
        if not up_orig:
            return

        up_components_new = preprocess(up_orig, threshold)
        print('# partitions: ', len(up_components_new))
        return up_components_new

    def task(self, up):
        bicliques = set()
        new_up = up
        while True:
            if len(new_up) == 0:  # or new_up in up_computed_already:
                break
            new_up, sol, biclique = greedyBicliqueToILP_opt(new_up)
            bicliques.add(tuple(biclique))

        roles_as_edges_in_this_iter = bicliques_to_roles_as_edges(bicliques)
        self.roles_as_edges.extend(roles_as_edges_in_this_iter)


        # new_roles = list()
        #
        # def run_heuristic_for(x: set, y: set):
        #     new_r1, new_r2 = heuristic1(x, y)
        #     # changed
        #     new_roles.append(tuple(new_r1))
        #     new_roles.append(tuple(new_r2))
        #
        # for r1, r2 in combinations(self.roles_as_edges, 2):
        #     # are permissions of r1 subset of permissions of r2
        #     run_heuristic_for(r1, r2)
        #
        # self.roles_as_edges = get_unique_items(new_roles)

    def post_execute(self, result):
        self.roles_as_edges = get_unique_items(self.roles_as_edges)

        if check_roles(self.roles_as_edges, self.up_orig):
            print('RBAC holds')
            total_num_roles, total_num_edges = getResults(self.roles_as_edges)
            print('Total # roles: ', total_num_roles)
            print('Total # edges: ', total_num_edges)
            return self.roles_as_edges
        else:
            print('RBAC failed')
            return None


def heuristic1(role1, role2):
    new_role1 = role1.copy()
    new_role2 = role2.copy()
    # permissions of role 1 are a subset of the permissions of role 2, then remove permissions of the role 1
    role1_users = {e[0] for e in role1}
    role2_users = {e[0] for e in role2}
    role1_permissions = {e[1] for e in role1}
    role2_permissions = {e[1] for e in role2}
    if role1 != role2 and role1_permissions.issubset(role2_permissions):
        # permissions to remove from role2
        permissions_to_remove = role1_permissions
        # users to add to role1
        users_to_add = role2_users

        if len(users_to_add) <= len(permissions_to_remove):
            for (u, p) in role2:
                for perm in permissions_to_remove:
                    if perm == p:
                        new_role2.remove((u, perm))

            for user in users_to_add:
                for perm in permissions_to_remove:
                    new_role1.add((user, perm))
    return new_role1, new_role2


def main_threaded():
    print('Start time:', datetime.now())
    sys.stdout.flush()

    if len(sys.argv) != 3:
        print('Usage: ', end='')
        print(sys.argv[0], end=' ')
        print('<input-file> <threshold>')
        return

    timeone = time.time()

    upfilepath = sys.argv[1]
    threshold = int(sys.argv[2])

    greedyDeltaTask = GreedyDeltaTask(num_workers=5)
    up_components_new = greedyDeltaTask.pre_execute([upfilepath, threshold])
    greedyDeltaTask.execute(up_components_new)

    timetwo = time.time()

    print('done! Time taken:', timetwo - timeone)
    sys.stdout.flush()


if __name__ == '__main__':
    main()
    # main_threaded()
