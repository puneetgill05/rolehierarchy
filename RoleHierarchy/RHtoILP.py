import argparse
from itertools import combinations
from pprint import pprint

import gurobipy as gp
from gurobipy import GRB

from minedgerolemining.readup import uptopu, readup


def create_u_assigned_r(users: set, perms: set, roles: set, m: gp.Model):
    for r in roles:
        # user u is assigned to role r
        for u in users:
            m.addVar(name=f'u_{u}_{r}', vtype=GRB.BINARY)
    m.update()


def create_r_assigned_p(users: set, perms: set, roles: set, m: gp.Model):
    for r in roles:
        for p in perms:
            # permission p is assigned role r
            m.addVar(name=f'p_{r}_{p}', vtype=GRB.BINARY)
            # permission p is inherited by role r from some other role r1
            # m.addVar(name=f'c_{r}_{p}', vtype=GRB.BINARY)


def create_r_inherits_p(users: set, perms: set, roles: set, m: gp.Model):
    for r in roles:
        for p in perms:
            # permission p is inherited by role r from some other role r1
            m.addVar(name=f'c_{r}_{p}', vtype=GRB.BINARY)


def create_r_inherits_r1(roles: set, r1_roles: set, m: gp.Model):
    # role r is assigned to role r1
    for r in roles:
        for r1 in r1_roles:
            if r1 != r:
                m.addVar(name='r_' + str(r) + '_' + str(r1), vtype=GRB.BINARY)
    m.update()


