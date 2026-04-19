import heapq
import os
import random
import sys
from collections import deque, defaultdict
from datetime import datetime

import numpy as np
from termcolor import colored


prefix_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(f'{prefix_dir}/..')

from readup import readup, uptopu
from utils import check_roles


def get_max_biclique(user, up: dict, pu: dict):
    common_perms = set()
    common_users = set()
    perms_to_explore = deque(up[user])
    perms_explored = set()
    users_to_explore = deque({user})
    users_explored = set()

    common_perms = common_perms.union(perms_to_explore)
    common_users = common_users.union({user})

    while len(users_to_explore) > 0 and len(perms_to_explore) > 0:
        if len(users_to_explore) > 0:
            # remove one user
            u = users_to_explore.pop()
            # get all the permissions remaining and add it to the to explore queue
            perms_left = up[u].difference(perms_explored)
            if u not in users_explored and len(perms_left) > 0:
                users_explored.add(u)
            for p in perms_left:
                # only add such a permission if all the users in common_users are also in it
                if common_users.issubset(pu[p]):
                    perms_to_explore.append(p)
                    common_perms.add(p)
                    perms_explored.add(p)
        if len(perms_to_explore) > 0:
            # remove one permission
            p = perms_to_explore.pop()
            # get all the users remaining and add it to the to explore queue
            users_left = pu[p].difference(users_explored)
            if p not in perms_explored and len(users_left) > 0:
                perms_explored.add(p)
            for u in users_left:
                # only add such a user if all the permissions in common_perms are also in it
                if common_perms.issubset(up[u]):
                    users_to_explore.append(u)
                    common_users.add(u)
                    users_explored.add(u)

    roles_as_edges = set()
    for u in common_users:
        for p in common_perms:
            roles_as_edges.add((u, p))
    return roles_as_edges

def run_rand_alg(up: dict, rounds: int):
    min_roles_so_far = set()
    min_so_far = np.Inf
    j = 0
    up_orig = up.copy()

    def all_edges_of_u_are_covered(edges_for_u, roles):
        for role in roles:
            if all_edges_for_u.issubset(role):
                return True
        return False

    while j < rounds:
        priority_heap = dict()
        up = up_orig.copy()
        final_roles_as_edges = list()
        users_already_checked = set()

        print('----------------')
        print(f'Iteration: {j}')
        print('----------------')

        for u in up:
            if u not in priority_heap:
                priority_heap[u] = 1
            else:
                priority_heap[u] += 1
        while True:
            if len(up) == 0 or check_roles(final_roles_as_edges, up_orig):
                break


            # while up != new_up:
            new_up = dict()
            # rand_u = random.choice(list(up.keys()))
            inverted_priority = defaultdict(list)
            for k, v in priority_heap.items():
                inverted_priority[v].append(k)
            heap = list(inverted_priority.items())
            heapq.heapify(heap)
            while len(heap) > 0 and len(up) > 0:
                _, rand_us = heapq.heappop(heap)
                rand_u = random.choice(rand_us)
                pu = uptopu(up)

                if rand_u in up:
                    # print(f'Rand u: {rand_u}, up: {up}')

                    role_as_edges = get_max_biclique(rand_u, up, pu)
                    final_roles_as_edges.append(role_as_edges)

                    for u in up:
                        all_edges_for_u = set()
                        for p in up[u]:
                            all_edges_for_u.add((u, p))

                        if not all_edges_of_u_are_covered(all_edges_for_u, final_roles_as_edges):
                            for _,p in all_edges_for_u:
                                if u not in new_up:
                                    new_up[u] = {p}
                                else:
                                    new_up[u].add(p)
                    up = new_up

                    for u,p in role_as_edges:
                        if u not in priority_heap:
                            priority_heap[u] = 1
                        else:
                            priority_heap[u] += 1

            # final_roles_as_edges.append(role_as_edges)
        if len(final_roles_as_edges) < min_so_far:
            min_roles_so_far = final_roles_as_edges.copy()
            min_so_far = len(min_roles_so_far)
        j += 1
    return min_roles_so_far





def main():
    print('Start time:', datetime.now())
    sys.stdout.flush()

    if len(sys.argv) != 3:
        print('Usage: ', end='')
        print(sys.argv[0], end=' ')
        print('<input-file> <num-rounds>')
        return

    upfilepath = sys.argv[1]
    num_rounds = int(sys.argv[2])
    up = readup(upfilepath)

    timeone = datetime.now()
    roles_as_edges = run_rand_alg(up, num_rounds)
    roles_check = check_roles(roles_as_edges, up)
    if roles_check:
        print(colored('RBAC check succeeded', 'white', 'on_green'))
    else:
        print(colored('RBAC check failed', 'white', 'on_red'))
    print('# roles: ', len(roles_as_edges))
    timetwo = datetime.now()
    print(f'Time taken: {(timetwo - timeone).total_seconds()} seconds')


if __name__ == '__main__':
    main()