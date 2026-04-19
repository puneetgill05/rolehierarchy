# when the permission of one role r_s  are a proper subset of those of a second role r_S, one may
# remove the permission of the subset from the superset
import collections
import datetime
import os
import queue
import sys
from itertools import combinations_with_replacement, combinations
from pprint import pprint

import numpy as np

prefix_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(f'{prefix_dir}/..')
sys.path.append(f'{prefix_dir}/../algorithms')
sys.path.append(f'{prefix_dir}/../hierarchical_miner')
print(sys.path)


from greedythenlattice_greedy import run
# from BicliqueCoverToILP import run_greedy_delta
# from maxsetsbp import run
# from greedy import run_greedy
from readup import readup
from utils import (calculate_number_of_edges_in_rbac, check_roles, make_biclique, is_biclique, get_roles_mapped,
                   inverse_map)
from miner import run_miner


# When permissions of one role, r_s, are a proper subset of those of second role, R_S, one may remove the permission of
# the subset from the superset, thus removing edges between roles and permissions, at the expense of adding
# an edge from any user that has R_S in order to also give them role r_s
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


def heuristic2_users(role1, role2, threshold):
    role1_users = {e[0] for e in role1}
    role1_permissions = {e[1] for e in role1}
    role2_users = {e[0] for e in role2}
    role2_permissions = {e[1] for e in role2}

    common_users = role1_users.intersection(role2_users)
    min_num_users = min(len(role1_users), len(role2_users))
    issubset = role1_users.issubset(role2_users) or role2_users.issubset(role1_users)
    new_role1 = role1.copy()
    new_role2 = role2.copy()

    if role1 != role2 and not issubset and len(common_users) / min_num_users >= threshold:
        new_role = {(u, p) for u in common_users for p in role1_permissions}.union(
            {(u, p) for u in common_users for p in role2_permissions})

        # remove edges from both roles
        edges_to_remove_from_role1 = set()
        edges_to_remove_from_role2 = set()

        for e in new_role:
            if e[1] in role1_permissions:
                edges_to_remove_from_role1.add(e)
            if e[1] in role2_permissions:
                edges_to_remove_from_role2.add(e)
        new_role1 = new_role1.difference(edges_to_remove_from_role1)
        new_role2 = new_role2.difference(edges_to_remove_from_role2)
        return new_role1, new_role2, new_role
    return new_role1, new_role2, set()


def heuristic2_perms(role1, role2, threshold):
    role1_users = {e[0] for e in role1}
    role1_permissions = {e[1] for e in role1}
    role2_users = {e[0] for e in role2}
    role2_permissions = {e[1] for e in role2}

    common_perms = role1_permissions.intersection(role2_permissions)
    min_num_perms = min(len(role1_permissions), len(role2_permissions))
    issubset = role1_permissions.issubset(role2_permissions) or role2_permissions.issubset(role1_permissions)
    new_role1 = role1.copy()
    new_role2 = role2.copy()

    if role1 != role2 and not issubset and len(common_perms) / min_num_perms >= threshold:
        new_role = {(u, p) for u in role1_users for p in common_perms}.union(
            {(u, p) for u in role2_users for p in common_perms})

        # remove edges from both roles
        edges_to_remove_from_role1 = set()
        edges_to_remove_from_role2 = set()

        for e in new_role:
            if e[0] in role1_users:
                edges_to_remove_from_role1.add(e)
            if e[0] in role2_users:
                edges_to_remove_from_role2.add(e)
        new_role1 = new_role1.difference(edges_to_remove_from_role1)
        new_role2 = new_role2.difference(edges_to_remove_from_role2)
        return new_role1, new_role2, new_role
    return new_role1, new_role2, set()