# optimize for the number of levels: maximize the number of levels
# optimize for the number of roles
def rh_to_ilp(up: dict):
    pu = uptopu(up)

    nu = len(up.keys())
    np = len(pu.keys())
    nr = min(nu, np)

    env = gp.Env(empty=True)
    env.setParam("OutputFlag", 0)
    env.start()
    m = gp.Model("role_hierarchy", env=env)

    print('Adding variables and objective...', end='')

    # role_pairs = set()
    for r in range(nr):
        # user u is assigned to role r
        for u in up:
            m.addVar(name=f'u_{u}_{r}', vtype=GRB.BINARY)
        for p in pu:
            # permission p is assigned role r
            m.addVar(name=f'p_{r}_{p}', vtype=GRB.BINARY)
            # permission p is inherited by role r from some other role r1
            m.addVar(name=f'c_{r}_{p}', vtype=GRB.BINARY)

        # role r is assigned to role r1
        for r1 in range(nr):
            if r1 != r:
                m.addVar(name='r_' + str(r) + '_' + str(r1), vtype=GRB.BINARY)
                # m.update()
                # role_pairs.add((r, r1))
    m.update()

    # constraint: Is role r inheriting permission p from role r1
    for r in range(nr):
        for p in pu:
            constr_expr = gp.LinExpr()
            for r1 in range(nr):
                if r == r1:
                    continue
                # get role r is assigned to role r1 variable
                r_r_r1 = m.getVarByName(name=f'r_{r}_{r1}')
                # get role r1 is assigned to permission p variable
                c_r1_p = m.getVarByName(name=f'c_{r1}_{p}')
                # Is role r1 assigned to permission p directly
                p_r1_p = m.getVarByName(name=f'p_{r1}_{p}')

                # role r is assigned to role r1 AND either role r1 is directly assigned to permission p or it
                # inherits from some other role
                # constr = r_r_r1 * (p_r1_p + c_r1_p)
                # Auxiliary variables for the products
                # z1 = m.addVar(vtype=GRB.BINARY, name=f'z1_{r}_{r1}_{p}')  # r_r_r1 * p_r1_p
                # z2 = m.addVar(vtype=GRB.BINARY, name=f'z2_{r}_{r1}_{p}')  # r_r_r1 * c_r1_p

                # Linearize z1 = r_r_r1 * p_r1_p
                # m.addConstr(z1 <= r_r_r1, name=f'z1_le_r_{r}_{r1}_{p}')
                # m.addConstr(z1 <= p_r1_p, name=f'z1_le_p_{r}_{r1}_{p}')
                # m.addConstr(z1 >= r_r_r1 + p_r1_p - 1, name=f'z1_ge_sum_{r}_{r1}_{p}')

                # Linearize z2 = r_r_r1 * c_r1_p
                # m.addConstr(z2 <= r_r_r1, name=f'z2_le_r_{r}_{r1}_{p}')
                # m.addConstr(z2 <= c_r1_p, name=f'z2_le_c_{r}_{r1}_{p}')
                # m.addConstr(z2 >= r_r_r1 + c_r1_p - 1, name=f'z2_ge_sum_{r}_{r1}_{p}')

                # constr_expr += z1 + z2
                constr_expr += (r_r_r1 * (c_r1_p + p_r1_p))
            c_r_p = m.getVarByName(name=f'c_{r}_{p}')
            m.addConstr(c_r_p == constr_expr, name=f'r_{r}_inherits_p_{p}')
            m.update()

    # constraint: each role r either inherits permission p or is assigned directly, but not both
    for r in range(nr):
        for p in pu:
            c_r_p = m.getVarByName(name=f'c_{r}_{p}')
            p_r_p = m.getVarByName(name=f'p_{r}_{p}')
            m.addConstr(c_r_p + p_r_p <= 1, name=f'r_{r}_either_inherits_or_direct_p_{p}')
    m.update()

    # constraint: If user u is assigned to permission p, then there exists a role r to which both user u is assigned
    # directly and permission p is either directly assigned or it inherits from another role r1
    for u in up:
        for p in up[u]:
            constr_expr = gp.LinExpr()
            for r in range(nr):
                u_u_r = m.getVarByName(name=f'u_{u}_{r}')
                p_r_p = m.getVarByName(name=f'p_{r}_{p}')
                c_r_p = m.getVarByName(name=f'c_{r}_{p}')

                constr_expr += u_u_r * (p_r_p + c_r_p)
            m.addConstr(constr_expr >= 1, name=f'u_{u}_has_p_{p}')
            m.update()

    # constraint: If user u is NOT assigned to permission p, then there exists no role r to which both user u is
    # assigned and permission p is either assigned directly or it inherits from another role r1
    for u in up:
        for p in pu:
            if p in up[u]:
                continue
            constr_expr = gp.LinExpr()
            for r in range(nr):
                u_u_r = m.getVarByName(name=f'u_{u}_{r}')
                p_r_p = m.getVarByName(name=f'p_{r}_{p}')
                c_r_p = m.getVarByName(name=f'c_{r}_{p}')

                constr_expr += u_u_r * (p_r_p + c_r_p)
            m.addConstr(constr_expr <= 0, name=f'u_{u}_not_have_p_{p}')
            m.update()

    # constraint: role r cannot be assigned to role r1 and r1 assigned to r at the same time
    for r in range(nr):
        for r1 in range(nr):
            if r == r1:
                continue
            r_r_r1 = m.getVarByName(name=f'r_{r}_{r1}')
            r_r1_r = m.getVarByName(name=f'r_{r1}_{r}')
            m.addConstr(r_r_r1 + r_r1_r <= 1, name=f'r_{r}_r1_{r1}_no_cycle')

    # constraint: every role r is either assigned to a user u or a permission p or another role r1
    for r in range(nr):
        # either assigned to user
        incoming_constr_expr = gp.LinExpr()
        outgoing_constr_expr = gp.LinExpr()
        for u in up:
            u_u_r = m.getVarByName(f'u_{u}_{r}')
            incoming_constr_expr += u_u_r
        for r1 in range(nr):
            if r == r1:
                continue
            r_r1_r = m.getVarByName(f'r_{r1}_{r}')
            incoming_constr_expr += r_r1_r
            r_r_r1 = m.getVarByName(f'r_{r}_{r1}')
            outgoing_constr_expr += r_r_r1
        for p in pu:
            p_r_p = m.getVarByName(f'p_{r}_{p}')
            outgoing_constr_expr += p_r_p
        # both incoming constraint and outgoing constraint must hold
        m.addConstr(incoming_constr_expr >= 1, f'r_{r}_assigned_in')
        m.addConstr(outgoing_constr_expr >= 1, f'r_{r}_assigned_out')

    m.update()

    # objective
    obj = gp.LinExpr()
    for r in range(nr):
        # for u in up:
        #     u_u_r = m.getVarByName(name=f'u_{u}_{r}')
        #     obj += u_u_r
        # for p in pu:
        #     p_r_p = m.getVarByName(name=f'p_{r}_{p}')
        #     obj += p_r_p
        for r1 in range(nr):
            if r == r1:
                continue
            r_r_r1 = m.getVarByName(name=f'r_{r}_{r1}')
            obj += r_r_r1

    # Minimize the # edges
    m.setObjective(obj, GRB.MAXIMIZE)
    m.update()
    m.write("model.lp")

    m.optimize()

    roles = dict()
    if m.status == GRB.OPTIMAL:
        print(f"Objective value = {m.ObjVal}")

        for v in m.getVars():
            if v.X == 1:
                print(f"{v.VarName} = {v.X}")
                if v.VarName.startswith('u'):
                    r = v.VarName.split('_')[-1]
                    u = v.VarName.split('_')[1]
                    if r not in roles:
                        roles[r] = {'roles': set(), 'users': set(), 'perms': set()}
                    roles[r]['users'].add(u)
                elif v.VarName.startswith('p'):
                    r = v.VarName.split('_')[1]
                    p = v.VarName.split('_')[-1]
                    if r not in roles:
                        roles[r] = {'roles': set(), 'users': set(), 'perms': set()}
                    roles[r]['perms'].add(p)
                elif v.VarName.startswith('r'):
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


def main():
    parser = argparse.ArgumentParser(description="Read input UP file and generate Integer Program for the RH problem")
    parser.add_argument("input_file", type=str, help="Input UP file")

    args = parser.parse_args()
    up = readup(args.input_file)
    rh_to_ilp(up)


if __name__ == "__main__":
    main()
