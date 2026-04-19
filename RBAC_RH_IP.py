import argparse
import os
import sys
from pprint import pprint

import gurobipy as gp
from gurobipy import GRB

prefix_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(f'{prefix_dir}/..')

import maxsetsbp
from readup import readup, uptopu


def r_is_assigned_p(r, p, m: gp.Model):
    p_r_p = m.addVar(name=f'p_{r}_{p}', vtype=GRB.BINARY)
    c_r_p = m.addVar(name=f'c_{r}_{p}', vtype=GRB.BINARY)
    m.update()
    p_r_p.LB = p_r_p.UB = 1
    c_r_p.LB = c_r_p.UB = 0
    # c_r_p.LB = c_r_p.UB = 1
    m.update()


def optimize_model(m: gp.Model):
    # m.feasRelaxS(0, False, False, True)

    m.optimize()
    roles = dict()
    if m.status == GRB.OPTIMAL:
        print(f"Objective value = {m.ObjVal}")

        for v in m.getVars():
            if v.X == 1 or v.X == 0:
                if v.VarName.startswith('u_') or v.VarName.startswith('r_') or v.VarName.startswith('p_') or v.VarName.startswith('c_'):
                    print(f"{v.VarName} = {v.X}")
            if v.X == 1:
                if v.VarName.startswith('u_'):
                    r = v.VarName.split('_')[-1]
                    u = v.VarName.split('_')[1]
                    if r not in roles:
                        roles[r] = {'roles': set(), 'users': set(), 'perms': set()}
                    roles[r]['users'].add(u)
                elif v.VarName.startswith('p_'):
                    r = v.VarName.split('_')[1]
                    p = v.VarName.split('_')[-1]
                    if r not in roles:
                        roles[r] = {'roles': set(), 'users': set(), 'perms': set()}
                    roles[r]['perms'].add(p)
                elif v.VarName.startswith('r_'):
                    r = v.VarName.split('_')[1]
                    r1 = v.VarName.split('_')[-1]
                    if r not in roles:
                        roles[r] = {'roles': set(), 'users': set(), 'perms': set()}
                    roles[r]['roles'].add(r1)
    elif m.status == GRB.INFEASIBLE:
        m.computeIIS()
        m.write("infeasible.ilp")

    print('Roles:')
    pprint(roles)


