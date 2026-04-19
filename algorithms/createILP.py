import datetime
import json
import os
import sys
import time
from typing import Tuple

import gurobipy as gp
from gurobipy import GRB, Var

prefix_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(f'{prefix_dir}/..')
print(sys.path)

from readup import readup
from utils import (calculate_number_of_edges, get_roles_as_edges, find_partitions, break_up, check_roles,
                   getResults, bicliques_to_roles_as_edges, get_roles_mapped, calculate_number_of_edges_in_up)

def get_nroles(up: dict, users: set, perms: set, nedges: int):
    # nroles = int(2 * min(len(users), len(perms)))
    nroles = int(2 * max(len(users), len(perms)))
    return nroles


def get_variables_by_prefix_and_suffix(variables: dict, var_prefix: str, suffices: set) -> dict:
    ret = dict()
    for suffix in suffices:
        var_name = '{var_prefix}_{suffix}'.format(var_prefix=var_prefix, suffix=suffix)
        if var_name in variables:
            ret[var_name] = variables[var_name]
    return ret


def reduce_to_ilp(up: dict, users: set, perms: set, nroles: int, m: gp.Model) -> gp.Model:
    variables_dict = dict()
    # add variables
    # user-role variables
    for u in users:
        for r in range(nroles):
            var_c = m.addVar(vtype=GRB.BINARY, name="c_{user}_{role}".format(user=u, role=r))
            variables_dict["c_{user}_{role}".format(user=u, role=r)] = var_c
    # perm-role variables
    for p in perms:
        for r in range(nroles):
            var_d = m.addVar(vtype=GRB.BINARY, name="d_{perm}_{role}".format(perm=p, role=r))
            variables_dict["d_{perm}_{role}".format(perm=p, role=r)] = var_d

    m.update()
    c_d_vars = m.getVars()

    # user-perm and user-perm-role variables
    for u in users:
        for p in perms:
            var_a = m.addVar(vtype=GRB.BINARY, name="a_{user}_{perm}".format(user=u, perm=p))
            variables_dict["a_{user}_{perm}".format(user=u, perm=p)] = var_a

            for r in range(nroles):
                var_b = m.addVar(vtype=GRB.BINARY, name="b_{user}_{perm}_{role}".format(user=u, perm=p, role=r))
                variables_dict["b_{user}_{perm}_{role}".format(user=u, perm=p, role=r)] = var_b

    print('Variables created done')

    m.update()

    # Constraint 1: If user u has permission p
    '''
    Basic constraints:

    for each user and perm in UP
    - (c_{user}_{0} && d_{perm}_{0}) || (c_{user}_{1} && d_{perm}_{1}) || ... || (c_{user}_{nroles-1} && d_{
    perm}_{nroles-1}
    
    Constraints after Tseitein transformation:
    
    - a_{user}_{perm} 
    - a_{user}_{perm} <=> (b_{user}_{perm}_{0} || b_{user}_{perm}_{1} || ... || b_{user}_{perm}_{nroles-1})
    - b_{user}_{perm}_{0} <=> (c_{user}_{0} && d_{perm}_{0})
    - b_{user}_{perm}_{1} <=> (c_{user}_{1} && d_{perm}_{1})
    - ...
    - b_{user}_{perm}_{nroles-1} <=> (c_{user}_{nroles-1} && d_{perm}_{nroles-1})
    '''
    for u in up:
        # c_ur_set = get_variables_by_prefix(m.getVars(), 'c_{user}'.format(user=u))
        c_ur_dict = get_variables_by_prefix_and_suffix(variables_dict, 'c_{user}'.format(user=u), set(range(nroles)))

        for p in up[u]:
            a_up = variables_dict['a_{user}_{perm}'.format(user=u, perm=p)]
            not_a_up = 1 - a_up

            m.addConstr(a_up >= 1, name='user {user} has permission {perm}'.format(user=u, perm=p))

            # b_upr_set = get_variables_by_prefix(m.getVars(), 'b_{user}_{perm}'.format(user=u, perm=p))
            b_upr_dict = get_variables_by_prefix_and_suffix(variables_dict, 'b_{user}_{perm}'.format(user=u, perm=p),
                                                           set(range(nroles)))
            # d_pr_set = get_variables_by_prefix(m.getVars(), 'd_{perm}'.format(perm=p))
            d_pr_dict = get_variables_by_prefix_and_suffix(variables_dict, 'd_{perm}'.format(perm=p),
                                                           set(range(nroles)))

            # a_{user}_{perm} => b_{user}_{perm}
            m.addConstr(not_a_up + gp.quicksum(b_upr_dict.values()) >= 1,
                        name='a_{user}_{perm} => b_{user}_{perm}'
                        .format(user=u, perm=p))


            # b_{user}_{perm} => a_{user}_{perm}
            for b_upr in b_upr_dict.values():
                not_b_upr = 1 - b_upr
                m.addConstr(not_b_upr + a_up >= 1,
                            name='b_{user}_{perm} => a_{user}_{perm}'
                            .format(user=u, perm=p))

            # b_{user}_{perm}_{role} <=> (c_{user}_{role} && d_{perm}_{role})
            # print('Constraint: b_{user}_{perm}_{role} <=> (c_{user}_{role} && d_{perm}_{role}) done')

            for r in range(nroles):
                # b_upr = get_first_variable_by_suffix(list(b_upr_set), str(r))
                b_upr_list = [v for k,v in b_upr_dict.items() if k.endswith('_{role}'.format(role=r))]

                # c_ur = get_first_variable_by_suffix(list(c_ur_set), str(r))
                c_ur_list = [v for k,v in c_ur_dict.items() if k.endswith('_{role}'.format(role=r))]

                # d_pr = get_first_variable_by_suffix(list(d_pr_set), str(r))
                d_pr_list = [v for k,v in d_pr_dict.items() if k.endswith('_{role}'.format(role=r))]

                if len(c_ur_list) > 0 and len(d_pr_list) > 0 and len(b_upr_list) > 0:
                    b_upr = b_upr_list[0]
                    not_b_upr = 1 - b_upr
                    c_ur = c_ur_list[0]
                    not_c_ur = 1 - c_ur
                    d_pr = d_pr_list[0]
                    not_d_pr = 1 - d_pr

                    # b_{user}_{perm}_{role} => c_{user}_{role}
                    m.addConstr(not_b_upr + c_ur >= 1,
                                name='b_{user}_{perm}_{role} => c_{user}_{role}'
                                .format(user=u, perm=p, role=r))

                    # b_{user}_{perm}_{role} => d_{perm}_{role}
                    m.addConstr(not_b_upr + d_pr >= 1,
                                name='b_{user}_{perm}_{role} => d_{perm}_{role}'
                                .format(user=u, perm=p, role=r))

                    # (c_{user}_{role} && d_{perm}_{role}) => b_{user}_{perm}_{role}
                    m.addConstr(not_c_ur + not_d_pr + b_upr >= 1,
                                name='(c_{user}_{role} and d_{perm}_{role}) => b_{user}_{perm}_{role}'
                                .format(user=u, perm=p, role=r))

    m.update()

    print('Constraint 1 done')

    # Constraint 2: If user u does not have permission p
    '''
    Basic Constraints:
    For each role j from 0 to nroles-1
    - ! (c_{user}_{j} && d_{perm}_{j})
    
    After DeMorgan's, constraints are:    
    - ! c_{user}_{0} || ! d_{perm}_{0}
    - ! c_{user}_{1} || ! d_{perm}_{1}
    - ...
    - ! c_{user}_{nroles-1} || ! d_{perm}_{nroles-1}
    '''
    for u in up:
        for p in perms:
            if p not in up[u]:
                m.addConstr(True, 'user {user} does not have permission {perm}'.format(user=u, perm=p))
                for r in range(nroles):
                    c_ur = m.getVarByName("c_{user}_{role}".format(user=u, role=r))
                    not_c_ur = 1 - c_ur
                    d_pr = m.getVarByName("d_{perm}_{role}".format(perm=p, role=r))
                    not_d_pr = 1 - d_pr
                    m.addConstr(not_c_ur + not_d_pr >= 1,
                                name='!(c_{user}_{role} &&  d_{perm}_{role})'.format(user=u, perm=p, role=r))

    print('Constraint 2 done')

    m.update()

    # set objective
    obj = gp.quicksum(c_d_vars)

    m.setObjective(obj, GRB.MINIMIZE)
    m.update()
    print('Objective done')
    return m


