import datetime
import json
import os
import random
import sys
import time
from pprint import pprint

import gurobipy as gp
from gurobipy import GRB, Var


prefix_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(f'{prefix_dir}/..')
print(sys.path)

from utils import (check_roles, check_roles_and_fix, get_roles_as_edges, get_roles_mapped,
                   calculate_number_of_edges_in_rbac, find_partitions)
from readup import readup


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


def reduce_to_lp(up: dict, users: set, perms: set, nroles: int, m: gp.Model) -> gp.Model:
    variables_dict = dict()
    # add variables
    # user-role variables
    for u in users:
        for r in range(nroles):
            var_c = m.addVar(vtype=GRB.CONTINUOUS, name="c_{user}_{role}".format(user=u, role=r))
            variables_dict["c_{user}_{role}".format(user=u, role=r)] = var_c
    # perm-role variables
    for p in perms:
        for r in range(nroles):
            var_d = m.addVar(vtype=GRB.CONTINUOUS, name="d_{perm}_{role}".format(perm=p, role=r))
            variables_dict["d_{perm}_{role}".format(perm=p, role=r)] = var_d

    m.update()
    c_d_vars = m.getVars()

    # user-perm and user-perm-role variables
    for u in users:
        for p in perms:
            var_a = m.addVar(vtype=GRB.CONTINUOUS, name="a_{user}_{perm}".format(user=u, perm=p))
            variables_dict["a_{user}_{perm}".format(user=u, perm=p)] = var_a

            for r in range(nroles):
                var_b = m.addVar(vtype=GRB.CONTINUOUS, name="b_{user}_{perm}_{role}".format(user=u, perm=p, role=r))
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
                b_upr_list = [v for k, v in b_upr_dict.items() if k.endswith('_{role}'.format(role=r))]

                # c_ur = get_first_variable_by_suffix(list(c_ur_set), str(r))
                c_ur_list = [v for k, v in c_ur_dict.items() if k.endswith('_{role}'.format(role=r))]

                # d_pr = get_first_variable_by_suffix(list(d_pr_set), str(r))
                d_pr_list = [v for k, v in d_pr_dict.items() if k.endswith('_{role}'.format(role=r))]

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

    # for var in m.getVars():
    #     m.addConstr(var >= 0)
    #     m.addConstr(var <= 1)

    m.update()

    # set objective
    obj = gp.quicksum(c_d_vars)

    m.setObjective(obj, GRB.MINIMIZE)
    m.update()
    print('Objective done')

    return m


def convert_to_dual(primal_model: gp.Model) -> gp.Model:
    dual_model = gp.Model("Dual")

    # Extract primal constraints and variables
    primal_constraints = primal_model.getConstrs()
    primal_variables = primal_model.getVars()

    # Create dual variables for each primal constraint
    dual_vars = []
    for constr in primal_constraints:
        if constr.Sense == GRB.LESS_EQUAL:
            dual_var = dual_model.addVar(lb=0, name=f"dual_{constr.ConstrName}")
        elif constr.Sense == GRB.GREATER_EQUAL:
            dual_var = dual_model.addVar(lb=0, name=f"dual_{constr.ConstrName}")
        elif constr.Sense == GRB.EQUAL:
            dual_var = dual_model.addVar(lb=-GRB.INFINITY, ub=GRB.INFINITY, name=f"dual_{constr.ConstrName}")
        dual_vars.append(dual_var)

    dual_model.update()

    # Dual objective
    dual_model.setObjective(
        sum(constr.RHS * dual_var for constr, dual_var in zip(primal_constraints, dual_vars)),
        GRB.MAXIMIZE if primal_model.ModelSense == GRB.MINIMIZE else GRB.MINIMIZE
    )

    dual_model.update()

    # Add dual constraints for each primal variable
    for var in primal_variables:
        coeffs = [primal_model.getCoeff(constr, var) for constr in primal_constraints]
        dual_model.addConstr(
            sum(coeff * dual_vars[i] for i, coeff in enumerate(coeffs)) <= var.Obj,
            name=f"dual_{var.VarName}"
        )

    dual_model.update()
    return dual_model


def randomized_rounding(m):
    c_d_vars = []
    for v in m.getVars():
        if v.VarName.startswith('c_') or v.VarName.startswith('d_'):
            c_d_vars.append(v)

    print("Fractional solution:", [c_d_vars[i].X for i in range(len(c_d_vars))])

    rounded_solution = dict()
    c_d_var_rounded_solution = dict()
    for i in range(len(c_d_vars)):
        prob = c_d_vars[i].X  # Fractional value as probability
        randomNum = random.random()
        rounded_value = 1 if prob >= randomNum else 0
        print(f'x: {prob} random: {randomNum} rounded value: {rounded_value}')

        rounded_solution[c_d_vars[i].VarName] = rounded_value
        c_d_var_rounded_solution[c_d_vars[i].VarName] = rounded_value

    for var in m.getVars():
        if var.varName not in rounded_solution:
            rounded_solution[var.VarName] = var.X
    return rounded_solution, c_d_var_rounded_solution


