#!/usr/bin/env python3

import argparse
import copy
import heapq
import json
import os
import random
import signal
import sys
import time
from asyncio import as_completed
from collections import defaultdict, deque
from pathlib import Path
from typing import Set, Dict, List

import gurobipy as gp
import numpy as np
from gurobipy import GRB
import networkx as nx
from pprint import pprint

from colorama import Fore
from tqdm import tqdm

from rh_utils import RH_to_adj, dict_to_digraph, read_rbac_file, read_rh_file
from rh_metrics import wsc, get_metrics

prefix_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(f'{prefix_dir}/..')
sys.path.append(f'{prefix_dir}/../..')

from algorithms import BicliqueCoverToILP
import maxsetsbp
from greedythenlattice_greedy_only import run
import greedythenlattice_greedy
from RoleHierarchy.graph_dict import dict_to_networkx, networkx_to_html_with_zoom
from readup import readup, readup_and_usermap_permmap
from minedgefromminrole import minrole_to_minedge
from removedominators import readem


def sighandler(signum, frame):
    raise Exception("timeout")


def if_it_does_not_contain_cycle(sub):
    visited = set()
    no_cycle = True
    for r in sub:
        if r not in visited:
            visited.add(r)
        else:
            no_cycle = False
            return no_cycle
    return no_cycle


def get_user_chain(roles_users: dict):
    sorted_roles_users = sorted(roles_users.items(), key=lambda item: len(item[1]))

    subsets_users = []
    for starting_role, _ in sorted_roles_users:
        sub = list()
        curr = starting_role
        sub.append(curr)

        for r, _ in sorted_roles_users:
            if curr == r:
                continue
            if roles_users[curr].issubset(roles_users[r]):
                sub.append(r)
                curr = r
        if len(sub) > 1:
            if if_it_does_not_contain_cycle(sub):
                subsets_users.append(sub)
    print('Subset users:')
    pprint(subsets_users)
    return subsets_users


def get_perm_chain(roles_perms: dict):
    sorted_roles_perms = sorted(roles_perms.items(), key=lambda item: len(item[1]))

    subsets_perms = []
    for starting_role, _ in sorted_roles_perms:
        sub = list()
        curr = starting_role
        sub.append(curr)

        for r, _ in sorted_roles_perms:
            if curr == r:
                continue
            if roles_perms[curr].issubset(roles_perms[r]):
                sub.append(r)
                curr = r
        if len(sub) > 1:
            if if_it_does_not_contain_cycle(sub):
                subsets_perms.append(sub)
    print('Subset perms:')
    pprint(subsets_perms)
    return subsets_perms


def create_RH_from_subset_users(subsets_users, roles_users, roles_perms):
    RH = dict()
    for r in roles_users:
        RH[r] = set()

    # assign role at j to role at i

    roles_assigned_perms = set()
    for subset in subsets_users:
        i = 0
        while i < len(subset) - 1:
            j = i + 1
            RH[subset[i]].add(subset[j])
            # perms_inherited = get_inherited_perms_in_RH(RH)
            # required_perms_at_ri = roles_perms[subset[i]].difference(perms_inherited[subset[j]])
            # required_perms_at_ri = required_perms_at_ri.difference(roles_perms[subset[j]])
            # # RH[subset[i]].update(required_perms_at_ri)
            #
            # RH[subset[i]] = RH[subset[i]].union(required_perms_at_ri)

            # roles_assigned_perms.add(subset[i])
            i += 1

    # assign users of r to r in RH
    for r in RH:
        RH[r].update(roles_users[r])

    for subset in subsets_users:
        # first_r = subset[0]
        # RH[first_r].update(roles_users[first_r])
        i = 1
        while 0 < i < len(subset):
            r = subset[i]
            prev_r = subset[i - 1]
            only_users = roles_users[r] - roles_users[prev_r]
            RH_r_users = {u for u in RH[r] if isinstance(u, str) and (u.startswith('u') or u.startswith('U'))}
            RH[r].difference_update(RH_r_users)
            RH[r].update(only_users)
            i += 1

    # if len(subsets_users) == 0:
    for r in RH:
        if r not in roles_assigned_perms:
            RH[r].update(roles_perms[r])

    return RH


def create_RH_from_subset_perms(subsets_perms, roles_users, roles_perms):
    RH: Dict[int, Set] = {}
    for r in roles_users:
        RH[r] = set()

    # assign role at i to role at j
    roles_assigned_users = set()
    for subset in subsets_perms:
        i = 0
        while i < len(subset) - 1:
            j = i + 1
            RH[subset[j]].add(subset[i])
            i += 1

    # assign users of r to r in RH
    # if len(subsets_perms) == 0:
    for r in RH:
        if r not in roles_assigned_users:
            RH[r].update(roles_users[r])

    for r in RH:
        RH[r].update(roles_perms[r])

    for subset in subsets_perms:
        i = 1
        while 0 < i < len(subset):
            prev_r = subset[i - 1]
            r = subset[i]
            only_perms = roles_perms[r] - roles_perms[prev_r]
            RH_r_perms = {p for p in RH[r] if isinstance(p, str) and (p.startswith('p') or p.startswith('P'))}
            RH[r].difference_update(RH_r_perms)
            RH[r].update(only_perms)
            i += 1
    return RH


def create_RH_from_subset(subsets_users, subsets_perms, roles_users, roles_perms):
    RH = dict()
    for r in roles_users:
        RH[r] = set()

    # assign role at j to role at i
    for subset in subsets_users:
        i = 0
        while i < len(subset) - 1:
            j = i + 1
            RH[subset[i]].add(subset[j])
            i += 1

    # assign role at i to role at j
    for subset in subsets_perms:
        i = 0
        while i < len(subset) - 1:
            j = i + 1
            RH[subset[j]].add(subset[i])
            i += 1

    # assign users of r to r in RH
    for r in RH:
        RH[r].update(roles_users[r])

    for subset in subsets_users:
        i = 1
        while 0 < i < len(subset):
            r = subset[i]
            prev_r = subset[i - 1]
            only_users = roles_users[r] - roles_users[prev_r]
            RH_r_users = {u for u in RH[r] if isinstance(u, str) and (u.startswith('u') or u.startswith('U'))}
            RH[r].difference_update(RH_r_users)
            RH[r].update(only_users)
            i += 1

    for r in RH:
        RH[r].update(roles_perms[r])

    for subset in subsets_perms:
        i = 1
        while 0 < i < len(subset):
            prev_r = subset[i - 1]
            r = subset[i]
            only_perms = roles_perms[r] - roles_perms[prev_r]
            RH_r_perms = {p for p in RH[r] if isinstance(p, str) and (p.startswith('p') or p.startswith('P'))}
            RH[r].difference_update(RH_r_perms)
            RH[r].update(only_perms)
            i += 1
    return RH


# In this function, we remove role-role edges and check if the RH is still authorized
def remove_redundant_role_role_edges(roles: dict, RH: dict, up: dict, usermap: dict, permmap: dict):
    RH_prev = copy.deepcopy(RH)
    edges_removed_in_this_round = {None}
    while True:
        check = check_RH(RH, up, usermap, permmap)
        if not check or len(edges_removed_in_this_round) == 0:
            RH = copy.deepcopy(RH_prev)
            break
        perms_inherited_dict = get_inherited_perms_in_RH(RH)
        for r in perms_inherited_dict:
            perms_assigned_r = {e for e in RH[r] if isinstance(e, str) and (e.startswith('p') or e.startswith('P'))}
            perms_inherited_dict[r] = perms_inherited_dict[r].union(perms_assigned_r)
        edges_to_remove = set()

        for r in RH:
            roles_assigned = {e for e in RH[r] if isinstance(e, int)}

            for s in roles_assigned:
                remaining_roles_assigned = roles_assigned - {s}

                perms_gained_from_remaining_roles = set()
                for t in remaining_roles_assigned:
                    perms_gained_from_remaining_roles = perms_gained_from_remaining_roles.union(perms_inherited_dict[t])
                if perms_inherited_dict[s].issubset(perms_gained_from_remaining_roles):
                    edges_to_remove.add((r, s))
                    break

        print('Role Role edges removed:', edges_to_remove)
        edges_removed_in_this_round = edges_to_remove
        roles_to_remove = set()
        for (r, e) in edges_to_remove:
            RH[r].remove(e)
            if len(RH[r]) == 0:
                roles_to_remove.add(r)

        for r in roles_to_remove:
            RH.pop(r)

        for r in RH:
            RH[r] = RH[r].difference(roles_to_remove)

        RH_prev = copy.deepcopy(RH)
    return RH


def remove_redundant_edges(RH: dict) -> dict:
    users_inherited = get_inherited_users_in_RH(RH)
    perms_inherited = get_inherited_perms_in_RH(RH)
    roles_inherited = get_inherited_roles_in_RH(RH)
    redundant_edges: dict[int, set] = {}
    for r in RH:
        perms_assigned = {e for e in RH[r] if isinstance(e, str) and (e.startswith('p') or e.startswith('P'))}
        users_assigned = {e for e in RH[r] if isinstance(e, str) and (e.startswith('u') or e.startswith('U'))}
        roles_assigned = {e for e in RH[r] if isinstance(e, int)}

        users_inherited_r = users_inherited[r]
        perms_inherited_r = perms_inherited[r]
        roles_inherited_r = roles_inherited[r]

        common_perms = perms_inherited_r.intersection(perms_assigned)
        common_users = users_inherited_r.intersection(users_assigned)
        common_roles = roles_inherited_r.intersection(roles_assigned)
        if len(common_perms) > 0:
            if r not in redundant_edges:
                redundant_edges[r] = set()
            redundant_edges[r] = redundant_edges[r].union(common_perms)
        if len(common_users) > 0:
            if r not in redundant_edges:
                redundant_edges[r] = set()
            redundant_edges[r] = redundant_edges[r].union(common_users)

        if len(common_roles) > 0:
            print(f'Redundant role edges: {r} -> {common_roles}')
            if r not in redundant_edges:
                redundant_edges[r] = set()
            redundant_edges[r] = redundant_edges[r].union(common_roles)

    print('Redundant edges:')
    pprint(redundant_edges)
    for r in redundant_edges:
        for e in redundant_edges[r]:
            RH[r].remove(e)

    empty_roles_to_remove = set()
    for r in RH:
        if len(RH[r]) == 0:
            empty_roles_to_remove.add(r)
    for r in empty_roles_to_remove:
        RH.pop(r)
    for r in RH:
        RH[r] = RH[r] - (RH[r] & empty_roles_to_remove)
    return RH


# get all descendant roles of r in RH
def descendant_of(RH: dict, r: int):
    stack = deque()
    stack.appendleft(r)
    visited = list()
    while stack:
        curr_r = stack.popleft()
        visited.append(curr_r)
        # if r != curr_r:
        #     roles_r = {e for e in RH[r] if isinstance(e, int)}
        #     users_inherited = users_inherited_dict[r].union(roles_r)
        #     users_inherited_dict[curr_r] = users_inherited_dict[curr_r].union(users_inherited)

        roles_assigned_to_curr_r = {e for e in RH[curr_r] if isinstance(e, int)}

        for s in roles_assigned_to_curr_r:
            if s not in visited and isinstance(s, int):
                stack.appendleft(s)

    visited.remove(r)
    return visited