def run_heuristic2(roles: list, up: dict, min_num_edges_so_far: int, threshold: float) -> list:
    new_roles = roles.copy()
    iter = 0
    while True:
        roles = new_roles.copy()
        new_roles_before = new_roles.copy()
        # roles_prev = roles.copy()
        print('Heuristic 2 for PERMISSIONS, iteration: ', iter)
        print('min # edges so far: ', min_num_edges_so_far)
        print('# roles so far: ', len(roles))
        for r1, r2 in combinations(roles, 2):
            # print('Roles checked: ', (r1, r2))
            new_r1, new_r2, new_r = heuristic2_perms(r1, r2, threshold)
            # add the new role to roles
            if len(new_r) > 0:
                roles.append(new_r)
            # add updated roles to roles
            if new_r1 not in roles:
                roles.append(new_r1)
                if r1 in roles:
                    roles.remove(r1)
            if new_r2 not in roles:
                roles.append(new_r2)
                if r2 in roles:
                    roles.remove(r2)
            # remove old roles
            # if r1 in roles:
            #     roles.remove(r1)
            # if r2 in roles:
            #     roles.remove(r2)
            # check if we still satisfy the up. If not, revert back
            # if not check_roles(roles, up):
            #     roles = roles_prev

            # calculate and compare the number of edges, if lower, then update new_roles
            num_edges_now = calculate_number_of_edges_in_rbac(roles)
            # if number of edges decrease, then add these new roles
            if num_edges_now < min_num_edges_so_far:
                new_roles = roles.copy()
                min_num_edges_so_far = num_edges_now
            # roles = roles_prev

        # if new_roles did not change after trying all combinations of roles, then stop
        if new_roles_before == new_roles:
            break
        iter += 1

    new_roles = remove_empty(new_roles)
    new_roles = get_unique_items(new_roles)

    # roles = new_roles.copy()
    #
    # new_roles = roles.copy()
    iter = 0
    while True:
        roles = new_roles.copy()
        new_roles_before = new_roles.copy()
        # roles_prev = roles.copy()
        print('Heuristic 2 for USERS, iteration: ', iter)
        print('min # edges so far: ', min_num_edges_so_far)
        print('# roles so far: ', len(roles))
        for r1, r2 in combinations(roles, 2):
            # print('Roles checked: ', (r1, r2))
            new_r1, new_r2, new_r = heuristic2_users(r1, r2, threshold)
            # add the new role to roles
            if len(new_r) > 0:
                roles.append(new_r)
            # add updated roles to roles
            if new_r1 not in roles:
                roles.append(new_r1)
                if r1 in roles:
                    roles.remove(r1)
            if new_r2 not in roles:
                roles.append(new_r2)
                if r2 in roles:
                    roles.remove(r2)
            # remove old roles
            # if r1 in roles:
            #     roles.remove(r1)
            # if r2 in roles:
            #     roles.remove(r2)
            # check if we still satisfy the up. If not, revert back
            # if not check_roles(roles, up):
            #     roles = roles_prev

            # calculate and compare the number of edges, if lower, then update new_roles
            num_edges_now = calculate_number_of_edges_in_rbac(roles)
            # if number of edges decrease, then add these new roles
            if num_edges_now < min_num_edges_so_far:
                new_roles = roles.copy()
                min_num_edges_so_far = num_edges_now
            # roles = roles_prev

        # if new_roles did not change after trying all combinations of roles, then stop
        if new_roles_before == new_roles:
            break
        iter += 1

    new_roles = remove_empty(new_roles)
    new_roles = get_unique_items(new_roles)



    return new_roles


