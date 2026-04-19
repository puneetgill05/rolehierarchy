#!/usr/bin/env python3

import argparse
import copy
import itertools
import json
import os
import sys
import time
from itertools import combinations
from pprint import pprint

import gurobipy as gp
import networkx as nx
from colorama import Fore
from gurobipy import GRB
from matplotlib import pyplot as plt

prefix_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(f'{prefix_dir}/..')
sys.path.append(f'{prefix_dir}/../..')

from algorithms import BicliqueCoverToILP
import maxsetsbp
from greedythenlattice_greedy_only import run
import greedythenlattice_greedy
from RoleHierarchy import RBAC_to_RH

from minedgerolemining.minedgefromminrole import minrole_to_minedge
from minedgerolemining.removedominators import readem
from readup import readup, uptopu, readup_and_usermap_permmap

from RBAC_to_RH import check_RH, get_metrics, roles_edges_to_dict, reconstruct_roles_from_RH, rbac_edges_to_dict, \
    roles_dict_to_edges
from graph_dict import dict_to_networkx, networkx_to_html_with_zoom


def optimize_model(m: gp.Model):
    m.optimize()
    roles = dict()
    if m.status == GRB.OPTIMAL:
        print(f"Objective value = {m.ObjVal}")

        for v in m.getVars():
            if v.X == 1 or v.X == 0:
                if v.VarName.startswith('u_') or v.VarName.startswith('r_') or v.VarName.startswith(
                        'p_') or v.VarName.startswith('c_'):
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

    # print('Roles:')
    # pprint(roles)


def rbac_to_rh_ip_v2(up: dict, existing_roles: dict):
    pu = uptopu(up)

    all_perms = set(pu.keys())
    m = gp.Model('RBAC_RH_IP')
    # print(roles)
    perm_roles_map = dict()

    for r in existing_roles:
        role = existing_roles[r]
        r_perms = {e[1] for e in role}
        r_users = {e[0] for e in role}

        for p in r_perms:
            p_r_p = m.addVar(name=f'p_{r}_{p}', vtype=GRB.BINARY)
            p_r_p.LB = p_r_p.UB = 1
            m.update()
            if p not in perm_roles_map:
                perm_roles_map[p] = set()
            perm_roles_map[p].add((r, p_r_p))

    new_roles = []
    max_r = max(existing_roles.keys())
    for i in range(len(existing_roles)):
        r = i
        new_roles.append(r + max_r + 1)
    all_roles = list(existing_roles.keys()) + new_roles

    for u in up:
        for new_r in new_roles:
            u_u_r = m.addVar(name=f'u_{u}_{new_r}', vtype=GRB.BINARY)

    for new_r in new_roles:
        for existing_r in existing_roles:
            r_nr_er = m.addVar(name=f'r_{new_r}_{existing_r}', vtype=GRB.BINARY)

    m.update()

    # constraint: If user u is assigned to permission p, then there exists a role r to which both user u is assigned
    # directly and permission p is either directly assigned or it inherits from another role r1
    for u in up:
        for p in up[u]:
            candidate_roles = perm_roles_map[p]
            constr_expr = gp.LinExpr()
            for new_r in new_roles:
                # for r in all_roles:
                u_u_nr = m.getVarByName(name=f'u_{u}_{new_r}')
                for existing_r, existing_r_var in candidate_roles:
                    p_er_p = existing_r_var
                    r_nr_er = m.getVarByName(name=f'r_{new_r}_{existing_r}')

                    # c_r_p = m.getVarByName(name=f'c_{r}_{p}')
                    constr_expr += u_u_nr * p_er_p
                    # constr_expr += r_nr_er
                    m.addConstr(r_nr_er == u_u_nr * p_er_p, name=f'r_{new_r}_has_{existing_r}_u_{u}_has_p_{p}')

                # constr_expr += u_u_r * (c_r_p)
            m.addConstr(constr_expr >= 1, name=f'u_{u}_has_p_{p}')
            m.update()

    # constraint: If user u is NOT assigned to permission p, then there exists no role r to which both user u is
    # assigned and permission p is either assigned directly or it inherits from another role r1
    for u in up:
        perms_not_in_u = set(pu.keys()).difference(up[u])
        for p in perms_not_in_u:
            constr_expr = gp.LinExpr()
            for new_r in new_roles:
                u_u_nr = m.getVarByName(name=f'u_{u}_{new_r}')
                candidate_roles = perm_roles_map[p]
                for existing_r, existing_r_var in candidate_roles:
                    r_nr_er = m.getVarByName(name=f'r_{new_r}_{existing_r}')

                    p_er_p = existing_r_var
                    constr_expr += u_u_nr * p_er_p
                    # m.addConstr(u_u_nr * p_er_p <= 0, name=f'r_{new_r}_not_have_{existing_r}_u_{u}_not_have_p_{p}')
                    # m.addConstr(u_u_nr * p_er_p <= 0, name=f'r_{new_r}_not_have_{existing_r}_u_{u}_not_have_p_{p}')
                    # m.addConstr(r_nr_er <= 0, name=f'r_{new_r}_not_have_{existing_r}_u_{u}_has_p_{p}')

                    # constr_expr += u_u_nr * p_er_p
                    # constr_expr += r_nr_er
            m.addConstr(constr_expr <= 0, name=f'u_{u}_not_have_p_{p}')
            # m.addConstr(constr_expr == 0, name=f'u_{u}_not_have_p_{p}')
            m.update()

    m.write("rbac_rh_model_v2.lp")

    optimize_model(m)