def remove_edges_if_common_perms(RH: dict):
    inherited_perms_rh = get_inherited_perms_in_RH(RH)
    edges_to_remove = set()
    for r1 in RH:
        assigned_perms_r1 = {e for e in RH[r1] if isinstance(e, str) and (e.startswith('P') or e.startswith('p'))}
        all_perms_r1 = inherited_perms_rh[r1].union(assigned_perms_r1)
        for r2 in RH:
            assigned_perms_r2 = {e for e in RH[r2] if isinstance(e, str) and (e.startswith('P') or e.startswith('p'))}
            all_perms_r2 = inherited_perms_rh[r2].union(assigned_perms_r2)

            if r1 != r2:
                if all_perms_r1.issubset(all_perms_r2) and r2 in RH[r1]:
                    # get all descendants of r2, and remove edge between r1 and the descendants
                    desc_r2 = descendant_of(RH, r2)
                    for d in desc_r2:
                        edges_to_remove.add((r1, d))
                elif all_perms_r2.issubset(all_perms_r1) and r1 in RH[r2]:
                    # get all descendants of r1, and remove edge between r2 and the descendants
                    desc_r1 = descendant_of(RH, r1)
                    for d in desc_r1:
                        edges_to_remove.add((r2, d))
                elif len(all_perms_r1 & all_perms_r2) != 0:
                    desc_r2 = descendant_of(RH, r2)
                    for d in desc_r2:
                        assigned_perms_d = {e for e in RH[d] if
                                             isinstance(e, str) and (e.startswith('P') or e.startswith('p'))}
                        all_perms_d = inherited_perms_rh[d].union(assigned_perms_d)
                        # is there an edge between r1 and d
                        if d in RH[r1] and all_perms_r1.issubset(all_perms_d):
                            RH[r1].add(d)
                            desc_d = descendant_of(RH, d)
                            for dd in desc_d:
                                edges_to_remove.add((r1, dd))
    for e in edges_to_remove:
        r = e[0]
        s = e[1]
        if s in RH[r]:
            RH[r].remove(s)

    for r in set(RH.keys()):
        if len(RH[r]) == 0:
            RH.pop(r)
    return RH

def get_entry_exit_roles_for_user_perm(u, p, RH, RH_adj: dict):
    # paths = all_simple_paths(RH_adj, u, p)
    # entry_exit_roles = set()
    # for path in paths:
    #     if len(path) > 2:
    #         entry_exit_roles.add((path[1], path[-2]))
    # return entry_exit_roles

    # print('RH:')
    # pprint(RH)
    # print('RH_adj:')
    # pprint(RH_adj)
    entry_exit_roles = set()
    entry_roles = {e for e in RH_adj[u] if isinstance(e, int)}
    exit_roles = set()
    for k in RH_adj:
        if isinstance(k, int):
            if p in RH_adj[k]:
                exit_roles.add(k)
    RH_G = dict_to_digraph(RH_adj)
    for e in entry_roles:
        for x in exit_roles:
            # if there is a path betweeen entry and exit roles, only then add it
            if nx.has_path(RH_G, e, x):
                entry_exit_roles.add((e, x))
            else:
                # print(f'no path between {u}->{e}, {x}->{p}')
                pass
    return entry_exit_roles


def check_if_all_edges_are_needed(roles: dict, RH: dict, up: dict, usermap: dict, permmap: dict, delete=True):
    edges_tested = set()
    RH_prime = copy.deepcopy(RH)
    edges_to_remove = set()
    edges_to_keep = set()
    RH_edges = {(r, e) for r in RH for e in RH[r]}

    RH_prime_prev = copy.deepcopy(RH_prime)

    for (r, e) in RH_edges:
        if (r, e) not in edges_tested:
            RH_prime[r].remove(e)
            edges_tested.add((r, e))
            check = check_RH(RH_prime, up, usermap, permmap)
            if check:
                edges_to_remove.add((r, e))
                RH_prime_prev = copy.deepcopy(RH_prime)
            else:
                edges_to_keep.add((r, e))
                RH_prime = copy.deepcopy(RH_prime_prev)
    # print('More edges can be removed, these are:')
    # pprint(edges_to_remove)

    if delete:
        roles_to_remove = set()
        for (r, e) in edges_to_remove:
            RH[r].remove(e)
            if len(RH[r]) == 0:
                roles_to_remove.add(r)

        for r in roles_to_remove:
            RH.pop(r)

        for r in RH:
            RH[r] = RH[r].difference(roles_to_remove)
    print('Edges to remove while checking one by one: ', edges_to_remove)
    return RH, edges_to_keep, edges_to_remove


def rbac_to_rh(roles_as_edges: dict, usermap: dict, permmap: dict):
    # roles_as_edges = utils.get_roles_as_edges(roles)
    inv_permmap = {v: k for k, v in permmap.items()}
    inv_usermap = {v: k for k, v in usermap.items()}
    roles_perms = dict()
    for r in roles_as_edges:
        role_edge = roles_as_edges[r]
        if r not in roles_perms:
            roles_perms[r] = set()
        for e in role_edge:
            roles_perms[r].add(inv_permmap[e[1]])
    print(roles_perms)
    roles_users = dict()
    roles_perms = dict()

    for r in roles_as_edges:
        role_edge = roles_as_edges[r]

        if r not in roles_users:
            roles_users[r] = set()
            roles_perms[r] = set()
        for e in role_edge:
            roles_users[r].add(inv_usermap[e[0]])
            roles_perms[r].add(inv_permmap[e[1]])
    print(roles_users)

    roles_dict = {r: roles_users[r].union(roles_perms[r]) for r in roles_users}

    subsets_users = get_user_chain(roles_users)
    subsets_perms = get_perm_chain(roles_perms)

    # RH = create_RH_from_subset(subsets_users, subsets_perms, roles_users, roles_perms)
    if len(subsets_users) >= len(subsets_perms):
        RH = create_RH_from_subset_users(subsets_users, roles_users, roles_perms)
        new_roles = reconstruct_roles_from_RH(RH)
        new_roles_edges = roles_dict_to_edges(new_roles)
    else:
        RH = create_RH_from_subset_perms(subsets_perms, roles_users, roles_perms)

    RH_dict, RH_dict_expanded = expand_RH(RH)

    RH_prime = dict()
    for r in RH_dict_expanded:
        if r not in RH_prime:
            RH_prime[r] = set()
        for u in RH_dict_expanded[r]['users']:
            RH_prime[r].add(u)
        for p in RH_dict_expanded[r]['perms']:
            RH_prime[r].add(p)
        for r1 in RH_dict_expanded[r]['roles']:
            RH_prime[r].add(r1)

    return RH, RH_dict


def expand_RH(RH: dict):
    RH_dict = dict()
    for r in RH:
        for e in RH[r]:
            if r not in RH_dict:
                RH_dict[r] = {
                    'users': set(),
                    'perms': set(),
                    'roles': set(),
                }
            if isinstance(e, str):
                if e.startswith('u') or e.startswith('U'):
                    RH_dict[r]['users'].add(e)
                elif e.startswith('p') or e.startswith('P'):
                    RH_dict[r]['perms'].add(e)
            else:
                RH_dict[r]['roles'].add(e)

    RH_dict_expanded = dict()

    for r in RH_dict:
        q = [r]
        visited = set()
        visited.add(r)
        users_r = set()
        perms_r = RH_dict[r]['perms']

        while q:
            curr_r = q.pop()
            users_r = users_r.union(RH_dict[curr_r]['users'])
            if curr_r not in RH_dict_expanded:
                RH_dict_expanded[curr_r] = {
                    'users': set(),
                    'perms': set(),
                    'roles': set()
                }
            RH_dict_expanded[curr_r]['users'] = RH_dict_expanded[curr_r]['users'].union(users_r)
            for s in RH_dict[curr_r]['roles']:
                if s not in visited:
                    q.append(s)
                    perms_r = perms_r.union(RH_dict[s]['perms'])

        RH_dict_expanded[r]['perms'] = perms_r
        RH_dict_expanded[r]['roles'] = RH_dict[r]['roles']

    return RH_dict, RH_dict_expanded


# def get_users_perms_in_RH_recursive(r, RH: dict, users_assigned: set, perms_assigned: set):
#     entities_assigned = {e for e in RH[r]}
#
#     for e in entities_assigned:
#         if isinstance(e, str):
#             if e.startswith('U') or e.startswith('u'):
#                 users_assigned.add(e)
#             elif e.startswith('P') or e.startswith('p'):
#                 perms_assigned.add(e)
#         elif isinstance(e, int):
#             get_users_perms_in_RH_recursive(e, RH, set(), perms_assigned)


def get_inherited_users_in_RH(RH: dict):
    users_inherited_dict: dict[int, set] = {}
    for r in RH:
        users_inherited_dict[r] = set()

    for r in RH:
        stack = deque()
        stack.appendleft(r)
        visited = set()

        while stack:
            curr_r = stack.popleft()
            visited.add(curr_r)
            if r != curr_r:
                users_r = {e for e in RH[r] if isinstance(e, str) and (e.startswith('u') or e.startswith('U'))}
                users_inherited = users_inherited_dict[r].union(users_r)
                users_inherited_dict[curr_r] = users_inherited_dict[curr_r].union(users_inherited)

            roles_assigned_to_curr_r = {e for e in RH[curr_r] if isinstance(e, int)}

            for s in roles_assigned_to_curr_r:
                if s not in visited and isinstance(s, int):
                    stack.appendleft(s)

    return users_inherited_dict


def get_inherited_perms_in_RH(RH: dict):
    perms_inherited_dict: dict[int, set] = {}
    for r in RH:
        perms_inherited_dict[r] = set()

    for r in RH:
        stack = deque()
        stack.appendleft(r)
        visited = set()

        perms_inherited = set()
        while stack:
            curr_r = stack.popleft()
            visited.add(curr_r)
            perms_curr_r = {e for e in RH[curr_r] if isinstance(e, str) and (e.startswith('p') or e.startswith('P'))}
            if r != curr_r:
                perms_inherited = perms_inherited.union(perms_curr_r)

            roles_assigned_curr_r = {e for e in RH[curr_r] if isinstance(e, int)}

            for e in roles_assigned_curr_r:
                if e not in visited and isinstance(e, int):
                    stack.appendleft(e)
        perms_inherited_dict[r] = perms_inherited_dict[r].union(perms_inherited)
    return perms_inherited_dict


def get_inherited_roles_in_RH(RH: dict):
    roles_inherited_dict: dict[int, set] = {}
    for r in RH:
        roles_inherited_dict[r] = set()

    for r in RH:
        stack = deque()
        stack.appendleft(r)
        visited = set()

        roles_inherited = set()
        while stack:
            curr_r = stack.popleft()
            visited.add(curr_r)
            roles_assigned_curr_r = {e for e in RH[curr_r] if isinstance(e, int)}
            if r != curr_r:
                roles_inherited = roles_inherited.union(roles_assigned_curr_r)

            for e in roles_assigned_curr_r:
                if e not in visited:
                    stack.appendleft(e)
                else:
                    roles_inherited.add(e)

        roles_inherited_dict[r] = roles_inherited_dict[r].union(roles_inherited)
    return roles_inherited_dict