def rbac_to_rh_ip(up: dict, roles: dict):
    pu = uptopu(up)

    all_perms = set(pu.keys())
    m = gp.Model('RBAC_RH_IP')
    # print(roles)
    for r in roles:
        role = roles[r]
        r_perms = {e[1] for e in role}
        r_users = {e[0] for e in role}

        for p in r_perms:
            r_is_assigned_p(r, p, m)
        m.update()
        for p in all_perms.difference(r_perms):
            p_r_p = m.addVar(name=f'p_{r}_{p}', vtype=GRB.BINARY)
            c_r_p = m.addVar(name=f'c_{r}_{p}', vtype=GRB.BINARY)
            m.update()
            p_r_p.LB = p_r_p.UB = 0
            c_r_p.LB = c_r_p.UB = 0

    # create new roles
    # make these roles inherit from existing roles
    new_roles = []
    max_r = max(roles.keys())
    for i in range(len(roles)):
        r = i
        new_roles.append(r + max_r + 1)
    all_roles = list(roles.keys()) + new_roles
    for r in all_roles:
        # users can be assigned to any roles
        for u in up:
            if m.getVarByName(f'u_{u}_{r}') is None:
                # if r in new_roles:
                # u_u_r =  m.addVar(name=f'u_{u}_{r}', vtype=GRB.BINARY)
                u_u_r = m.addVar(name=f'u_{u}_{r}', vtype=GRB.CONTINUOUS)
                u_u_r.LB = 0
                u_u_r.UB = 1
                # only new roles can be assigned to user
                # if r in roles:
                #     u_u_r.LB = u_u_r.UB = 0
        for p in pu:
            if m.getVarByName(f'p_{r}_{p}') is None:
                # only existing roles can be directly assigned to a permission,
                # new roles have to inherit
                if r in new_roles:
                    # permission p is assigned role r
                    # p_r_p = m.addVar(name=f'p_{r}_{p}', vtype=GRB.BINARY)
                    p_r_p = m.addVar(name=f'p_{r}_{p}', vtype=GRB.CONTINUOUS)
                    p_r_p.LB = 0
                    p_r_p.UB = 1
                    # p_r_p.LB = p_r_p.UB = 0
            if m.getVarByName(f'c_{r}_{p}') is None:
                # permission p is inherited by role r from some other role r1
                if r in new_roles:
                    c_r_p = m.addVar(name=f'c_{r}_{p}', vtype=GRB.CONTINUOUS)
                    c_r_p.LB = 0
                    c_r_p.UB = 1
                # if r in roles:
                #     c_r_p.LB = c_r_p.UB = 0


    m.update()
    # for p in pu:
    #     # for r in new_roles:
    #     #     p_r_p = m.getVarByName(f'p_{r}_{p}')
    #     #     if p_r_p is not None:
    #     #         p_r_p.LB = p_r_p.UB = 0
    #     for r in roles:
    #         c_r_p = m.getVarByName(f'c_{r}_{p}')
    #         if c_r_p is not None:
    #             c_r_p.LB = c_r_p.UB = 0
    m.update()

    # new roles can be assigned to existing roles
    for r in new_roles:
        for r1 in roles:
            if r == r1:
                continue
            if m.getVarByName(f'r_{r}_{r1}') is None:
                # r_r_r1 = m.addVar(name=f'r_{r}_{r1}', vtype=GRB.BINARY)
                r_r_r1 = m.addVar(name=f'r_{r}_{r1}', vtype=GRB.CONTINUOUS)
                r_r_r1.LB = 0
                r_r_r1.UB = 1
    m.update()

    # constraint: every new role inherits from at least 2 existing roles
    # for r in new_roles:
    #     constr_expr = gp.LinExpr()
    #     for r1 in roles:
    #         r_r_r1 = m.getVarByName(name=f'r_{r}_{r1}')
    #         constr_expr += r_r_r1
    #     # m.addConstr(constr_expr >= 2, name=f'r_{r}_has_atleast_r1s')
    #     m.update()


    # constraint: Is role r inheriting permission p from role r1
    for r in new_roles:
        for p in pu:
            constr_expr = gp.LinExpr()
            for r1 in roles:
                if r == r1:
                    continue
                # get role r is assigned to role r1 variable
                r_r_r1 = m.getVarByName(name=f'r_{r}_{r1}')
                # get role r1 is assigned to permission p variable
                c_r1_p = m.getVarByName(name=f'c_{r1}_{p}')
                # Is role r1 assigned to permission p directly
                p_r1_p = m.getVarByName(name=f'p_{r1}_{p}')

                constr_expr += (r_r_r1 * (c_r1_p + p_r1_p))
            c_r_p = m.getVarByName(name=f'c_{r}_{p}')
            m.addConstr(c_r_p == constr_expr, name=f'r_{r}_inherits_p_{p}')
            m.update()

    # for r in new_roles:
    #     for p in pu:
    #         constr_expr = gp.LinExpr()
    #         for r1 in roles:
    #             if r == r1:
    #                 continue
    #             r_r_r1 = m.getVarByName(name=f'r_{r}_{r1}')
    #             c_r1_p = m.getVarByName(name=f'c_{r1}_{p}')
    #             p_r1_p = m.getVarByName(name=f'p_{r1}_{p}')
    #
    #             y = m.addVar(vtype=GRB.BINARY, name=f'y_{r}_{r1}_{p}')
    #             m.addConstr(y <= r_r_r1, name=f'y1_{r}_{r1}_{p}')
    #             m.addConstr(y <= p_r1_p + c_r1_p, name=f'y2_{r}_{r1}_{p}')
    #             m.addConstr(y >= r_r_r1 + p_r1_p + c_r1_p - 1, name=f'y3_{r}_{r1}_{p}')
    #             constr_expr += y
    #
    #         c_r_p = m.getVarByName(name=f'c_{r}_{p}')
    #         m.addConstr(c_r_p == constr_expr, name=f'r_{r}_inherits_p_{p}')
    #         m.update()

    # constraint: each role r either inherits permission p or is assigned directly, but not both
    for r in new_roles:
        for p in pu:
            c_r_p = m.getVarByName(name=f'c_{r}_{p}')
            p_r_p = m.getVarByName(name=f'p_{r}_{p}')
    m.addConstr(c_r_p + p_r_p <= 1, name=f'r_{r}_inherits_p_{p}')
    m.addConstr(c_r_p <= 1, name=f'r_{r}_inherits_p_{p}')
    m.update()

    for r in roles:
        for p in pu:
            c_r_p = m.getVarByName(name=f'c_{r}_{p}')
            p_r_p = m.getVarByName(name=f'p_{r}_{p}')
            m.addConstr(c_r_p + p_r_p <= 1, name=f'r_{r}_direct_p_{p}')
    m.update()

    # constraint: no two roles are assigned same permissions
    for p in pu:
        for r in new_roles:
            # diff_vars = []
            c_r_p = m.getVarByName(f'c_{r}_{p}')
            p_r_p = m.getVarByName(f'p_{r}_{p}')

            rp = m.addVar(vtype=GRB.CONTINUOUS, name=f'new_role_{r}_has_p_{p}')
            rp.LB = 0
            rp.UB = 1
            m.addConstr(rp == c_r_p + p_r_p, name=f'new_role_{r}_has_p_{p}')
            # print(f'adding new role: {r}, permission: {p}')

        m.update()

        for r1 in roles:
            c_r1_p = m.getVarByName(f'c_{r1}_{p}')
            p_r1_p = m.getVarByName(f'p_{r1}_{p}')
            r1p = m.addVar(vtype=GRB.CONTINUOUS, name=f'existing_role_{r1}_has_p_{p}')
            r1p.LB = 0
            r1p.UB = 1
            m.addConstr(r1p == c_r1_p + p_r1_p, name=f'existing_role_{r1}_has_p_{p}')
            # print(f'adding existing role: {r1}, permission: {p}')

        m.update()

    for r1 in roles:
        diff_vars = []
        for r in new_roles:
            if r != r1:
                for p in pu:
                    # r1, r1p = existing_r_has_p_dict[p]
                    r1p = m.getVarByName(f'existing_role_{r1}_has_p_{p}')
                    rp = m.getVarByName(f'new_role_{r}_has_p_{p}')

                    d = m.addVar(vtype=GRB.CONTINUOUS, name=f'diff_r_{r}_r1_{r1}_p_{p}')
                    d.LB = 0
                    d.UB = 1
                    # print(f'existing role: {r1}, new role: {r}, permission: {p}')
                    m.addConstr(d == (1 - r1p) * rp + (1 - rp) * r1p, name=f'only_one_r_{r}_r1_{r1}_has_p_{p}')
                    diff_vars.append(d)
                m.addConstr(gp.quicksum(diff_vars) >= 1, name=f'unique_rp_r_{r}_r1_{r1}')


            # if r != r1:
            #     # continue
            #     # diff_vars = []
            #     for p in pu:
            #         c_r_p = m.getVarByName(f'c_{r}_{p}')
            #         p_r_p = m.getVarByName(f'p_{r}_{p}')
            #         c_r1_p = m.getVarByName(f'c_{r1}_{p}')
            #         p_r1_p = m.getVarByName(f'p_{r1}_{p}')
            #         # either r inherits permission p or is assigned permission p
            #         # r_p = c_r_p + p_r_p
            #         # either r1 inherits permission p or is assigned permission p
            #         # r1_p = c_r1_p + p_r1_p
            #         d = m.addVar(vtype=GRB.BINARY, name=f'diff_r_{r}_r1_{r1}_p_{p}')
            #         rp = m.addVar(vtype=GRB.BINARY, name=f'role_{r}_has_p_{p}')
            #         r1p = m.addVar(vtype=GRB.BINARY, name=f'role1_{r1}_has_p_{p}')
            #         m.addConstr(rp == c_r_p + p_r_p, name=f'role_{r}_has_p_{p}')
            #         m.addConstr(r1p == c_r1_p + p_r1_p, name=f'role1_{r1}_has_p_{p}')
            #         m.addConstr(d == (1 - r1p) * rp + (1 - rp) * r1p, name=f'only_one_r_{r}_r1_{r1}_has_p_{p}')
            #
            #         diff_vars.append(d)
            #         m.update()
            #     # at least one of the permissions between roles r and r1 is different
            #
            #     m.addConstr(gp.quicksum(diff_vars) >= 1, name=f'unique_rp_r_{r}_r1_{r1}')
    m.update()

    # constraint: If user u is assigned to permission p, then there exists a role r to which both user u is assigned
    # directly and permission p is either directly assigned or it inherits from another role r1
    for u in up:
        for p in up[u]:
            constr_expr = gp.LinExpr()
            for r in new_roles:
            # for r in all_roles:
                u_u_r = m.getVarByName(name=f'u_{u}_{r}')
                p_r_p = m.getVarByName(name=f'p_{r}_{p}')
                c_r_p = m.getVarByName(name=f'c_{r}_{p}')

                constr_expr += u_u_r * (p_r_p + c_r_p)
                # constr_expr += u_u_r * (c_r_p)
            m.addConstr(constr_expr >= 1, name=f'u_{u}_has_p_{p}')
            m.update()

    # constraint: If user u is NOT assigned to permission p, then there exists no role r to which both user u is
    # assigned and permission p is either assigned directly or it inherits from another role r1
    for u in up:
        perms_not_in_u = set(pu.keys()).difference(up[u])
        for p in perms_not_in_u:
            # if p in up[u]:
            #     continue
            constr_expr = gp.LinExpr()
            for r in new_roles:
            # for r in all_roles:
                u_u_r = m.getVarByName(name=f'u_{u}_{r}')
                p_r_p = m.getVarByName(name=f'p_{r}_{p}')
                c_r_p = m.getVarByName(name=f'c_{r}_{p}')

                constr_expr += u_u_r * (p_r_p + c_r_p)
            m.addConstr(constr_expr <= 0, name=f'u_{u}_not_have_p_{p}')
            # m.addConstr(constr_expr == 0, name=f'u_{u}_not_have_p_{p}')
            m.update()

    # constraint: role r cannot be assigned to role r1 and r1 assigned to r at the same time
    # for r in new_roles:
    #     for r1 in roles:
    #         if r == r1:
    #             continue
    #         r_r_r1 = m.getVarByName(name=f'r_{r}_{r1}')
    #         r_r1_r = m.getVarByName(name=f'r_{r1}_{r}')
    #         m.addConstr(r_r_r1 + r_r1_r <= 1, name=f'r_{r}_r1_{r1}_no_cycle')

    # constraint: every role r is either assigned to a user u or a permission p or another role r1
    # new roles are assigned to users and existing roles
    for r in new_roles:
        # new roles assigned to a user
        incoming_constr_expr = gp.LinExpr()
        outgoing_constr_expr = gp.LinExpr()
        # role r is assigned to user u
        for u in up:
            u_u_r = m.getVarByName(f'u_{u}_{r}')
            incoming_constr_expr += u_u_r

        # new roles are only allowed to connect to existing roles
        for r1 in roles:
            if r == r1:
                continue
            # role r is assigned to role r1
            r_r_r1 = m.getVarByName(f'r_{r}_{r1}')
            outgoing_constr_expr += r_r_r1

        # both incoming constraint and outgoing constraint must hold
        # m.addConstr(incoming_constr_expr >= 1, f'r_{r}_assigned_in')
        # m.addConstr(outgoing_constr_expr >= 1, f'r_{r}_assigned_out')

    # existing roles are assigned to permissions and new roles
    for r in roles:
        # roles assigned to a permission
        incoming_constr_expr = gp.LinExpr()
        outgoing_constr_expr = gp.LinExpr()
        # role r is assigned to permission p
        for p in pu:
            p_r_p = m.getVarByName(f'p_{r}_{p}')
            outgoing_constr_expr += p_r_p

        # new roles are only allowed to connect to existing roles
        for r1 in new_roles:
            if r == r1:
                continue
            # role r1 is assigned to role r
            r_r1_r = m.getVarByName(f'r_{r1}_{r}')
            incoming_constr_expr += r_r1_r

        # both incoming constraint and outgoing constraint must hold
        # m.addConstr(incoming_constr_expr >= 1, f'r_{r}_assigned_in')
        # m.addConstr(outgoing_constr_expr >= 1, f'r_{r}_assigned_out')
    m.update()

    # objective
    obj = gp.LinExpr()
    for r in new_roles:
        # for u in up:
        #     u_u_r = m.getVarByName(name=f'u_{u}_{r}')
        #     if r in new_roles:
        #         obj += u_u_r
        #     elif r in roles:
        #         obj -= u_u_r
        for p in pu:
            p_r_p = m.getVarByName(name=f'p_{r}_{p}')
            c_r_p = m.getVarByName(name=f'c_{r}_{p}')
            obj -= p_r_p
            obj += c_r_p
    for r in new_roles:
        for r1 in roles:
            if r == r1:
                continue
            r_r_r1 = m.getVarByName(name=f'r_{r}_{r1}')
            obj += r_r_r1

    # Minimize the # edges
    m.setObjective(obj, GRB.MAXIMIZE)
    m.update()
    m.write("rbac_rh_model.lp")
    optimize_model(m)
    pass


def main():
    parser = argparse.ArgumentParser(description="Read input UP file -> generate a min role RBAC policy -> generate "
                                                 "Integer Program for the RH problem")
    parser.add_argument("input_file", type=str, help="Input UP file")

    args = parser.parse_args()
    up = readup(args.input_file)
    num_roles, roles = maxsetsbp.run(args.input_file)
    roles_dict = dict()
    for r in range(len(roles)):
        roles_dict[r] = roles[r]
    # roles = {
    #     0: {(0,0), (0,1), (2,0), (2,1), (3,0), (3,1)},
    #     1: {(2,4), (3,4), (4,4)},
    #     2: {(0,0), (0,2), (1,0), (1,2), (2,0), (2,2)},
    #     3: {(1,3), (4,3)},
    # }
    pprint(roles)
    rbac_to_rh_ip(up, roles_dict)




if __name__ == "__main__":
    main()