def is_cover(subsets, universe):
    covered = set()
    for s in subsets:
        covered |= s
    return covered == universe


# get the smallest set of roles that cover all the permissions in the universe
def brute_force_set_cover(universe, sets):
    n = len(sets)
    best_cover = None

    for r in range(1, n + 1):  # Try all sizes of combinations
        for subset_indices in combinations(range(n), r):
            selected_sets = [sets[i] for i in subset_indices]
            if is_cover(selected_sets, universe):
                best_cover = selected_sets
                return best_cover  # Return the first minimal cover found

    return None  # No cover found


# given a cover and set of roles, get a subset of roles that cover the permissions
def get_corresponding_roles(role_dict: dict, cover: list):
    roles_assigned = set()
    for subset in cover:
        for r in role_dict:
            r_perms = {e[1] for e in role_dict[r]}
            if r_perms == subset:
                roles_assigned.add(r)
    return roles_assigned


def subsets_bicliques_brute(up: dict, roles_dict: dict):
    # U = set([1, 2, 3, 4])
    # S = [set([1, 2]), set([2, 3]), set([3, 4]), set([4])]

    role_perms = []
    for r in roles_dict:
        r_perms = {e[1] for e in roles_dict[r]}
        role_perms.append(r_perms)
    # print('--------------------------')

    ctr_new_role = max(roles_dict.keys()) + 1
    new_roles = dict()

    for u in up:
        perms = up[u]

        cover = brute_force_set_cover(up[u], role_perms)
        if cover and len(cover) > 1:
            # print(f'U: {u}, perms: {perms}')
            roles_assigned = get_corresponding_roles(roles_dict, cover)
            # print('Roles assigned: ', roles_assigned)
            for r_assigned in roles_assigned:
                r_assigned_perms = {e[1] for e in roles_dict[r_assigned]}
                # print(f'Perms of {r_assigned} : {r_assigned_perms}')
                if ctr_new_role not in new_roles:
                    new_roles[ctr_new_role] = {
                        'roles': set(),
                        'users': set(),
                        'perms': set()
                    }
                new_roles[ctr_new_role]['roles'].add(r_assigned)
            new_roles[ctr_new_role]['users'].add(u)
            ctr_new_role += 1
            # print('--------------------------')
        else:
            # print("No set cover exists")
            continue
    # print('New roles:')
    # pprint(new_roles)

    updated_roles = eliminate_roles(new_roles)
    # print('Updated roles:')
    # pprint(updated_roles)

    print(f'# new roles: {len(new_roles)}')
    print(f'# updated roles: {len(updated_roles)}')
    print('==========================================')
    print('==========================================')
    return updated_roles