def reconstruct_up_from_roles(roles: dict):
    recon_up = dict()
    for r in roles:
        perms = set()
        users = set()

        for e in roles[r]:
            if isinstance(e, str) and (e.startswith('u') or e.startswith('U')):
                users.add(e)
            elif isinstance(e, str) and (e.startswith('p') or e.startswith('P')):
                perms.add(e)
        for u in users:
            for p in perms:
                if u not in recon_up:
                    recon_up[u] = set()
                recon_up[u].add(p)
    return recon_up


def rbac_edges_to_dict(roles: list):
    RBAC = dict()
    for r in roles:
        for e in roles[r]:
            if r not in RBAC:
                RBAC[r] = set()
            RBAC[r].add(e[0])
            RBAC[r].add(e[1])
    return RBAC


def reconstruct_roles_from_RH(RH: dict):
    recon_roles: dict[int, set] = {}
    for r in RH:
        users_r = {e for e in RH[r] if isinstance(e, str) and (e.startswith('u') or e.startswith('U'))}
        perms_r = {e for e in RH[r] if isinstance(e, str) and (e.startswith('p') or e.startswith('P'))}
        if r not in recon_roles:
            recon_roles[r] = set()
        recon_roles[r] = users_r.union(perms_r)

    for r in RH:
        stack = deque()
        stack.appendleft(r)
        visited = set()
        users_r = {e for e in RH[r] if isinstance(e, str) and (e.startswith('u') or e.startswith('U'))}
        perms_r = {e for e in RH[r] if isinstance(e, str) and (e.startswith('p') or e.startswith('P'))}

        users_acc = users_r
        perms_acc = perms_r
        while stack:
            curr_r = stack.pop()
            visited.add(curr_r)

            users_curr_r = {e for e in RH[curr_r] if isinstance(e, str) and (e.startswith('u') or e.startswith('U'))}
            perms_curr_r = {e for e in RH[curr_r] if isinstance(e, str) and (e.startswith('p') or e.startswith('P'))}
            users_acc = users_acc.union(users_curr_r)
            perms_acc = perms_acc.union(perms_curr_r)
            recon_roles[curr_r] = recon_roles[curr_r].union(users_curr_r)
            roles_assigned_curr_r = {e for e in RH[curr_r] if isinstance(e, int)}
            for e in roles_assigned_curr_r:
                if e not in visited and isinstance(e, int):
                    stack.appendleft(e)
        recon_roles[r] = recon_roles[r].union(perms_acc)
    return recon_roles


def roles_edges_to_dict(roles: dict, usermap: dict, permmap: dict):
    roles_as_dict = dict()
    for r in roles:
        role_edges = roles[r]
        role_mapped_edges = set()
        for (u, p) in role_edges:
            if r not in roles_as_dict:
                roles_as_dict[r] = set()
            roles_as_dict[r].add(usermap[u])
            roles_as_dict[r].add(permmap[p])
            role_mapped_edges.add((usermap[u], permmap[p]))
    return roles_as_dict


def roles_dict_to_edges(roles_as_dict: dict):
    roles_as_edges = dict()
    for r in roles_as_dict:
        role_edges = set()
        users_in_role = set()
        perms_in_role = set()
        for e in roles_as_dict[r]:
            if e.startswith('U') or e.startswith('u'):
                users_in_role.add(e)
            elif e.startswith('P') or e.startswith('p'):
                perms_in_role.add(e)
        for user in users_in_role:
            for perm in perms_in_role:
                role_edges.add((user, perm))
        roles_as_edges[r] = role_edges

    return roles_as_edges


def check_whether_lists_equal(lst1: list, lst2: list):
    check_list_1 = True
    check_list_2 = True
    for e1 in lst1:
        check_list_1 = check_list_1 and e1 in lst2
    for e2 in lst2:
        check_list_2 = check_list_2 and e2 in lst1 and e2 in lst1
    return check_list_1 and check_list_2


def reconstruct_up_from_RH(RH: dict, up: dict, usermap: dict, permmap: dict):
    inv_permmap = {v: k for k, v in permmap.items()}
    inv_usermap = {v: k for k, v in usermap.items()}
    # roles_as_dict = roles_edges_to_dict(roles, inv_usermap, inv_permmap)
    recon_roles = reconstruct_roles_from_RH(RH)
    recon_up = reconstruct_up_from_roles(recon_roles)
    return recon_up


def check_RH(RH, up, usermap, permmap):
    recon_up = reconstruct_up_from_RH(RH, up, usermap, permmap)
    # map the reconstructed up back to labels in usermap and permmap
    recon_up_mapped = dict()

    check = True
    for u in recon_up:
        perms = recon_up[u]
        if usermap[u] not in recon_up_mapped:
            recon_up_mapped[usermap[u]] = set()
        for p in perms:
            recon_up_mapped[usermap[u]].add(permmap[p])
        check = recon_up_mapped[usermap[u]] == up[usermap[u]]
        if not check:
            print(Fore.RED + f'Does reconstructed UP match UP: {check}')
            print('Got:', u, recon_up_mapped[usermap[u]])
            print('Expected:', u, up[usermap[u]])
            # pprint(RH)

            return check

    check = check and recon_up_mapped.keys() == up.keys()
    for u in up:
        check = check and (up[u] == recon_up_mapped[u])
        if not check:
            print(Fore.RED + f'Does reconstructed UP match UP: {check}')
            return check
    if check:
        print(Fore.GREEN + f'Does reconstructed UP match UP: {check}')
    else:
        print(Fore.RED + f'Does reconstructed UP match UP: {check}')
    return check


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

    to_remove = set()
    for r1 in RH:
        for r2 in RH[r1]:
            if isinstance(r2, int) and r2 in inv_duplicate_roles:
                to_remove.add(r2)

        for r in to_remove:
            if r in RH[r1]:
                RH[r1].remove(r)
                RH[r1].add(inv_duplicate_roles[r])

    return RH


def _rh_builder_iteration(self, r: int, parent: int):
    if (parent, r) not in self.E:
        self._add_edge(parent, r)

    # for each ri such that super_role (parent) directly inherits perms from ri
    for ri in list(self.children[parent]):
        if ri == r:
            continue

        Pi, Pr = self.roles[ri], self.roles[r]
        inter = Pi & Pr

        # if disjoint, ignore
        if not inter:
            continue

        # if r is a superset of ri
        if Pr.issuperset(Pi):
            # remove edge from parent to ri, add edge between r and ri, r can inherit perms from ri and parent
            # can inherit from r
            self._remove_edge(parent, ri)
            self._add_edge(r, ri)
            # for all the descendants (dfs) of ri, remove any edges from r to rj
            for rj in self._descendants(ri):
                if (r, rj) in self.E:
                    self._remove_edge(r, rj)
            continue

        # On the other hand, if perms of r and contained in perms of ri
        if Pr.issubset(Pi):
            # remove edge between parent and r and build the RH where ri is the parent
            self._remove_edge(parent, r)
            self._rh_builder_iteration(r, ri)
            # return

        for rj in self._bfs_nodes(ri):
            if self.roles[r].issuperset(self.roles[rj]):
                self._add_edge(r, rj)
                for rk in self._descendants(rj):
                    if (r, rk) in self.E:
                        self._remove_edge(r, rk)


def rbac_to_rh_no_new_roles(upfilename: str, roles: dict, edge_threshold=10):
    up, usermap, permmap = readup_and_usermap_permmap(upfilename)
    inv_permmap = {v: k for k, v in permmap.items()}
    inv_usermap = {v: k for k, v in usermap.items()}

    start_time = time.time()
    print('Initial Metrics')
    roles_mapped = dict()
    for r in roles:
        if r not in roles_mapped:
            roles_mapped[r] = set()
        for e in roles[r]:
            roles_mapped[r].add(inv_usermap[e[0]])
            roles_mapped[r].add(inv_permmap[e[1]])

    # RH, RH_dict = rbac_to_rh(roles, usermap, permmap)

    u_name = upfilename.split('/')[-1]

    RH = read_rh_file(Path(f'VAIDYA_RH_{u_name}'))


    G = dict_to_networkx(RH, directed=True)

    # Export to interactive HTML
    out_file = networkx_to_html_with_zoom(G, title="NetworkX from Dict → Interactive HTML", filename="nx_graph.html")
    print(out_file)

    # RH = keep_shortest_paths(RH, up, usermap, permmap)
    # get_metrics(RH)
    check_RH(RH, up, usermap, permmap)

    # RH, edges_to_keep, edges_to_remove = check_if_all_edges_are_needed(roles, RH, up, usermap, permmap, delete=False)

    RH = remove_redundant_roles(RH)
    # RH = remove_redundant_role_role_edges(roles, RH, up, usermap, permmap)
    RH = remove_redundant_edges(RH)

    RH = remove_edges_if_common_perms(RH)
    for i in range(10):
        RH = remove_more_edges_subgraph(RH, up, usermap, permmap, k=5)

    # RH = remove_more_edges(RH, up, usermap, permmap)
    # RH = remove_more_edges(RH, up, usermap, permmap)
    # remove_edges_v2(RH)
    # RH = remove_redundant_role_role_edges(roles, RH, up, usermap, permmap)

    RH = minimize_edges(RH, up, usermap, permmap, set())

    RH = remove_redundant_edges(RH)
    RH = remove_edges_if_common_perms(RH)

    # RH = minimize_edges(RH, up, usermap, permmap, edges_to_keep=edges_to_keep)

    # RH = remove_more_edges(roles, RH, up, usermap, permmap)
    # RH = remove_redundant_roles(RH)

    # RH_adj = RH_to_adj(RH)
    # RH_adj_undirected = make_undirected(RH_adj)
    # RH = bfs_spanning_forest(RH, RH_adj_undirected)
    # print('Forest:', RH)
    # get_metric(RH)
    check_RH(RH, up, usermap, permmap)
    # print('RH:')
    # pprint(RH)

    end_time = time.time()
    print('Time taken to compute RH:', (end_time - start_time), ' seconds')

    # print('CHECK IF ALL EDGES ARE NEEDED:')
    # RH, _, _ = check_if_all_edges_are_needed(roles, RH, up, usermap, permmap)

    roles_as_dict = roles_edges_to_dict(roles, inv_usermap, inv_permmap)

    print(Fore.RESET)
    # get_metrics(RH)
    G = dict_to_networkx(RH, directed=True)

    # Export to interactive HTML
    out_file = networkx_to_html_with_zoom(G, title="NetworkX from Dict → Interactive HTML", filename="nx_graph.html")
    print(out_file)
    check_RH(RH, up, usermap, permmap)

    # Print results
    # print('==============')
    # print('PageRank Scores')
    # print('==============')
    # start_time = time.time()
    #
    # pagerank_scores = nx.pagerank(G, alpha=0.85, weight='weight')
    # epsilon = 0.0001
    # sorted_pagerank_scores = dict(sorted(pagerank_scores.items(), key=lambda item: item[1], reverse=True))
    # end_time = time.time()
    # print(f'Time taken to compute Pagerank Centrality: {end_time - start_time} seconds')
    # filtered_pagerank_scores = dict()
    # for node, score in sorted_pagerank_scores.items():
    #     if isinstance(node, int) and score > epsilon:
    #         print(f"{node}: {score:.4f}")
    #         filtered_pagerank_scores[node] = score
    #
    # plt.bar(filtered_pagerank_scores.keys(), filtered_pagerank_scores.values(), color="skyblue")
    # plt.xlabel("Node")
    # plt.ylabel("PageRank Score")
    # plt.title("PageRank per Node")
    # plt.show()

    return RH