def run_heuristic1(roles: list) -> set:
    def are_eq(x: set, y: set):
        return x == y

    def is_in(x: tuple, myset: set) -> bool:
        for item in myset:
            if set(item) == set(x):
                return True
        return False

    def run_heuristic_for(x: set, y: set):
        new_r1, new_r2 = heuristic1(x, y)
        # changed
        if not are_eq(new_r1, x) or not are_eq(new_r2, y):
            new_roles.add(tuple(new_r1))
            new_roles.add(tuple(new_r2))
            roles_changed.add(tuple(x))
            roles_changed.add(tuple(y))

    new_roles = set()
    roles_changed = set()
    for r1, r2 in combinations(roles, 2):
        # are permissions of r1 subset of permissions of r2
        run_heuristic_for(r1, r2)
        # are permissions of r2 subset of permissions of r1
        run_heuristic_for(r2, r1)

    for r in roles:
        if not is_in(r, roles_changed):
            new_roles.add(tuple(r))
    if calculate_number_of_edges_in_rbac(new_roles) > calculate_number_of_edges_in_rbac(roles):
        new_roles = set()
        for r in roles:
            new_roles.add(tuple(r))

    return new_roles

    #         if (role1 != role2 and
    #                 ((role1, role2) not in roles_already_compared or
    #                  (role2, role1) not in roles_already_compared)):
    #             # are permissions of role1 a subset of the permissions of role2?
    #             new_role1, new_role2 = heuristic1(role1, role2)
    #             # if no, then add it to the already compared list
    #             if len(new_role1.symmetric_difference(role1)) == 0 and len(new_role2.symmetric_difference(role2)) == 0:
    #                 roles_already_compared.append((role1, role2))
    #
    #                 #     # check whether permissions of role2 are a subset of the permissions of role1
    #                 new_role1, new_role2 = heuristic1(role2, role1)
    #                 # if no, then add it to the already compared list
    #                 if (len(new_role1.symmetric_difference(role2)) == 0 and len(new_role2.symmetric_difference(role1))
    #                         == 0):
    #                     roles_already_compared.append((role2, role1))
    #
    #                     # roles not changed
    #                     if role1 not in roles_already_changed and role2 not in roles_already_changed:
    #                         roles_already_changed.append(role1)
    #                         roles_already_changed.append(role2)
    #                         if new_role1 not in new_roles:
    #                             new_roles.append(new_role1)
    #                         if new_role2 not in new_roles:
    #                             new_roles.append(new_role2)
    #                 # if yes, add the new roles
    #                 else:
    #                     # roles changed
    #                     roles_already_compared.append((role2, role1))
    #
    #                     # if role1 not in roles_already_changed and role2 not in roles_already_changed:
    #                     roles_already_changed.append(role1)
    #                     roles_already_changed.append(role2)
    #
    #                     if len(new_role1) > 0 and new_role1 not in new_roles:
    #                         new_roles.append(new_role1)
    #                     if len(new_role2) > 0 and new_role2 not in new_roles:
    #                         new_roles.append(new_role2)
    #             # if yes, add the new roles and we don't need to check whether permissions of role2 are a subset
    #             # of the permissions of role1
    #             else:
    #                 # roles changed
    #                 roles_already_compared.append((role1, role2))
    #                 # if role1 not in roles_already_changed and role2 not in roles_already_changed:
    #                 roles_already_changed.append(role1)
    #                 roles_already_changed.append(role2)
    #
    #                 if len(new_role1) > 0 and new_role1 not in new_roles:
    #                     new_roles.append(new_role1)
    #                 if len(new_role2) > 0 and new_role2 not in new_roles:
    #                     new_roles.append(new_role2)
    #     if calculate_number_of_edges_in_roles(new_roles) < calculate_number_of_edges_in_roles(roles):
    #         return new_roles
    # return roles_orig