# If there exists a role that can be covered by other roles, remove such role and reassign the users to the roles that cover it
def eliminate_roles(new_roles: dict):
    updated_roles = new_roles.copy()
    roles_to_remove = set()
    for nr in new_roles:
        # if 'roles' not in new_roles[nr]:
        #     print('No roles found')
        if len(new_roles[nr]['roles']) == 1:
            roles_to_remove.add(nr)
        if len(new_roles[nr]['roles']) > 2:
            roles_covered = set()
            roles_used_by_nr = set()
            for nr1 in new_roles:
                if nr1 != nr:
                    if new_roles[nr1]['roles'].issubset(new_roles[nr]['roles']) and nr1 not in roles_to_remove:
                        roles_covered.update(new_roles[nr1]['roles'])
                        roles_used_by_nr.add(nr1)
            if roles_covered == new_roles[nr]['roles']:
                for nr1 in roles_used_by_nr:
                    roles_to_remove.add(nr)
                    updated_roles[nr1]['users'].update(new_roles[nr]['users'])

    for nr in roles_to_remove:
        if nr in updated_roles:
            updated_roles.pop(nr)
    print('Eliminated roles:', set(new_roles.keys()).difference(set(updated_roles.keys())))
    return updated_roles


def remove_redundant_roles(RH: dict):
    recon_roles = reconstruct_roles_from_RH(RH)

    duplicate_roles = dict()
    dups = set()
    for r1 in recon_roles:
        for r2 in recon_roles:
            if r1 != r2 and recon_roles[r1] == recon_roles[r2] and r1 not in dups:
                if r1 not in duplicate_roles:
                    duplicate_roles[r1] = set()
                duplicate_roles[r1].add(r2)
                dups.add(r2)
    print(f'Duplicate roles: {duplicate_roles}')

    inv_duplicate_roles = {v: k for k, vals in duplicate_roles.items() for v in vals}
    print(f'Inverse Duplicate roles: {inv_duplicate_roles}')

    for r in duplicate_roles:
        for dup in duplicate_roles[r]:
            if dup in RH:
                RH.pop(dup)

    for r1 in RH:
        for r2 in RH[r1]:
            if isinstance(r2, int) and r2 in inv_duplicate_roles:
                RH[r1].remove(r2)
                RH[r1].add(inv_duplicate_roles[r2])

    return RH


def subsets_bicliques_ILP_OLD(up: dict, roles_dict: dict):
    role_perms = dict()
    for r_assigned in roles_dict:
        r_perms = {e[1] for e in roles_dict[r_assigned]}
        role_perms[r_assigned] = r_perms
    # print('--------------------------')

    ctr_new_role = max(roles_dict.keys()) + 1
    new_roles = dict()
    role_subsets_considered = dict()

    new_role_ctrs = set()
    for u in up:
        perms = up[u]

        roles_assigned_orig = solve_set_cover_ilp(perms, role_perms)
        roles_assigned_combs = list(itertools.combinations(roles_assigned_orig, 2))
        # roles_assigned_combs = [tuple(roles_assigned_orig)]

        roles_assigned_needed = set()
        for comb in roles_assigned_combs:
            if roles_assigned_needed.union(comb) == set(roles_assigned_orig):
                if comb not in roles_assigned_needed:
                    roles_assigned_needed.add(comb)
                break
            else:
                roles_needed = set()
                for r in roles_assigned_needed:
                    roles_needed.add(r[0])
                    roles_needed.add(r[1])
                if set(comb).issubset(roles_needed):
                    continue
                else:
                    if len(roles_assigned_orig) % 2 == 0:
                        shared_roles = roles_needed.intersection(set(comb))
                        if len(shared_roles) == 0:
                            roles_assigned_needed.add(comb)
                    else:
                        roles_assigned_needed.add(comb)

        # print('Roles Assigned Original:')
        # pprint(roles_assigned_orig)
        # print('Roles Needed:')
        # pprint(roles_assigned_needed)

        for roles_assigned in roles_assigned_needed:
            if roles_assigned and len(roles_assigned) > 1:
                if ctr_new_role not in new_roles and roles_assigned not in role_subsets_considered:
                    new_roles[ctr_new_role] = {
                        'roles': set(),
                        'users': set(),
                        'perms': set()
                    }
                    role_subsets_considered[roles_assigned] = ctr_new_role
                ctr_new_role = role_subsets_considered[roles_assigned]

                new_roles[ctr_new_role]['roles'] = new_roles[ctr_new_role]['roles'].union(roles_assigned)
                new_roles[ctr_new_role]['users'].add(u)
                new_role_ctrs.add(ctr_new_role)
                ctr_new_role = max(new_role_ctrs) + 1
                # perms_in_cover = {roles_dict[r][1] for r in roles_dict}

                perms_in_cover = []
                for r_assigned in roles_assigned:
                    r_perms = {e[1] for e in roles_dict[r_assigned]}
                    perms_in_cover.append(r_perms)

                # print('--------------------------')
            else:
                # print("No set cover exists")
                continue

    updated_roles = eliminate_roles(new_roles)
    # print('Updated roles:')
    # pprint(updated_roles)

    print(f'# updated roles: {len(updated_roles)}')
    print('==========================================')
    print('==========================================')
    return updated_roles