# remove edges between entry and exit roles for a user u and permission p
# idea: use dfs to check
def remove_edges_v2(RH: dict):
    RH_adj = RH_to_adj(RH)
    users = {e for e in RH_adj if isinstance(e, str) and (e.startswith('u') or e.startswith('U'))}
    inherited_roles = get_inherited_roles_in_RH(RH)
    inherited_perms = get_inherited_perms_in_RH(RH)
    inherited_users = get_inherited_users_in_RH(RH)

    all_data = dict()
    for u in users:
        assigned_r = {e for e in RH_adj[u] if isinstance(e, int)}
        assigned_p = {e for e in RH_adj[u] if isinstance(e, str) and (e.startswith('p') or e.startswith('P'))}

        all_data[u] = {
            'inherited': {
                'perms': set(),
                'roles': set(),
            },
            'assigned': {
                'perms': assigned_p,
                'roles': assigned_r,
            }
        }

        for r in assigned_r:
            all_data[u]['inherited']['perms'].update(inherited_perms[r])
            all_data[u]['inherited']['roles'].update(inherited_roles[r])

    for r in RH:
        assigned_r = {e for e in RH_adj[r] if isinstance(e, int)}
        assigned_p = {e for e in RH_adj[r] if isinstance(e, str) and (e.startswith('p') or e.startswith('P'))}

        all_data[r] = {
            'inherited': {
                'perms': set(),
                'roles': set(),
            },
            'assigned': {
                'perms': assigned_p,
                'roles': assigned_r,
            }
        }

        for s in assigned_r:
            all_data[r]['inherited']['perms'].update(inherited_perms[s])
            all_data[r]['inherited']['roles'].update(inherited_roles[s])

    print('ALL DATA')
    pprint(all_data)
    common_roles_user_map = dict()
    for u in users:
        assigned_r = all_data[u]['assigned']['roles']

        common_roles_for_u = set()
        for r1 in assigned_r:
            for r2 in assigned_r:
                if r1 == r2: continue
                assigned_inherited_roles_r1 = all_data[r1]['inherited']['roles'].union(all_data[r1]['assigned'][
                                                                                           'roles'])
                assigned_inherited_roles_r2 = all_data[r2]['inherited']['roles'].union(all_data[r2]['assigned'][
                                                                                           'roles'])
                common_roles = assigned_inherited_roles_r1.intersection(assigned_inherited_roles_r2)
                common_roles_for_u = common_roles_for_u.union(common_roles)
        common_roles_user_map[u] = common_roles_for_u

    print('Common roles user map: ')
    pprint(common_roles_user_map)
    for u in common_roles_user_map:
        # common users assigned or inherited by all roles in common_roles
        u_common_roles = common_roles_user_map[u]
        for cr in u_common_roles:
            users_cr = inherited_users[cr]
            assigned_users_cr = {e for e in RH[cr] if isinstance(e, str) and (e.startswith('u') or e.startswith('U'))}
            users_cr = users_cr.union(assigned_users_cr) - {u}
            can_be_deleted = True
            for u1 in users_cr:
                u1_common_roles = common_roles_user_map[u1]
                if u_common_roles.intersection(u1_common_roles) != u_common_roles:
                    can_be_deleted = False
            if can_be_deleted:
                for u1 in users_cr:
                    roles_assigned_to_u = {e for e in RH_adj[u] if isinstance(e, int)}
                    roles_assigned_to_u1 = {e for e in RH_adj[u1] if isinstance(e, int)}
                    common_roles_u_u1 = roles_assigned_to_u.intersection(roles_assigned_to_u1)
                    for r in common_roles_u_u1:
                        print(f'Common roles by {u}, {u1} : {r}')

    pass


def main(args):
    MAXSETSBP = 'maxsetsbp'
    MINEDGE_FROM_MINROLE = 'mefmr'

    upfilename = args.input_file
    up, usermap, permmap = readup_and_usermap_permmap(upfilename)

    rbac_algorithm = args.rbac_algorithm
    # MINEDGES FROM MINROLES
    if rbac_algorithm == MINEDGE_FROM_MINROLE:
        emfilename = upfilename + "-em.txt"
        em = readem(emfilename)
        up, usermap, permmap = readup_and_usermap_permmap(upfilename)
        role_usermap, role_permmap = minrole_to_minedge(up, em, 86400, 60)
        roles_minedges_from_minroles = dict()
        for r in role_usermap:
            roles_minedges_from_minroles[r] = set()
            for u in role_usermap[r]:
                for p in role_permmap[r]:
                    roles_minedges_from_minroles[r].add((u, p))
        roles = roles_minedges_from_minroles

    else:
        # roles, _ = greedythenlattice_greedy.run(upfilename)
        # u_name = upfilename.split('/')[-1]
        # rbac_fname = f'MERGED_RBAC_{u_name}'
        # roles = read_rbac_file(rbac_fname)
        num_roles, roles = maxsetsbp.run(upfilename)
        roles = {idx: roles[idx] for idx in range(len(roles))}

    RH = rbac_to_rh_no_new_roles(upfilename, roles)

    RH_to_write = dict()
    for r in RH:
        RH_to_write[r] = list(RH[r])
    u_name = upfilename.split('/')[-1]
    rh_fname = f'ALG1_RH_{u_name}'
    with open(rh_fname, 'w') as f:
        json.dump(RH_to_write, f, indent=4, sort_keys=True)

    metrics = get_metrics(RH, use_sampling=True)
    # metrics = {}
    return RH, metrics


def all_simple_paths(RH, source, target, edges_to_keep=None, cutoff=None, num_paths_threshold=None):
    if edges_to_keep is None:
        edges_to_keep = set()
    paths = list()
    stack = [(source, iter(RH.get(source, [])), [source])]

    while stack:
        v, it, path = stack[-1]
        if v == target:
            paths.append(path)
            stack.pop()
            if len(path) > num_paths_threshold:
                return paths
            continue
        try:
            w = next(it)
            if (v, w) not in edges_to_keep:
                if w not in path and cutoff is None:
                    stack.append((w, iter(RH.get(w, [])), path + [w]))
            else:
                stack.pop()
        except StopIteration:
            stack.pop()
    return paths


def remove_more_edges_subgraph(RH: dict, up: dict, usermap: dict, permmap: dict, k=10, persolve_time=86400):
    inv_permmap = {v: kk for kk, v in permmap.items()}
    inv_usermap = {v: kk for kk, v in usermap.items()}
    k = min(len(RH), k)
    random_roles = random.sample(RH.keys(), k)
    subRH = dict()
    roles_removed = dict()
    for r in random_roles:
        roles_removed[r] = set()
        subRH[r] = copy.deepcopy(RH[r])
        roles_assigned = {e for e in subRH[r] if isinstance(e, int)}
        for s in roles_assigned:
            # if s not in subgraph of roles, delete it
            if s not in random_roles:
                subRH[r].remove(s)
                roles_removed[r].add(s)

    inherited_perms_sub_rh = get_inherited_perms_in_RH(subRH)
    inherited_users_sub_rh = get_inherited_users_in_RH(subRH)
    inherited_roles_sub_rh = get_inherited_roles_in_RH(subRH)

    up_induced = dict()
    up_induced_mapped = dict()
    all_users = set()
    all_perms_mapped = set()
    for r in subRH:
        assigned_users_r = {e for e in subRH[r] if isinstance(e, str) and (e.startswith('U') or e.startswith('u'))}
        assigned_perms_r = {e for e in subRH[r] if isinstance(e, str) and (e.startswith('P') or e.startswith('p'))}
        assigned_roles_r = {e for e in subRH[r] if isinstance(e, int)}

        all_users_r = inherited_users_sub_rh[r].union(assigned_users_r)
        all_perms_r = inherited_perms_sub_rh[r].union(assigned_perms_r)
        all_roles_r = inherited_roles_sub_rh[r].union(assigned_roles_r)
        all_users = all_users.union(all_users_r)
        all_perms_mapped = all_perms_mapped.union(all_perms_r)

        all_perms_r_unmapped = {permmap[p] for p in all_perms_r}
        for U in all_users_r:
            u = usermap[U]
            if u not in up_induced:
                up_induced[u] = set()
            up_induced[u] = up_induced[u].union(up[u] & all_perms_r_unmapped)
            up_induced_mapped[U] = {inv_permmap[p] for p in up_induced[u]}
    print('Calling remove more edges')
    subRH = remove_more_edges(subRH, up_induced, usermap, permmap, persolve_time=persolve_time)

    # consolidate roles back
    RH_new = copy.deepcopy(RH)
    for r in subRH:
        RH_new[r] = subRH[r]
        for rr in roles_removed[r]:
            if rr not in RH_new:
                print(f'Role {rr} not in RH_new')
                print(f'Missing perms {rr} -> RH[rr]')
            else:
                print(f'Adding {rr} back')
                RH_new[r].add(rr)

    return RH_new