# def run_heuristic2_take_one(roles: list, up: dict, min_num_edges_so_far: int):
#     new_roles = []
#     for i in range(len(roles)):
#         role1 = roles[i]
#         for j in range(len(roles)):
#             role2 = roles[j]
#             roles_copy = roles.copy()
#
#             if role1 != role2:
#                 new_role1, new_role2, new_role = heuristic2(role1, role2)
#                 if len(new_role) > 0:
#                     if role1 in roles_copy and len(new_role1) > 0:
#                         roles_copy[i] = new_role1
#                         # roles[i] = new_role1
#                     if role2 in roles_copy and len(new_role2) > 0:
#                         roles_copy[j] = new_role2
#                         # roles[j] = new_role2
#
#                     if len(new_role) > 0:
#                         roles_copy.append(new_role)
#                         # roles.append(new_role)
#                     num_edges_now = calculate_number_of_edges_in_roles(roles_copy)
#                     # if number of edges decrease, then add these new roles
#                     if num_edges_now <= min_num_edges_so_far:
#                         new_roles = roles_copy.copy()
#                         min_num_edges_so_far = num_edges_now
#
#     new_roles = remove_empty(new_roles)
#     new_roles = get_unique_items(new_roles)
#
#     # print('Heuristic 2 - new roles:', new_roles)
#     print(f'Number of roles after Heuristics 1 and 2: {len(new_roles)}')
#     num_edges = 0
#     for role in new_roles:
#         num_edges += calculate_number_of_edges(role)
#     print(f'Number of edges after Heuristics 1 and 2: {num_edges}')
#     check_roles(new_roles, up)
#     return new_roles


def main():
    start_time = datetime.datetime.now()
    print('Start time:', start_time)
    sys.stdout.flush()

    if len(sys.argv) != 3:
        print('Usage: ', end='')
        print(sys.argv[0], end=' ')
        print('<input-file> <heuristic-2-threshold>')
        return

    upfilename = sys.argv[1]
    threshold = float(sys.argv[2])
    up = readup(upfilename)

    roles, _ = run(upfilename)
    # roles = run_greedy_delta(upfilename, 50000)

    # _, roles = run(upfilename)
    # roles = run_greedy(upfilename)
    # roles = [{(0, 0), (0, 1), (0, 2)}, {(1, 0), (1, 2)}]
    print(f'Number of roles originally: {len(roles)}')
    roles_dict = dict()
    role_index = 0
    num_edges = calculate_number_of_edges_in_rbac(roles)
    print('Number of edges originally: ', num_edges)

    check_roles(roles, up)

    for role in roles:
        roles_dict[role_index] = dict()
        roles_dict[role_index]['perms'] = {e[1] for e in role}
        roles_dict[role_index]['users'] = {e[0] for e in role}
        role_index += 1

    new_roles = []
    while True:
        if roles == new_roles:
            break
        new_roles = run_heuristic1(roles)
        new_roles = remove_empty(new_roles)
        new_roles = get_unique_items(new_roles)

        # print('Heuristic 1 - roles:', new_roles)
        print(f'Heuristic 1: Number of roles: {len(new_roles)}')
        num_edges = calculate_number_of_edges_in_rbac(new_roles)
        print(f'Number of edges after Heuristic 1: {num_edges}')

        min_num_edges_so_far = num_edges

        # roles = new_roles.copy()
        roles = []
        for role in new_roles:
            # roles.append(make_biclique(set(role)))
            roles.append(set(role))
        new_roles = run_heuristic2(roles.copy(), up, min_num_edges_so_far, threshold)
        print(f'Number of roles after Heuristics 1 and 2: {len(new_roles)}')
        num_edges = calculate_number_of_edges_in_rbac(new_roles)
        print(f'Number of edges after Heuristics 1 and 2: {num_edges}')
        roles = new_roles

    if check_roles(new_roles, up):
        print('RBAC succeeded')
        # print('Roles: ')
        # pprint(get_roles_mapped(new_roles))
    else:
        print('RBAC failed')
    end_time = datetime.datetime.now()
    print('End time:', end_time)
    print('Time taken:', (end_time - start_time).total_seconds(), 'seconds')


def remove_empty(lst):
    newlst = []
    for elem in lst:
        if len(elem) != 0:
            newlst.append(elem)
    return newlst


def get_unique_items(lst):
    newlst = list()
    for item in lst:
        if item not in newlst:
            newlst.append(item)
    return newlst


if __name__ == '__main__':
    main()