def create_new_roles(u, roles_assigned_in_round, new_roles: dict, roles_dict: dict, role_subsets_considered: dict,
                     new_role_ctrs: set, ctr_new_role: int):
    roles_assigned_combs = list(itertools.combinations(roles_assigned_in_round, 2))
    # roles_assigned_combs = [tuple(roles_assigned_orig)]

    roles_assigned_needed = set()
    for comb in roles_assigned_combs:
        if roles_assigned_needed.union(comb) == set(roles_assigned_in_round):
            if comb not in roles_assigned_needed:
                roles_assigned_needed.add(comb)
            break
        else:
            roles_needed = set()
            for r in roles_assigned_needed:
                roles_needed.add(r[0])
                roles_needed.add(r[1])
            if set(comb).issubset(roles_needed):
                continue
            else:
                if len(roles_assigned_in_round) % 2 == 0:
                    shared_roles = roles_needed.intersection(set(comb))
                    if len(shared_roles) == 0:
                        roles_assigned_needed.add(comb)
                else:
                    roles_assigned_needed.add(comb)

    # print('Roles Assigned in this round:')
    # pprint(roles_assigned_in_round)
    # print('Roles Needed:')
    # pprint(roles_assigned_needed)

    for roles_assigned in roles_assigned_needed:
        if roles_assigned and len(roles_assigned) > 1:
            if ctr_new_role not in new_roles and roles_assigned not in role_subsets_considered:
                new_roles[ctr_new_role] = {
                    'roles': set(),
                    'users': set(),
                    'perms': set()
                }
                role_subsets_considered[roles_assigned] = ctr_new_role
            ctr_new_role = role_subsets_considered[roles_assigned]

            new_roles[ctr_new_role]['roles'] = new_roles[ctr_new_role]['roles'].union(roles_assigned)
            new_roles[ctr_new_role]['users'].add(u)
            new_role_ctrs.add(ctr_new_role)
            ctr_new_role = max(new_role_ctrs) + 1
            # perms_in_cover = {roles_dict[r][1] for r in roles_dict}

            perms_in_cover = []
            for r_assigned in roles_assigned:
                r_perms = {e[1] for e in roles_dict[r_assigned]}
                perms_in_cover.append(r_perms)

            # print('--------------------------')
        else:
            # print("No set cover exists")
            continue
    # roles_assigned_orig = roles_assigned_orig - roles_assigned_in_round
    return new_roles


def subsets_bicliques_ILP(up: dict, roles_dict: dict):
    role_perms = dict()
    for r_assigned in roles_dict:
        r_perms = {e[1] for e in roles_dict[r_assigned]}
        role_perms[r_assigned] = r_perms

    ctr_new_role = max(roles_dict.keys()) + 1
    new_roles = dict()
    role_subsets_considered = dict()

    new_role_ctrs = set()
    roles_assigned_by_user = dict()
    for u in up:
        perms = up[u]
        roles_assigned_orig = solve_set_cover_ilp(perms, role_perms)
        if u not in roles_assigned_by_user:
            roles_assigned_by_user[u] = set(roles_assigned_orig)

    for u in roles_assigned_by_user:
        roles_assigned_orig = roles_assigned_by_user[u]

        while len(roles_assigned_orig) > 0:
            all_largest_shared_roles = set()
            for v in roles_assigned_by_user:
                if u != v:
                    common_roles = tuple(roles_assigned_orig.intersection(roles_assigned_by_user[v]))
                    if len(common_roles) > 1:
                        all_largest_shared_roles.add(common_roles)

            all_largest_shared_roles = sorted(all_largest_shared_roles, key=len)
            roles_covered_by_shared_roles_rounds = {r for sharedroles in all_largest_shared_roles for r in sharedroles}
            if len(all_largest_shared_roles) == 0:
                roles_assigned_in_round = roles_assigned_orig
                new_roles = create_new_roles(u, roles_assigned_in_round, new_roles, roles_dict, role_subsets_considered,
                                             new_role_ctrs, ctr_new_role)
                if len(new_roles) > 0:
                    ctr_new_role = max(new_roles.keys()) + 1

                roles_assigned_orig = set()

            for largest_shared_roles in all_largest_shared_roles:
                if len(largest_shared_roles) == 0:
                    roles_assigned_in_round = roles_assigned_orig
                else:
                    roles_assigned_in_round = largest_shared_roles
                new_roles = create_new_roles(u, roles_assigned_in_round, new_roles, roles_dict, role_subsets_considered,
                                             new_role_ctrs, ctr_new_role)
                if len(new_roles) > 0:
                    ctr_new_role = max(new_roles.keys()) + 1
                roles_assigned_orig = roles_assigned_orig - roles_covered_by_shared_roles_rounds

    updated_roles = eliminate_roles(new_roles)

    # IF WE WANT TO LIMIT THE NUMBER OF ROLES ON EACH LAYER

    if len(updated_roles) > len(roles_dict):
        new_roles_to_keep = list(updated_roles.keys())[:len(roles_dict)]
    else:
        new_roles_to_keep = list(updated_roles.keys())

    # new_roles_to_keep = list(updated_roles.keys())
    subset_of_updated_roles = {k: updated_roles[k] for k in new_roles_to_keep if k in updated_roles}

    # print('Updated roles:')
    # pprint(updated_roles)

    print(f'# updated roles: {len(updated_roles)}')
    print('==========================================')
    print('==========================================')
    return subset_of_updated_roles