def minimize_edges_subgraph(RH: dict, up: dict, usermap: dict, permmap: dict, k=10, persolve_time=86400):
    inv_permmap = {v: kk for kk, v in permmap.items()}
    inv_usermap = {v: kk for kk, v in usermap.items()}
    k = min(len(RH), k)
    random_roles = random.sample(RH.keys(), k)
    subRH = dict()
    roles_removed = dict()
    for r in random_roles:
        roles_removed[r] = set()
        subRH[r] = copy.deepcopy(RH[r])
        roles_assigned = {e for e in subRH[r] if isinstance(e, int)}
        for s in roles_assigned:
            # if s not in subgraph of roles, delete it
            if s not in random_roles:
                subRH[r].remove(s)
                roles_removed[r].add(s)

    inherited_perms_sub_rh = get_inherited_perms_in_RH(subRH)
    inherited_users_sub_rh = get_inherited_users_in_RH(subRH)
    inherited_roles_sub_rh = get_inherited_roles_in_RH(subRH)

    up_induced = dict()
    up_induced_mapped = dict()

    for r in subRH:
        assigned_users_r = {e for e in subRH[r] if isinstance(e, str) and (e.startswith('U') or e.startswith('u'))}
        assigned_perms_r = {e for e in subRH[r] if isinstance(e, str) and (e.startswith('P') or e.startswith('p'))}
        assigned_roles_r = {e for e in subRH[r] if isinstance(e, int)}

        all_users_r = inherited_users_sub_rh[r].union(assigned_users_r)
        all_perms_r = inherited_perms_sub_rh[r].union(assigned_perms_r)
        all_roles_r = inherited_roles_sub_rh[r].union(assigned_roles_r)

        # all_perms = {permmap[p] for p in all_perms_mapped}
        all_perms_r_unmapped = {permmap[p] for p in all_perms_r}
        for U in all_users_r:
            u = usermap[U]
            if u not in up_induced:
                up_induced[u] = set()
            up_induced[u] = up_induced[u].union(all_perms_r_unmapped)
            up_induced_mapped[U] = {inv_permmap[p] for p in up_induced[u]}
    print('Calling minimize edges')
    subRH = minimize_edges(subRH, up_induced, usermap, permmap, edges_to_keep=set(), persolve_time=persolve_time)

    # consolidate roles back
    RH_new = copy.deepcopy(RH)
    for r in subRH:
        RH_new[r] = subRH[r]
        for rr in roles_removed[r]:
            if rr not in RH_new:
                print(f'Role {rr} not in RH_new')
                print(f'Missing perms {rr} -> RH[rr]')
            else:
                print(f'Adding {rr} back')
                RH_new[r].add(rr)


    return RH_new


def remove_more_edges_orig(RH: dict, up: dict, usermap: dict, permmap: dict, persolve_time=86400):
    signal.signal(signal.SIGALRM, sighandler)
    signal.alarm(0)
    TIMELIMIT = persolve_time

    m = gp.Model('RH_remove_redundant_edges')
    inv_permmap = {v: k for k, v in permmap.items()}
    inv_usermap = {v: k for k, v in usermap.items()}

    RH_adj = RH_to_adj(RH)
    ur_vars = set()
    rp_vars = set()

    ur_vars_dict = dict()
    user_entry_exit_dict = dict()
    perm_entry_exit_dict = dict()
    rp_vars_dict = dict()
    signal.alarm(TIMELIMIT)
    print('Adding variables')
    timeone = time.time()
    try:
        for u in tqdm(up):
            U = inv_usermap[u]
            for p in up[u]:
                P = inv_permmap[p]
                entry_exit_roles = get_entry_exit_roles_for_user_perm(U, P, RH, RH_adj)
                if len(entry_exit_roles) == 0:
                    print(f'U:{U} -> {P}, entry_exit: {entry_exit_roles}')
                entry_exit_vars = set()

                for (entry_r, exit_r) in entry_exit_roles:
                    # VARIABLES
                    ur = None
                    if len(m.getVars()) == 0:
                        ur = m.addVar(name=f'ur_{U}_{entry_r}', vtype=GRB.BINARY, lb=0, ub=1)
                    else:
                        ur = m.getVarByName(f'ur_{U}_{entry_r}')
                        if not ur:
                            ur = m.addVar(name=f'ur_{U}_{entry_r}', vtype=GRB.BINARY, lb=0, ub=1)
                    # m.update()

                    rp = m.getVarByName(f'rp_{exit_r}_{P}')
                    if not rp:
                        rp = m.addVar(name=f'rp_{exit_r}_{P}', vtype=GRB.BINARY, lb=0, ub=1)
                    # m.update()
                    ur_vars.add(ur)
                    rp_vars.add(rp)

                    v = m.getVarByName(name=f'v_{U}_{entry_r}_{exit_r}_{P}')
                    if not v:
                        v = m.addVar(name=f'v_{U}_{entry_r}_{exit_r}_{P}', vtype=GRB.BINARY, lb=0, ub=1)

                    RH_G = dict_to_digraph(RH_adj)
                    if not nx.has_path(RH_G, entry_r, exit_r):
                        v.LB = 0
                        v.UB = 0

                    # m.update()
                    entry_exit_vars.add(v)

                    if (u, entry_r) not in ur_vars_dict:
                        ur_vars_dict[(u, entry_r)] = set()
                    ur_vars_dict[(u, entry_r)].add(ur)

                    if (u, entry_r) not in user_entry_exit_dict:
                        user_entry_exit_dict[(u, entry_r)] = set()
                    user_entry_exit_dict[(u, entry_r)].add(v)

                    if (exit_r, p) not in rp_vars_dict:
                        rp_vars_dict[(exit_r, p)] = set()
                    rp_vars_dict[(exit_r, p)].add(rp)

                    if (exit_r, p) not in perm_entry_exit_dict:
                        perm_entry_exit_dict[(exit_r, p)] = set()
                    perm_entry_exit_dict[(exit_r, p)].add(v)

                    # m.addConstr(ur >= v, name=f'ur_{U}_{entry_r}_needed')
                    # m.addConstr(rp >= v, name=f'rp_{exit_r}_{P}_needed')
                    m.addConstr(ur >= v)
                    m.addConstr(rp >= v)

                # m.update()

                # for (u1, r) in ur_vars_dict:
                #     for ur in ur_vars_dict[(u1, r)]:
                #         n = len(user_entry_exit_dict[(u1, r)])
                # m.addConstr(ur >= gp.quicksum(user_entry_exit_dict[(u1, r)]) - (n-1), name=f'ur_{U}_{r}_lower')
                # m.addConstr(ur >= gp.quicksum(user_entry_exit_dict[(u1, r)]), name=f'ur_{U}_{r}')
                # for (r, p1) in rp_vars_dict:
                #     for rp in rp_vars_dict[(r, p1)]:
                #         n = len(perm_entry_exit_dict[(r, p1)])
                # m.addConstr(rp >= gp.quicksum(perm_entry_exit_dict[(r, p1)]) - (n-1), name=f'rp_{r}_{P}_lower')
                # m.addConstr(rp >= gp.quicksum(perm_entry_exit_dict[(r, p1)]), name=f'rp_{r}_{P}')

                # AT LEAST ONE PATH IS USED TO CONNECT EVERY USER AND PERM
                m.addConstr(gp.quicksum(entry_exit_vars) >= 1, name=f'atleast_one_path_{U}_{P}')
        # m.update()
        m.setObjective(gp.quicksum(m.getVars()), GRB.MINIMIZE)
    except Exception as e:
        print('Exception: ', e)
        print('time out!', end=' ')
        sys.stdout.flush()
        signal.alarm(0)
        timetwo = time.time()
        print('Time taken (seconds): ', round(timetwo - timeone))
        return RH

    signal.alarm(0)
    m.setParam(GRB.Param.TimeLimit, float(TIMELIMIT))
    timeone = time.time()
    print('About to call m.optimize()...', end='')
    try:
        m.update()
        m.optimize()
        m.write('model.lp')
    except Exception as e:
        print('Exception: ', e)
        print('time out!', end=' ')
        sys.stdout.flush()
        signal.alarm(0)
        m.terminate()
        timetwo = time.time()
        print('Time taken (seconds): ', round(timetwo - timeone))

    if m.Status == GRB.OPTIMAL:
        print("Optimal objective:", m.objVal)
    elif m.Status == GRB.SUBOPTIMAL:
        print("Suboptimal objective:", m.objVal)
    elif m.Status == GRB.INFEASIBLE:
        print("Model infeasible")
        m.computeIIS()
        m.write("iis.ilp")
        raise SystemExit
    else:
        print("Status:", m.Status)

    user_role_edges_dict = dict()
    perm_role_edges_dict = dict()
    print('ILP Solution')
    for v in m.getVars():
        # print(v.VarName, v.X)

        if v.VarName.startswith('ur_'):
            u = v.VarName.split('_')[1]
            entry_r = int(v.VarName.split('_')[2])
            # exit_r = int(v.VarName.split('_')[3])
            # p = v.VarName.split('_')[4]

            if (u, entry_r) not in user_role_edges_dict:
                user_role_edges_dict[(u, entry_r)] = set()

            # if (exit_r, p) not in perm_role_edges_dict:
            #     perm_role_edges_dict[(exit_r, p)] = set()
            if v.X == 1:
                user_role_edges_dict[(u, entry_r)].add(v)
                # perm_role_edges_dict[(exit_r, p)].add(v)

        elif v.VarName.startswith('rp_'):
            exit_r = int(v.VarName.split('_')[1])
            p = v.VarName.split('_')[2]

            if (exit_r, p) not in perm_role_edges_dict:
                perm_role_edges_dict[(exit_r, p)] = set()
            if v.X == 1:
                perm_role_edges_dict[(exit_r, p)].add(v)

    user_role_edges_to_remove = set()
    perm_role_edges_to_remove = set()

    for (u, r) in user_role_edges_dict:
        if len(user_role_edges_dict[(u, r)]) == 0:
            user_role_edges_to_remove.add((u, r))

    for (r, p) in perm_role_edges_dict:
        if len(perm_role_edges_dict[(r, p)]) == 0:
            perm_role_edges_to_remove.add((r, p))

    print('User-Role edges to remove:', len(user_role_edges_to_remove))
    print('Perm-Role edges to remove:', len(perm_role_edges_to_remove))

    roles_to_remove = set()
    for (u, r) in user_role_edges_to_remove:
        if r in RH and u in RH[r]:
            RH[r].remove(u)
            if len(RH[r]) == 0:
                roles_to_remove.add(r)
    for (r, p) in perm_role_edges_to_remove:
        if r in RH and p in RH[r]:
            RH[r].remove(p)
            if len(RH[r]) == 0:
                roles_to_remove.add(r)

    for r in roles_to_remove:
        RH.pop(r)

    for r in RH:
        RH[r] = RH[r].difference(roles_to_remove)

    RH = remove_redundant_roles(RH)
    RH = remove_redundant_edges(RH)
    # RH = remove_redundant_role_role_edges(roles, RH, up, usermap, permmap)
    return RH