def doRandomizedRounding(m):
    rounded_solution, c_d_var_rounded_solution = randomized_rounding(m)
    for var in m.getVars():
        if var.VarName in rounded_solution:
            var.setAttr("Start", rounded_solution[var.varName])

    print("\nConstraint Evaluation:")
    # while True:
    #     constrsSatisfied = True
    for constr in m.getConstrs():
        lhs_value = sum(rounded_solution[var.VarName] * m.getCoeff(constr, var) for var in m.getVars())
        rhs_value = constr.RHS
        sense = constr.Sense

        if (sense == '<' and not lhs_value <= rhs_value) or \
                (sense == '>' and not lhs_value >= rhs_value) or \
                (sense == '=' and not lhs_value == rhs_value):
            print(f"{constr}: Violated (LHS = {lhs_value}, {sense} RHS = {rhs_value})")
            # rounded_solution, c_d_var_rounded_solution = randomized_rounding(m)
            for var in m.getVars():
                if var.VarName in rounded_solution:
                    var.setAttr("Start", rounded_solution[var.varName])
        #         constrsSatisfied &= False
        # if constrsSatisfied:
        #     break

    print("Rounded solution:", rounded_solution)

    new_objective_value = 0
    for var in m.getVars():
        if var.varName in c_d_var_rounded_solution:
            new_objective_value += c_d_var_rounded_solution[var.VarName]

    print("Rounded Objective:", new_objective_value)


def run_model(m, filepath, filename):
    m.update()
    m.write(os.path.join(filepath, filename + '.lp'))

    m.optimize()
    m.write(os.path.join(filepath, filename + '.sol'))

    # if m.status == GRB.OPTIMAL:
    #     doRandomizedRounding(m)


def rindex(input_str, target_str):
    if input_str[::-1].find(target_str) > -1:
        return len(input_str) - input_str[::-1].find(target_str)
    else:
        return 0


def main():
    print('Start time:', datetime.datetime.now())
    sys.stdout.flush()

    if len(sys.argv) != 3:
        print('Usage: ', end='')
        print(sys.argv[0], end=' ')
        print('<input-file>:str <time-limit>:int')
        return

    last_sep_index = rindex(sys.argv[1], '/')
    filepath = sys.argv[1][:last_sep_index]
    filename = sys.argv[1][last_sep_index:]
    timelimit = int(sys.argv[2])

    up_orig = readup(sys.argv[1])
    if not up_orig:
        return

    up_components = find_partitions(up_orig)
    total_num_edges = 0
    total_num_roles = 0

    for up in up_components:
        nedges = 0
        users = set()
        perms = set()
        for u in up:
            users.add(u)
            perms = perms.union(up[u])
            nedges += len(up[u])

        print('Total # users:', len(users))
        print('Total # perms:', len(perms))
        print('Total # edges:', nedges)
        sys.stdout.flush()

        time1 = time.time()
        # print('# roles to begin with:', nedges)
        nroles = get_nroles(up, users, perms, nedges)
        print('# roles:', nroles)

        m = gp.Model("minedgesLinearProg")
        m.setParam(GRB.Param.TimeLimit, timelimit)

        m = reduce_to_lp(up, users, perms, nroles, m)
        time2 = time.time()
        print('Time taken to reduce to ILP:', time2 - time1)
        sys.stdout.flush()
        run_model(m, filepath, filename)
        roles_as_edges = create_rbac(m)
        check_roles_and_fix(roles_as_edges, up)
        if check_roles(roles_as_edges, up):
            print('RBAC holds')
            print('RBAC: ')
            pprint(get_roles_mapped(roles_as_edges))
            num_edges = calculate_number_of_edges_in_rbac(roles_as_edges)
            print('# edges: ', num_edges)
            print('# roles: ', len(roles_as_edges))
            total_num_roles += len(roles_as_edges)
            total_num_edges += num_edges
        else:
            print('RBAC failed')
        # dual_model = convert_to_dual(m)
        # run_model(dual_model, filepath, 'dual_' + filename)
        time3 = time.time()
        print('Time taken to run model:', time3 - time2)
        sys.stdout.flush()

    print('Total # edges: ', total_num_edges)
    print('Total # roles: ', total_num_roles)


def create_rbac(m: gp.Model):
    # get roles as dict
    roles = dict()
    for var in json.loads(m.getJSONSolution())['Vars']:
        if var['VarName'].startswith('c_') and var['X'] > 0:
            role = var['VarName'][rindex(var['VarName'], '_'):]
            user = 'u_' + var['VarName'][var['VarName'].find('_') + 1: rindex(var['VarName'], '_') - 1]
            if role in roles:
                roles[role].add(user)
            else:
                roles[role] = {user}
        elif var['VarName'].startswith('d_') and var['X'] > 0:
            role = var['VarName'][rindex(var['VarName'], '_'):]
            perm = 'p_' + var['VarName'][var['VarName'].find('_') + 1: rindex(var['VarName'], '_') - 1]
            if role in roles:
                roles[role].add(perm)
            else:
                roles[role] = {perm}

    # get roles as edges
    roles_created_as_edges = get_roles_as_edges(roles)
    return roles_created_as_edges


if __name__ == '__main__':
    main()