def solve_set_cover_ilp(universe, role_perms: dict):
    m = gp.Model("SetCover")
    m.setParam("OutputFlag", 0)  # Turn off Gurobi output

    subsets = [role_perms[r] for r in role_perms]
    n_sets = len(subsets)
    role_index_map = dict()

    i = 0
    for r in role_perms:
        role_index_map[r] = i
        i += 1

    # Binary variables x[i] = 1 if subset i is chosen
    x = m.addVars(len(role_perms), vtype=GRB.BINARY, name="x")

    # Objective: minimize the number of sets selected
    m.setObjective(gp.quicksum(x[i] for i in range(n_sets)), GRB.MINIMIZE)

    m.update()
    # Constraint: every element in the universe must be covered
    for e in universe:
        covering_sets = [i for i, s in enumerate(subsets) if e in s and s.issubset(universe)]
        m.addConstr(gp.quicksum(x[i] for i in covering_sets) >= 1, name=f"cover_{e}")

    m.update()
    m.write('set_cover.lp')
    m.optimize()

    if m.status == GRB.OPTIMAL:
        selected_sets = [r for r in role_index_map if x[role_index_map[r]].X == 1]
        return selected_sets
    else:
        return []


def rbac_to_rh(upfilename, roles):
    up, usermap, permmap = readup_and_usermap_permmap(upfilename)
    inv_permmap = {v: k for k, v in permmap.items()}
    inv_usermap = {v: k for k, v in usermap.items()}

    roles_dict = dict()
    for r in roles:
        roles_dict[r] = roles[r]

    # pprint(roles)

    start_time = time.time()

    RH = dict()
    layer = 0
    layer_0 = dict()
    for r in roles_dict:
        r_perms = {e[1] for e in roles_dict[r]}
        r_users = {e[0] for e in roles_dict[r]}
        layer_0[r] = {
            'users': r_users, 'roles': set(), 'perms': r_perms
        }
    RH[layer] = layer_0
    # updated_roles = subsets_bicliques_brute(up, roles_dict=roles_dict)
    updated_roles = subsets_bicliques_ILP(up, roles_dict)
    # updated_roles = subsets_bicliques_ILP_OLD(up, roles_dict)
    while updated_roles:
        up_induced = dict()
        for r in updated_roles:
            for u in updated_roles[r]['users']:
                if u not in up_induced:
                    up_induced[u] = set()
                up_induced[u].update(updated_roles[r]['roles'])
        updated_roles_dict = dict()
        for r in updated_roles:
            if r not in updated_roles_dict:
                updated_roles_dict[r] = set()
            for u in updated_roles[r]['users']:
                for r1 in updated_roles[r]['roles']:
                    updated_roles_dict[r].add((u, r1))
        layer += 1
        layer_i = dict()
        for r in updated_roles_dict:
            r_roles = {e[1] for e in updated_roles_dict[r]}
            r_users = {e[0] for e in updated_roles_dict[r]}
            r_perms = set()
            for e in updated_roles_dict[r]:
                r_perms.update(RH[layer - 1][e[1]]['perms'])
            layer_i[r] = {
                'users': r_users, 'roles': r_roles, 'perms': r_perms
            }
        RH[layer] = layer_i
        # updated_roles = subsets_bicliques_brute(up_induced, updated_roles_dict)
        updated_roles = subsets_bicliques_ILP(up_induced, updated_roles_dict)

    end_time = time.time()
    print('Time taken to compute RH:', (end_time - start_time), ' seconds')

    RH_roles_only = dict()
    for l in RH:
        if l not in RH_roles_only:
            RH_roles_only[l] = set()
        for r in RH[l]:
            RH_roles_only[l].add(r)
    num_roles_on_each_layer = dict()
    for l in RH_roles_only:
        if l not in num_roles_on_each_layer:
            num_roles_on_each_layer[l] = len(RH_roles_only[l])

    print('Number of roles on each layer in RH:')
    pprint(num_roles_on_each_layer)

    # RH = remove_redundant_roles(RH)

    RH_flat = dict()
    for layer in RH:
        for r in RH[layer]:
            RH_flat[r] = RH[layer][r].copy()

    # print('Flattened RH')
    # pprint(RH_flat)
    RH_mapped = dict()
    for r in RH_flat:
        if r not in RH_mapped:
            RH_mapped[r] = set()
        for u in RH_flat[r]['users']:
            RH_mapped[r].add(inv_usermap[u])
        for p in RH_flat[r]['perms']:
            RH_mapped[r].add(inv_permmap[p])
        for s in RH_flat[r]['roles']:
            RH_mapped[r].add(s)

    RH_mapped = remove_redundant_roles(RH_mapped)
    UP_mapped = dict()
    for u in up:
        UP_mapped[inv_usermap[u]] = {inv_permmap[p] for p in up[u]}

    check_RH(RH_mapped, up, usermap, permmap)
    # get_metrics(RH_mapped)

    G = dict_to_networkx(RH_mapped, directed=True)
    is_G_acyclic = nx.is_directed_acyclic_graph(G)
    if is_G_acyclic:
        print(Fore.GREEN + f'Is G acyclic: {is_G_acyclic}')
    else:
        print(Fore.RED + f'Is G acyclic: {is_G_acyclic}')
    print(Fore.RESET)

    path = nx.dag_longest_path(G, weight="weight", default_weight=1)
    length = nx.dag_longest_path_length(G, weight="weight", default_weight=1)
    print('Longest path:', path, ', length:', length)

    # Export to interactive HTML
    out_file = networkx_to_html_with_zoom(G, title="NetworkX from Dict → Interactive HTML", filename="nx_graph.html")
    print(out_file)

    # Print results
    # print('==============')
    # print('PageRank Scores')
    # print('==============')
    # start_time = time.time()
    #
    # pagerank_scores = nx.pagerank(G, alpha=0.85, weight='weight')
    # end_time = time.time()
    # print(f'Time taken to compute Pagerank Centrality: {end_time - start_time} seconds')
    #
    # epsilon = 0.001
    # sorted_pagerank_scores = dict(sorted(pagerank_scores.items(), key=lambda item: item[1], reverse=True))
    #
    # filtered_pagerank_scores = dict()
    # for node, score in sorted_pagerank_scores.items():
    #     if isinstance(node, int) and score > epsilon:
    #         # print(f"{node}: {score:.4f}")
    #         filtered_pagerank_scores[node] = score
    #
    # plt.bar(filtered_pagerank_scores.keys(), filtered_pagerank_scores.values(), color="skyblue")
    # plt.xlabel("Node")
    # plt.ylabel("PageRank Score")
    # plt.title("PageRank per Node")
    # plt.show()
    return RH, RH_mapped