def remove_more_edges(RH: dict, up: dict, usermap: dict, permmap: dict, persolve_time=86400):
    signal.signal(signal.SIGALRM, sighandler)
    signal.alarm(0)
    TIMELIMIT = persolve_time

    m = gp.Model('RH_remove_redundant_edges')
    inv_permmap = {v: k for k, v in permmap.items()}
    inv_usermap = {v: k for k, v in usermap.items()}

    RH_adj = RH_to_adj(RH)

    signal.alarm(TIMELIMIT)
    print('Adding variables')
    timeone = time.time()
    up_entry_exit_roles = dict()
    try:
        for u in up:
            U = inv_usermap[u]
            for p in up[u]:
                P = inv_permmap[p]
                entry_exit_roles = get_entry_exit_roles_for_user_perm(U, P, RH, RH_adj)
                if len(entry_exit_roles) == 0:
                    print(f'U:{U} -> {P}, entry_exit: {entry_exit_roles}')
                up_entry_exit_roles[(u, p)] = list(entry_exit_roles)

        entry_exit_roles_vars_map = dict()
        ur_vars_map = dict()
        rp_vars_map = dict()
        for (u, p) in tqdm(up_entry_exit_roles, desc='(user, perm)'):
            U = inv_usermap[u]
            P = inv_permmap[p]

            for (entry_r, exit_r) in up_entry_exit_roles[(u, p)]:
                ur = m.addVar(name=f'ur_{U}_{entry_r}', vtype=GRB.BINARY, lb=0, ub=1)
                rp = m.addVar(name=f'rp_{exit_r}_{P}', vtype=GRB.BINARY, lb=0, ub=1)
                v = m.addVar(name=f'v_{U}_{entry_r}_{exit_r}_{P}', vtype=GRB.BINARY, lb=0, ub=1)

                ur_vars_map[f'ur_{U}_{entry_r}'] = ur
                rp_vars_map[f'rp_{exit_r}_{P}'] = rp
                entry_exit_roles_vars_map[f'v_{U}_{entry_r}_{exit_r}_{P}'] = v

        m.update()

        for (u, p) in up_entry_exit_roles:
            U = inv_usermap[u]
            P = inv_permmap[p]
            entry_exit_vars = set()
            for (entry_r, exit_r) in up_entry_exit_roles[(u, p)]:
                ur = ur_vars_map[f'ur_{U}_{entry_r}']
                rp = rp_vars_map[f'rp_{exit_r}_{P}']
                v = entry_exit_roles_vars_map[f'v_{U}_{entry_r}_{exit_r}_{P}']
                entry_exit_vars.add(v)
                m.addConstr(ur >= v)
                m.addConstr(rp >= v)

            m.addConstr(gp.quicksum(entry_exit_vars) >= 1, name=f'atleast_one_path_{U}_{P}')

        m.setObjective(gp.quicksum(m.getVars()), GRB.MINIMIZE)
    except Exception as e:
        print('Exception: ', e)
        print('time out!', end=' ')
        sys.stdout.flush()
        signal.alarm(0)
        timetwo = time.time()
        print('Time taken (seconds): ', round(timetwo - timeone))
        return RH

    signal.alarm(0)
    m.setParam(GRB.Param.TimeLimit, float(TIMELIMIT))
    timeone = time.time()
    print('About to call m.optimize()...', end='')
    try:
        m.update()
        m.optimize()
        m.write('model.lp')
    except Exception as e:
        print('Exception: ', e)
        print('time out!', end=' ')
        sys.stdout.flush()
        signal.alarm(0)
        m.terminate()
        timetwo = time.time()
        print('Time taken (seconds): ', round(timetwo - timeone))

    if m.Status == GRB.OPTIMAL:
        print("Optimal objective:", m.objVal)
    elif m.Status == GRB.SUBOPTIMAL:
        print("Suboptimal objective:", m.objVal)
    elif m.Status == GRB.INFEASIBLE:
        print("Model infeasible")
        m.computeIIS()
        m.write("iis.ilp")
        raise SystemExit
    else:
        print("Status:", m.Status)

    user_role_edges_dict = dict()
    perm_role_edges_dict = dict()
    print('ILP Solution')
    for v in m.getVars():
        # print(v.VarName, v.X)

        if v.VarName.startswith('ur_'):
            u = v.VarName.split('_')[1]
            entry_r = int(v.VarName.split('_')[2])
            # exit_r = int(v.VarName.split('_')[3])
            # p = v.VarName.split('_')[4]

            if (u, entry_r) not in user_role_edges_dict:
                user_role_edges_dict[(u, entry_r)] = set()

            # if (exit_r, p) not in perm_role_edges_dict:
            #     perm_role_edges_dict[(exit_r, p)] = set()
            if v.X == 1:
                user_role_edges_dict[(u, entry_r)].add(v)
                # perm_role_edges_dict[(exit_r, p)].add(v)

        elif v.VarName.startswith('rp_'):
            exit_r = int(v.VarName.split('_')[1])
            p = v.VarName.split('_')[2]

            if (exit_r, p) not in perm_role_edges_dict:
                perm_role_edges_dict[(exit_r, p)] = set()
            if v.X == 1:
                perm_role_edges_dict[(exit_r, p)].add(v)

    user_role_edges_to_remove = set()
    perm_role_edges_to_remove = set()

    for (u, r) in user_role_edges_dict:
        if len(user_role_edges_dict[(u, r)]) == 0:
            user_role_edges_to_remove.add((u, r))

    for (r, p) in perm_role_edges_dict:
        if len(perm_role_edges_dict[(r, p)]) == 0:
            perm_role_edges_to_remove.add((r, p))

    print('User-Role edges to remove:', len(user_role_edges_to_remove))
    print('Perm-Role edges to remove:', len(perm_role_edges_to_remove))

    roles_to_remove = set()
    for (u, r) in user_role_edges_to_remove:
        if r in RH and u in RH[r]:
            RH[r].remove(u)
            if len(RH[r]) == 0:
                roles_to_remove.add(r)
    for (r, p) in perm_role_edges_to_remove:
        if r in RH and p in RH[r]:
            RH[r].remove(p)
            if len(RH[r]) == 0:
                roles_to_remove.add(r)

    for r in roles_to_remove:
        RH.pop(r)

    for r in RH:
        RH[r] = RH[r].difference(roles_to_remove)

    RH = remove_redundant_roles(RH)
    RH = remove_redundant_edges(RH)
    # RH = remove_redundant_role_role_edges(roles, RH, up, usermap, permmap)
    return RH


def minimize_edges(RH: dict, up: dict, usermap: dict, permmap: dict, edges_to_keep: set, persolve_time=86400):
    m = gp.Model('RH_minimize_edges')
    inv_permmap = {v: k for k, v in permmap.items()}
    inv_usermap = {v: k for k, v in usermap.items()}

    TIMELIMIT = persolve_time
    signal.alarm(TIMELIMIT)

    timeone = time.time()
    try:
        all_edge_vars = list()
        for r in RH:
            for e in RH[r]:
                if isinstance(e, str):
                    if e.startswith('u') or e.startswith('U'):
                        u_var = m.addVar(name=f'u_{e}_{r}', vtype=GRB.BINARY)
                        all_edge_vars.append(u_var)
                    elif e.startswith('p') or e.startswith('P'):
                        p_var = m.addVar(name=f'p_{r}_{e}', vtype=GRB.BINARY)
                        all_edge_vars.append(p_var)
                elif isinstance(e, int):
                    r_var = m.addVar(name=f'r_{r}_{e}', vtype=GRB.BINARY)
                    all_edge_vars.append(r_var)

        m.update()

        # CONSTRAINTS
        entry_points = dict()
        exit_points = dict()

        entry_roles = dict()
        exit_roles = dict()
        for u in up:
            for r in RH:
                U = inv_usermap[u]
                if U not in entry_points:
                    entry_points[U] = set()
                    entry_roles[U] = set()
                ur = m.getVarByName(name=f'u_{U}_{r}')
                if ur is not None:
                    entry_points[U].add(ur)
                    entry_roles[U].add(r)
            for p in up[u]:
                # there is at least one path from u to p
                P = inv_permmap[p]
                if P not in exit_points:
                    exit_points[P] = set()
                    exit_roles[P] = set()
                for r in RH:
                    rp = m.getVarByName(name=f'p_{r}_{P}')
                    if rp is not None:
                        exit_points[P].add(rp)
                        exit_roles[P].add(r)

        vars_to_optimize = list()
        all_role_role_edges = set()
        role_role_edges_to_test = set()

        for u in tqdm(up, desc='users'):
            U = inv_usermap[u]
            u_entry_points: Set[gp.Var] = entry_points[U]
            entry_roles_to_keep = set()

            for p in up[u]:
                P = inv_permmap[p]
                exit_roles_to_keep = set()

                p_exit_points: Set[gp.Var] = exit_points[P]

                all_paths = list()

                for entry_point in u_entry_points:
                    entry_r = int(entry_point.VarName.split('_')[-1])
                    for exit_point in p_exit_points:
                        exit_r = int(exit_point.VarName.split('_')[1])
                        RH_roles_only = get_RH_roles(RH)
                        all_role_role_edges = all_role_role_edges.union({(r, s) for r in RH_roles_only for s in
                                                                         RH_roles_only[r]})
                        paths = all_simple_paths(RH_roles_only, entry_r, exit_r, edges_to_keep, cutoff=None,
                                                 num_paths_threshold=5)
                        if len(paths) == 0:
                            entry_roles_to_keep.add(entry_r)
                            exit_roles_to_keep.add(exit_r)
                        else:
                            all_paths.extend(paths)

                all_paths = random.sample(all_paths, min(5, len(all_paths)))

                y_vars = []

                for path in all_paths:
                    role_role_edges_to_test = role_role_edges_to_test.union(
                        {(path[i], path[i + 1]) for i in range(len(path) - 1)})
                    edges_on_path = []

                    # get ur1
                    ur1 = m.getVarByName(f'u_{U}_{path[0]}')
                    edges_on_path.append(ur1)
                    # print(U, path[0])
                    vars_to_optimize.append(ur1)

                    # transit points
                    for i in range(len(path) - 1):
                        ri, rj = path[i], path[i + 1]
                        rij = m.getVarByName(f'r_{ri}_{rj}')
                        edges_on_path.append(rij)
                        vars_to_optimize.append(rij)

                    r2p = m.getVarByName(f'p_{path[-1]}_{P}')
                    edges_on_path.append(r2p)
                    vars_to_optimize.append(r2p)

                    # y_varname = ''
                    yk = m.addVar(vtype=GRB.BINARY, name=f"path_{U}_{P}_{'_'.join(map(str, path))}")
                    m.update()
                    y_vars.append(yk)
                    all_edge_vars.append(yk)
                    for evar in edges_on_path:
                        # print(evar)
                        m.addConstr(yk <= evar)
                if y_vars:
                    m.addConstr(gp.quicksum(y_vars) >= 1, name=f"reach_{U}_{P}")
    except Exception as e:
        print('Exception: ', e)
        print('time out!', end=' ')
        sys.stdout.flush()
        signal.alarm(0)
        timetwo = time.time()
        print('Time taken (seconds): ', round(timetwo - timeone))
        return RH

    signal.alarm(0)
    m.setParam(GRB.Param.TimeLimit, float(TIMELIMIT))
    timeone = time.time()
    print('About to call m.optimize()...', end='')
    try:
        m.update()
        # print('All edge vars: ', all_edge_vars)
        m.setObjective(gp.quicksum(all_edge_vars), GRB.MINIMIZE)
        m.optimize()
        m.write('model.lp')
    except Exception as e:
        print('Exception: ', e)
        print('time out!', end=' ')
        sys.stdout.flush()
        signal.alarm(0)
        m.terminate()
        timetwo = time.time()
        print('Time taken (seconds): ', round(timetwo - timeone))

    if m.Status == GRB.OPTIMAL:
        print("Optimal objective:", m.objVal)
    elif m.Status == GRB.INFEASIBLE:
        print("Model infeasible")
        m.computeIIS()
        m.write("iis.ilp")
        raise SystemExit
    else:
        print("Status:", m.Status)

    user_role_edges_to_remove = set()
    perm_role_edges_to_remove = set()
    role_role_edges_to_keep = set()
    for v in m.getVars():

        if v.VarName.startswith('u_'):
            if v.X == 0:
                u = v.VarName.split('_')[1]
                r = int(v.VarName.split('_')[-1])
                user_role_edges_to_remove.add((u, r))

        elif v.VarName.startswith('p_'):
            if v.X == 0:
                p = v.VarName.split('_')[-1]
                r = int(v.VarName.split('_')[1])
                perm_role_edges_to_remove.add((r, p))
        elif v.VarName.startswith('path_'):
            if v.X == 1:
                path_splits = v.VarName.split('_')
                for i in range(3, len(path_splits) - 1):
                    r1 = int(path_splits[i])
                    r2 = int(path_splits[i + 1])
                    role_role_edges_to_keep.add((r1, r2))
                    role_edges_must_be_kept = all_role_role_edges.difference(role_role_edges_to_test)
                    role_role_edges_to_keep = role_role_edges_to_keep.union(role_edges_must_be_kept)

    print('User-Role edges to remove:', len(user_role_edges_to_remove))
    print('Perm-Role edges to remove:', len(perm_role_edges_to_remove))

    all_role_role_edges = set()
    for r in RH:
        roles_assigned_to_r = {e for e in RH[r] if isinstance(e, int)}
        for s in roles_assigned_to_r:
            all_role_role_edges.add((r, s))

    role_role_edges_to_remove = set()
    if len(role_role_edges_to_keep) > 0:
        role_role_edges_to_remove = all_role_role_edges.difference(role_role_edges_to_keep)

        print('Role-Role edges to remove:', len(role_role_edges_to_remove))

    roles_to_remove = set()
    for (u, r) in user_role_edges_to_remove:
        if r in RH and u in RH[r]:
            RH[r].remove(u)
            if len(RH[r]) == 0:
                roles_to_remove.add(r)
    for (r, p) in perm_role_edges_to_remove:
        if r in RH and p in RH[r]:
            RH[r].remove(p)
            if len(RH[r]) == 0:
                roles_to_remove.add(r)
    for (r1, r2) in role_role_edges_to_remove:
        if r1 in RH and r2 in RH[r1]:
            RH[r1].remove(r2)
            if len(RH[r1]) == 0:
                roles_to_remove.add(r1)

    for r in roles_to_remove:
        RH.pop(r)

    for r in RH:
        RH[r] = RH[r].difference(roles_to_remove)
    return RH