def run_model(m, filepath, filename) -> gp.Model:
    m.update()
    m.write(os.path.join(filepath, filename + '.lp'))

    m.optimize()
    m.write(os.path.join(filepath, filename + '.sol'))
    return m


def rindex(input_str, target_str):
    if input_str[::-1].find(target_str) > -1:
        return len(input_str) - input_str[::-1].find(target_str)
    else:
        return 0


# High level method which calls the low level reduce_to_ilp() method to get gurobi model with objective function
# and constraints.
# This function uses the solution to create roles as a map and roles as edges from the original input graph, up
# Return: number of edges, roles (mapped), roles (as edges)
def run_ilp_and_get_roles(up: dict, users: set, perms: set, nroles: int, m: gp.Model) -> Tuple[int, dict, set]:
    m = reduce_to_ilp(up, users, perms, nroles, m)

    # optimize the model
    m.update()
    m.optimize()

    # get roles as dict
    roles = dict()
    for var in json.loads(m.getJSONSolution())['Vars']:
        if var['VarName'].startswith('c_') and var['X'] == 1:
            role = var['VarName'][rindex(var['VarName'], '_'):]
            # user = 'u_' + var['VarName'][var['VarName'].find('_')+1 : rindex(var['VarName'], '_')-1]
            user = var['VarName'][var['VarName'].find('_')+1 : rindex(var['VarName'], '_')-1]
            if role in roles:
                roles[role].add(user)
            else:
                roles[role] = {user}
        elif var['VarName'].startswith('d_') and var['X'] == 1:
            role = var['VarName'][rindex(var['VarName'], '_'):]
            # perm = 'p_' + var['VarName'][var['VarName'].find('_') + 1: rindex(var['VarName'], '_') - 1]
            perm = var['VarName'][var['VarName'].find('_') + 1: rindex(var['VarName'], '_') - 1]
            if role in roles:
                roles[role].add(perm)
            else:
                roles[role] = {perm}

    # get roles as edges
    roles_created_as_edges = get_roles_as_edges(roles)

    # calculate the number of edges in the tripartite graph
    num_edges = 0
    for r in roles_created_as_edges:
        num_edges += calculate_number_of_edges(r)

    # make sure roles assign exactly the same permissions to users as the input up
    check_roles(roles_created_as_edges, up)

    return num_edges, roles, roles_created_as_edges