# def add_roles_if_perms_overlap(RH: dict):
#     max_r = -1
#     layers = list()
#     for layer in RH:
#         layers.append(layer)
#         for r in RH[layer]:
#             if max_r < r:
#                 max_r = r
#     new_r = max_r + 1
#     RH_old = copy.deepcopy(RH)
#     for layer in layers:
#         roles_to_remove_from_this_layer = set()
#         for r1 in RH_old[layer]:
#             for r2 in RH_old[layer]:
#                 perms_intersect_orig = RH[layer][r1]['perms'].intersection(RH[layer][r2]['perms'])
#                 perms_intersect = perms_intersect_orig.copy()
#                 if r1 != r2 and len(perms_intersect) > 0:
#                     RH[layer + 1][r1] = RH[layer][r1]
#                     RH[layer + 1][r2] = RH[layer][r2]
#                     RH[layer + 1][r1]['roles'].add(new_r)
#                     RH[layer + 1][r2]['roles'].add(new_r)
#
#                     users_assigned_to_r1_r2 = RH[layer + 1][r1]['users'].union(RH[layer + 1][r2]['users'])
#                     roles_to_remove_from_this_layer.add(r1)
#                     roles_to_remove_from_this_layer.add(r2)
#                     RH[layer][new_r] = dict()
#                     RH[layer][new_r]['users'] = users_assigned_to_r1_r2
#                     if layer > 0:
#                         for r in RH_old[layer - 1]:
#                             if RH[layer - 1][r]['perms'].issubset(perms_intersect):
#                                 if 'roles' not in RH[layer][new_r]:
#                                     RH[layer][new_r]['roles'] = set()
#                                 RH[layer][new_r]['roles'].add(r)
#                                 perms_intersect = perms_intersect - RH[layer - 1][r]['perms']
#
#                     RH[layer][new_r]['perms'] = perms_intersect_orig
#                     new_r += 1
#         for r in roles_to_remove_from_this_layer:
#             RH[layer].pop(r)
#     # print('RH AFTER:')
#     for layer in layers:
#         RH[layer] = eliminate_roles(RH[layer])
#
#     # RH = remove_redundant_roles(RH)
#     pprint(RH)
#     return RH