def minimize_edges_orig(RH: dict, up: dict, usermap: dict, permmap: dict, edges_to_keep: set, persolve_time=86400):
    m = gp.Model('RH_minimize_edges')
    inv_permmap = {v: k for k, v in permmap.items()}
    inv_usermap = {v: k for k, v in usermap.items()}

    TIMELIMIT = persolve_time
    signal.alarm(TIMELIMIT)

    timeone = time.time()
    try:
        all_edge_vars = list()
        for r in RH:
            for e in RH[r]:
                if isinstance(e, str):
                    if e.startswith('u') or e.startswith('U'):
                        u_var = m.addVar(name=f'u_{e}_{r}', vtype=GRB.BINARY)
                        all_edge_vars.append(u_var)
                    elif e.startswith('p') or e.startswith('P'):
                        p_var = m.addVar(name=f'p_{r}_{e}', vtype=GRB.BINARY)
                        all_edge_vars.append(p_var)
                elif isinstance(e, int):
                    r_var = m.addVar(name=f'r_{r}_{e}', vtype=GRB.BINARY)
                    all_edge_vars.append(r_var)
                    # all_edges.add((r, e))

        # m.update()

        # CONSTRAINTS
        entry_points = dict()
        exit_points = dict()

        entry_roles = dict()
        exit_roles = dict()
        for u in up:
            for r in RH:
                U = inv_usermap[u]
                if U not in entry_points:
                    entry_points[U] = set()
                    entry_roles[U] = set()
                ur = m.getVarByName(name=f'u_{U}_{r}')
                if ur is not None:
                    entry_points[U].add(ur)
                    entry_roles[U].add(r)
            for p in up[u]:
                # there is at least one path from u to p
                P = inv_permmap[p]
                if P not in exit_points:
                    exit_points[P] = set()
                    exit_roles[P] = set()
                for r in RH:
                    rp = m.getVarByName(name=f'p_{r}_{P}')
                    if rp is not None:
                        exit_points[P].add(rp)
                        exit_roles[P].add(r)

        vars_to_optimize = list()
        all_role_role_edges = set()
        role_role_edges_to_test = set()

        for u in tqdm(up, desc='users'):
            U = inv_usermap[u]
            u_entry_points: Set[gp.Var] = entry_points[U]
            entry_roles_to_keep = set()

            for p in up[u]:
                P = inv_permmap[p]
                exit_roles_to_keep = set()

                # print('------------------------------')
                # print(f'Paths from {U} to {P}')

                p_exit_points: Set[gp.Var] = exit_points[P]

                all_paths = list()
                # if common entry and exit points, just use those
                # common_points = u_entry_points.intersection(p_exit_points)
                # if common_points:
                #     u_entry_points = common_points
                #     p_exit_points = common_points

                # print(f'Entry points: {entry_roles[U]}, Exit points: {exit_roles[P]}')

                for entry_point in u_entry_points:
                    entry_r = int(entry_point.VarName.split('_')[-1])
                    for exit_point in p_exit_points:
                        exit_r = int(exit_point.VarName.split('_')[1])
                        RH_roles_only = get_RH_roles(RH)
                        all_role_role_edges = all_role_role_edges.union({(r, s) for r in RH_roles_only for s in
                                                                         RH_roles_only[r]})
                        paths = all_simple_paths(RH_roles_only, entry_r, exit_r, edges_to_keep, cutoff=None,
                                                 num_paths_threshold=5)
                        if len(paths) == 0:
                            entry_roles_to_keep.add(entry_r)
                            exit_roles_to_keep.add(exit_r)
                        else:
                            all_paths.extend(paths)
                        # vars_to_optimize.append(entry_r)
                        # vars_to_optimize.append(exit_r)
                # print(f'all_paths: {len(all_paths)}')
                # print(random.sample(all_paths, min(5, len(all_paths))))
                all_paths = random.sample(all_paths, min(5, len(all_paths)))
                # print(f'all_paths: {len(all_paths)}')

                y_vars = []

                for path in all_paths:
                    role_role_edges_to_test = role_role_edges_to_test.union(
                        {(path[i], path[i + 1]) for i in range(len(path) - 1)})
                    edges_on_path = []

                    # get ur1
                    ur1 = m.getVarByName(f'u_{U}_{path[0]}')
                    edges_on_path.append(ur1)
                    # print(U, path[0])
                    vars_to_optimize.append(ur1)

                    # transit points
                    for i in range(len(path) - 1):
                        ri, rj = path[i], path[i + 1]
                        # print(ri, rj)
                        rij = m.getVarByName(f'r_{ri}_{rj}')
                        edges_on_path.append(rij)
                        vars_to_optimize.append(rij)

                    r2p = m.getVarByName(f'p_{path[-1]}_{P}')
                    edges_on_path.append(r2p)
                    vars_to_optimize.append(r2p)
                    # print(path[-1], P)

                    yk = m.addVar(vtype=GRB.BINARY, name=f"path_{U}_{P}_{'_'.join(map(str, path))}")
                    y_vars.append(yk)
                    all_edge_vars.append(yk)
                    # m.update()
                    for evar in edges_on_path:
                        # print(evar)
                        m.addConstr(yk <= evar)
                    # m.addConstr(yk >= gp.quicksum(edges_on_path) - (len(edges_on_path) - 1))
                # print('-------------')
                if not y_vars:
                    # m.update()
                    # No candidate path in RH for this (U,P) pair  either skip or fail early:
                    # raise ValueError(f"No path in RH for U={U}, P={P}")

                    vars_to_be_1 = list()
                    for entry_r in entry_roles_to_keep:
                        ur1 = m.getVarByName(f'u_{U}_{entry_r}')
                        m.addConstr(ur1 >= 1)
                    for exit_r in exit_roles_to_keep:
                        r2p = m.getVarByName(f'p_{exit_r}_{P}')
                        m.addConstr(r2p >= 1)

                    yk = m.addVar(vtype=GRB.BINARY, name=f"special_path_{U}_{P}")
                    y_vars.append(yk)
                    all_edge_vars.append(yk)

                    # for evar in vars_to_be_1:
                    #     m.addConstr(yk <= evar)
                    m.addConstr(yk >= 1)
                    continue
                else:
                    m.addConstr(gp.quicksum(y_vars) >= 1, name=f"reach_{U}_{P}")
                # m.update()
    except Exception as e:
        print('Exception: ', e)
        print('time out!', end=' ')
        sys.stdout.flush()
        signal.alarm(0)
        timetwo = time.time()
        print('Time taken (seconds): ', round(timetwo - timeone))
        return RH

    signal.alarm(0)
    m.setParam(GRB.Param.TimeLimit, float(TIMELIMIT))
    timeone = time.time()
    print('About to call m.optimize()...', end='')
    try:
        m.update()
        # print('All edge vars: ', all_edge_vars)
        m.setObjective(gp.quicksum(all_edge_vars), GRB.MINIMIZE)
        m.optimize()
        m.write('model.lp')
    except Exception as e:
        print('Exception: ', e)
        print('time out!', end=' ')
        sys.stdout.flush()
        signal.alarm(0)
        m.terminate()
        timetwo = time.time()
        print('Time taken (seconds): ', round(timetwo - timeone))

    if m.Status == GRB.OPTIMAL:
        print("Optimal objective:", m.objVal)
    elif m.Status == GRB.INFEASIBLE:
        print("Model infeasible")
        m.computeIIS()
        m.write("iis.ilp")
        raise SystemExit
    else:
        print("Status:", m.Status)

    user_role_edges_to_remove = set()
    perm_role_edges_to_remove = set()
    role_role_edges_to_keep = set()
    for v in m.getVars():

        if v.VarName.startswith('u_'):
            if v.X == 0:
                u = v.VarName.split('_')[1]
                r = int(v.VarName.split('_')[-1])
                user_role_edges_to_remove.add((u, r))

        elif v.VarName.startswith('p_'):
            if v.X == 0:
                p = v.VarName.split('_')[-1]
                r = int(v.VarName.split('_')[1])
                perm_role_edges_to_remove.add((r, p))
        elif v.VarName.startswith('path_'):
            if v.X == 1:
                path_splits = v.VarName.split('_')
                for i in range(3, len(path_splits) - 1):
                    r1 = int(path_splits[i])
                    r2 = int(path_splits[i + 1])
                    role_role_edges_to_keep.add((r1, r2))
                    role_edges_must_be_kept = all_role_role_edges.difference(role_role_edges_to_test)
                    role_role_edges_to_keep = role_role_edges_to_keep.union(role_edges_must_be_kept)

    print('User-Role edges to remove:', len(user_role_edges_to_remove))
    print('Perm-Role edges to remove:', len(perm_role_edges_to_remove))

    all_role_role_edges = set()
    for r in RH:
        roles_assigned_to_r = {e for e in RH[r] if isinstance(e, int)}
        for s in roles_assigned_to_r:
            all_role_role_edges.add((r, s))

    role_role_edges_to_remove = set()
    if len(role_role_edges_to_keep) > 0:
        role_role_edges_to_remove = all_role_role_edges.difference(role_role_edges_to_keep)

        print('Role-Role edges to remove:', len(role_role_edges_to_remove))

    roles_to_remove = set()
    for (u, r) in user_role_edges_to_remove:
        if r in RH and u in RH[r]:
            RH[r].remove(u)
            if len(RH[r]) == 0:
                roles_to_remove.add(r)
    for (r, p) in perm_role_edges_to_remove:
        if r in RH and p in RH[r]:
            RH[r].remove(p)
            if len(RH[r]) == 0:
                roles_to_remove.add(r)
    for (r1, r2) in role_role_edges_to_remove:
        if r1 in RH and r2 in RH[r1]:
            RH[r1].remove(r2)
            if len(RH[r1]) == 0:
                roles_to_remove.add(r1)

    for r in roles_to_remove:
        RH.pop(r)

    for r in RH:
        RH[r] = RH[r].difference(roles_to_remove)
    return RH