def main():
    print('Start time:', datetime.datetime.now())
    sys.stdout.flush()

    if len(sys.argv) != 3:
        print('Usage: ', end='')
        print(sys.argv[0], end=' ')
        print('<input-file> <threshold>')
        return

    last_sep_index = rindex(sys.argv[1], '/')
    filepath = sys.argv[1][:last_sep_index]
    filename = sys.argv[1][last_sep_index:]

    up_orig = readup(sys.argv[1])
    if not up_orig:
        return
    threshold = int(sys.argv[2])

    nedges = 0
    users = set()
    perms = set()
    for u in up_orig:
        users.add(u)
        perms = perms.union(up_orig[u])
        nedges += len(up_orig[u])

    print('Total # users:', len(users))
    print('Total # perms:', len(perms))
    print('Total # edges:', nedges)
    sys.stdout.flush()

    time1 = time.time()
    # print('# roles to begin with:', nedges)
    # nroles = get_nroles(up, users, perms, nedges)
    # print('# roles:', nroles)
    #
    # m = gp.Model("minedgesILP")
    # num_edges, roles_mapped, roles_as_edges = run_ilp_and_get_roles(up, users, perms, nroles, m)

    up_components_new = [up_orig]
    # up_components = find_partitions(up_orig)
    #
    # up_components_new = list()
    # # threshold = 500
    # for up in up_components:
    #     num_edges = calculate_number_of_edges_in_up(up)
    #     if num_edges > threshold:
    #         broken_ups = break_up(up, threshold)
    #         up_components_new.extend(broken_ups)
    #     else:
    #         up_components_new.append(up)


    total_num_edges = 0
    total_num_roles = 0

    up_computed_already = list()
    roles_as_edges = list()
    for up in up_components_new:
        bicliques = set()
        new_up = up
        users = set()
        perms = set()
        for u in new_up:
            users.add(u)
            perms = perms.union(new_up[u])
        while True:
            if len(new_up) == 0 or new_up in up_computed_already:
                break
            up_computed_already.append(new_up)
            nroles = get_nroles(new_up, users, perms, nedges)
            print('# roles:', nroles)
            m = gp.Model("minedgesILP")
            num_edges, roles_mapped, roles_as_edges_in_this_iter = run_ilp_and_get_roles(new_up, users, perms, nroles, m)
            roles_as_edges.extend(roles_as_edges_in_this_iter)
            total_num_edges += num_edges
    if check_roles(roles_as_edges, up_orig):
        print('RBAC holds')
        total_num_roles, total_num_edges = getResults(roles_as_edges)
        print('Total # roles: ', total_num_roles)
        print('Total # edges: ', total_num_edges)
    else:
        print('RBAC failed')

    sys.stdout.flush()
    sys.stdout.flush()


if __name__ == '__main__':
    main()