def run_rbac_to_rh_no_new_roles(upfilename: str, roles: dict):
    up, usermap, permmap = readup_and_usermap_permmap(upfilename)

    RH1, RH_flat = rbac_to_rh(upfilename, roles)
    # RH = add_roles_if_perms_overlap(RH)
    recon_rbac = reconstruct_roles_from_RH(RH_flat)
    # print('Reconstructed RBAC:')
    # pprint(recon_rbac)
    recon_rbac_as_edges = roles_dict_to_edges(recon_rbac)

    recon_rbac_unmapped_as_edges = dict()
    for r in recon_rbac_as_edges:
        r_edges = set()
        for e in recon_rbac_as_edges[r]:
            r_edges.add((usermap[e[0]], permmap[e[1]]))
        recon_rbac_unmapped_as_edges[r] = r_edges

    RH = RBAC_to_RH.rbac_to_rh_no_new_roles(upfilename, recon_rbac_unmapped_as_edges)
    RH_to_write = dict()
    for r in RH:
        RH_to_write[r] = list(RH[r])
    u_name = upfilename.split('/')[-1]
    rh_fname = f'ALG2_RH_{u_name}'
    with open(rh_fname, 'w') as f:
        json.dump(RH_to_write, f, indent=4, sort_keys=True)
    metrics = get_metrics(RH, use_sampling=True)
    return RH, metrics


def main(args):
    # up = readup(args.input_file)
    upfilename = args.input_file

    up, usermap, permmap = readup_and_usermap_permmap(upfilename)
    inv_permmap = {v: k for k, v in permmap.items()}
    inv_usermap = {v: k for k, v in usermap.items()}

    # MINEDGES FROM MINROLES
    # emfilename = args.input_file + "-em.txt"
    # em = readem(emfilename)
    # up, usermap, permmap = readup_and_usermap_permmap(upfilename)
    # role_usermap, role_permmap = minrole_to_minedge(up, em, 60, 5)
    # roles_minedges_from_minroles = dict()
    # for r in role_usermap:
    #     roles_minedges_from_minroles[r] = set()
    #     for u in role_usermap[r]:
    #         for p in role_permmap[r]:
    #             roles_minedges_from_minroles[r].add((u, p))
    # roles = roles_minedges_from_minroles

    # roles, _ = greedythenlattice_greedy.run(upfilename)
    # roles = BicliqueCoverToILP.run_greedy_delta(upfilename, 1000)

    num_roles, roles = maxsetsbp.run(upfilename)
    roles = {idx: roles[idx] for idx in range(len(roles))}

    RH, metrics = run_rbac_to_rh_no_new_roles(upfilename, roles)

    return RH, metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Read input UP file -> generate a min role RBAC policy -> generate "
                                                 "Integer Program for the RH problem")
    parser.add_argument("input_file", type=str, help="Input UP file")

    args = parser.parse_args()
    result = main(args)
    # print(result)