def get_RH_roles(RH: dict):
    RH_roles_only = dict()
    for r in RH:
        if r not in RH_roles_only:
            RH_roles_only[r] = set()
        for e in RH[r]:
            if isinstance(e, int):
                RH_roles_only[r].add(e)
    return RH_roles_only


def partition_graph_mincut(RH: dict):
    RH_roles_only = get_RH_roles(RH)
    RH_roles_adj = RH_to_adj(RH_roles_only)
    RH_adj = RH_to_adj(RH)
    users = set()
    perms = set()
    for k in RH_roles_adj:
        if isinstance(k, str):
            if k.startswith('u') or k.startswith('U'):
                users.add(k)
            elif k.startswith('p') or k.startswith('P'):
                perms.add(k)

    G = dict_to_digraph(RH_adj)

    completeG = dict_to_digraph(RH_adj)
    entry_roles = set()
    exit_roles = set()
    for r in RH:
        users_r = {e for e in RH[r] if isinstance(e, str) and (e.startswith('U') or e.startswith('u'))}
        perms_r = {e for e in RH[r] if isinstance(e, str) and (e.startswith('P') or e.startswith('p'))}
        entry_roles = entry_roles.union(users_r)
        exit_roles = exit_roles.union(perms_r)
        # if len(users_r) == 0 and len(perms_r) > 0:
        #     exit_roles.add(r)
        # elif len(perms_r) == 0 and len(users_r) > 0:
        #     entry_roles.add(r)
        # elif len(users_r) > len(perms_r):
        #     entry_roles.add(r)
        # else:
        #     exit_roles.add(r)

    # cut_value, cut_edges, (S, T) = multi_source_sink_min_cut(G, entry_roles, exit_roles)
    cut_value, cut_edges, (S, T) = maxcut(G)
    print(f'cut value: {cut_value}')
    print(f'cut edges: {cut_edges}')
    print(f'S Vertices: {S}')
    print(f'T Vertices: {T}')

    # inherited_perms = get_inherited_perms_in_RH(RH)
    # inherited_users = get_inherited_users_in_RH(RH)
    # inherited_roles = get_inherited_roles_in_RH(RH)

    aug_S = copy.deepcopy(S)
    # for r in RH:
    #     if r in S:
    #         aug_S = aug_S.union(RH[r])
    #
    #         aug_S = aug_S.union(inherited_perms[r])
    #         aug_S = aug_S.union(inherited_users[r])
    #         aug_S = aug_S.union(inherited_roles[r])

    aug_T = copy.deepcopy(T)
    # for r in RH:
    #     if r in T:
    #         aug_T = aug_T.union(RH[r])
    #         aug_T = aug_T.union(inherited_perms[r])
    #         aug_T = aug_T.union(inherited_users[r])
    #         aug_T = aug_T.union(inherited_roles[r])

    left_sub = completeG.subgraph(aug_S).copy()
    right_sub = completeG.subgraph(aug_T).copy()
    left_mapping = dict()
    right_mapping = dict()
    for e in cut_edges:
        if isinstance(e[0], int) and e[0] not in left_mapping:
            left_mapping[e[0]] = f'Prole{e[0]}'
        if isinstance(e[1], int) and e[1] not in right_mapping:
            right_mapping[e[0]] = f'Urole{e[1]}'

    networkx_to_html_with_zoom(left_sub, title="NetworkX from Dict → Interactive HTML", filename="leftsub.html")
    networkx_to_html_with_zoom(right_sub, title="NetworkX from Dict → Interactive HTML", filename="rightsub.html")
    networkx_to_html_with_zoom(completeG, title="NetworkX from Dict → Interactive HTML", filename="complete.html")
    networkx_to_html_with_zoom(G, title="NetworkX from Dict → Interactive HTML", filename="rolesonly.html")

    # nx.relabel_nodes(left_sub, left_mapping, copy=False)
    # nx.relabel_nodes(right_sub, right_mapping, copy=False)
    # leftsub_adj = {n: list(left_sub.neighbors(n)) for n in left_sub.nodes()}
    # rightsub_adj = {n: list(right_sub.neighbors(n)) for n in right_sub.nodes()}

    # leftsub_adj_nodes = set(leftsub_adj.keys())
    # for k in leftsub_adj_nodes:
    #     if len(leftsub_adj[k]) == 0 or k not in S:
    #         leftsub_adj.pop(k)

    edges_to_add_back = set()
    # create a RH format from the adj list
    roles_in_S = {e for e in S if isinstance(e, int)}
    roles_in_T = {e for e in T if isinstance(e, int)}

    leftsub_RH = dict()
    for k in roles_in_S:
        # key is a role, add perms
        if k not in leftsub_RH:
            leftsub_RH[k] = set()
        # add a special permission
        if k in left_mapping:
            leftsub_RH[k].add(f'Prole{k}')
        for e in RH[k]:
            # if isinstance(e, int) or (isinstance(e, str) and (e.startswith('P') or e.startswith('p'))):
            if e in S:
                leftsub_RH[k].add(e)
            else:
                edges_to_add_back.add((k, e))

    rightsub_RH = dict()
    for k in roles_in_T:
        # key is a role, add perms
        if k not in rightsub_RH:
            rightsub_RH[k] = set()
        # add a special user
        if k in right_mapping:
            rightsub_RH[k].add(f'Urole{k}')
        for e in RH[k]:
            # if isinstance(e, int) or (isinstance(e, str) and (e.startswith('P') or e.startswith('p'))):
            if e in T:
                rightsub_RH[k].add(e)
            else:
                edges_to_add_back.add((k, e))

    for (e, f) in cut_edges:
        # if e is a user and f is a role
        if isinstance(e, str) and (e.startswith('u') or e.startswith('U')) and isinstance(f, int):
            # add a role to e in S and assign that role perm Prole
            if f not in leftsub_RH:
                leftsub_RH[f] = set()
            leftsub_RH[f].add(e)
            leftsub_RH[f].add(f'Prole{f}')
        elif isinstance(e, str) and (e.startswith('p') or e.startswith('P')) and isinstance(f, int):
            # add a role to e in S and assign that role user Urole
            if f not in leftsub_RH:
                leftsub_RH[f] = set()
            leftsub_RH[f].add(e)
            leftsub_RH[f].add(f'Urole{f}')

        elif isinstance(f, str) and (f.startswith('u') or f.startswith('U')) and isinstance(e, int):
            # add a role to f in T and assign that role perm Prole
            if e not in rightsub_RH:
                rightsub_RH[e] = set()
            rightsub_RH[e].add(f)
            rightsub_RH[e].add(f'Prole{e}')
        elif isinstance(f, str) and (f.startswith('p') or f.startswith('P')) and isinstance(e, int):
            # add a role to f in T and assign that role user Urole
            if e not in rightsub_RH:
                rightsub_RH[e] = set()
            rightsub_RH[e].add(f)
            rightsub_RH[e].add(f'Urole{e}')

        # elif isinstance(k, str) and (k.startswith('U') or k.startswith('u')):
        #     for e in RH_adj[k]:
        #         if e in leftsub_adj and isinstance(e, int):
        #             if e not in leftsub_RH:
        #                 leftsub_RH[e] = set()
        #             leftsub_RH[e].add(k)
        #             # add a special permission
        #             if e in left_mapping:
        #                 leftsub_RH[e].add(f'Prole{e}')

    # rightsub_adj_nodes = set(rightsub_adj.keys())
    # for k in rightsub_adj_nodes:
    #     if len(rightsub_adj[k]) == 0 or k in S:
    #         rightsub_adj.pop(k)

    # elif isinstance(k, str) and (k.startswith('U') or k.startswith('u')):
    #     for e in RH_adj[k]:
    #         if e in rightsub_adj and isinstance(e, int):
    #             if e not in rightsub_RH:
    #                 rightsub_RH[e] = set()
    #             rightsub_RH[e].add(k)
    #             # add a special user
    #             if e in right_mapping:
    #                 rightsub_RH[e].add(f'Urole{e}')
    return cut_edges, leftsub_RH, rightsub_RH, left_mapping, right_mapping, edges_to_add_back


def multi_source_sink_min_cut(G: nx.DiGraph, sources, sinks):
    GG = G.copy()
    SS = "__super_source__"
    TT = "__super_sink__"
    GG.add_node(SS)
    GG.add_node(TT)

    for u in sources:
        GG.add_edge(SS, u)
    for p in sinks:
        GG.add_edge(p, TT)

    cut_val, (S, T) = nx.minimum_cut(GG, SS, TT)
    # extract original-edge cutset only (ignore SS/TT arcs)
    cut_edges = {(u, v) for u in S for v in GG.successors(u)
                 if v in T and u != SS and v != TT}
    return cut_val, cut_edges, (S - {SS}, T - {TT})


def maxcut(G: nx.DiGraph):
    try:
        topoG = nx.topological_sort(G)
        UG = G.to_undirected()

        cut_val, (S, T) = nx.approximation.one_exchange(UG)
        cut_edges = {(u, v) for u in S for v in UG.neighbors(u)
                     if v in T}
        return cut_val, cut_edges, (S, T)
    except Exception as e:
        print("No topological ", e)

    # GG = G.copy()
    # SS = "__super_source__"
    # TT = "__super_sink__"
    # GG.add_node(SS)
    # GG.add_node(TT)

    # for u in sources:
    #     GG.add_edge(SS, u)
    # for p in sinks:
    #     GG.add_edge(p, TT)

    # cut_val, (S, T) = nx.approximation.one_exchange(GG)
    # extract original-edge cutset only (ignore SS/TT arcs)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Read input UP file")
    parser.add_argument("input_file", type=str, help="Input UP file")
    parser.add_argument("--rbac_algorithm", required=False, default='maxsetsbp', type=str, help=("Algorithm used to "
                                                                                                 "compute RBAC policy"))
    args = parser.parse_args()
    result = main(args)
    # print(result)
