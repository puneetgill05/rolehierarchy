import random
from collections import deque
from itertools import product
from pprint import pprint
from typing import List


def check_roles_and_fix(roles, up):
    all_edges = set()
    for u in up:
        for p in up[u]:
            all_edges.add((u, p))

    # if the role has a user u, check if all the permissions in the role match the permissions assigned to u in up
    roles_satisfy_up = True
    for role in roles:
        extra_edges = set()
        for u, p in role:
            if p in up[u]:
                continue
            else:
                roles_satisfy_up = False
                # print(f'Added extra edge ({u}, {p})')
                extra_edges.add((u, p))
        for u, p in extra_edges:
            role.remove((u, p))

    # if user u has permission p, check if there is a role assigned to this edge (u, p)

    for e in all_edges:
        edge_found = False
        for role in roles:
            if e in role:
                edge_found = True
        if not edge_found:
            roles_satisfy_up = False
            print(f'Missing edge {e}')
    return roles_satisfy_up


def check_roles(roles, up):
    all_edges = set()
    for u in up:
        for p in up[u]:
            all_edges.add((u, p))

    # if the role has a user u, check if all the permissions in the role match the permissions assigned to u in up
    roles_satisfy_up = True
    for role in roles:
        for u, p in role:
            if u in up and p in up[u]:
                continue
            else:
                roles_satisfy_up = False
                # print(f'Added extra edge ({u}, {p})')
    # if user u has permission p, check if there is a role assigned to this edge (u, p)
    for e in all_edges:
        edge_found = False
        for role in roles:
            if e in role:
                edge_found = True
        if not edge_found:
            roles_satisfy_up = False
            print(f'Missing edge {e}')
    return roles_satisfy_up


def get_users_perms_in_role(role):
    users_in_biclique = set()
    perms_in_biclique = set()
    for e in role:
        users_in_biclique.add(e[0])
        perms_in_biclique.add(e[1])
    return users_in_biclique, perms_in_biclique


def calculate_number_of_edges_in_rbac(roles):
    num_edges = 0
    for role in roles:
        users_in_biclique, perms_in_biclique = get_users_perms_in_role(role)
        num_edges += len(users_in_biclique) + len(perms_in_biclique)
    return num_edges


def calculate_number_of_edges(role):
    users_in_biclique, perms_in_biclique = get_users_perms_in_role(role)
    return len(users_in_biclique) + len(perms_in_biclique)


def calculate_delta(biclique: set):
    users_in_biclique, perms_in_biclique = get_users_perms_in_role(biclique)
    delta = len(users_in_biclique) * len(perms_in_biclique) - len(users_in_biclique) - len(perms_in_biclique)
    return delta


def calculate_number_of_edges_in_up(up: dict):
    num_edges = 0
    for u in up:
        num_edges += len(up[u])
    return num_edges


def get_roles_mapped(roles_as_edges):
    roles_mapped = dict()
    ctr = 0
    for role in roles_as_edges:
        role_set = set()
        for e in role:
            # role_set.add('u_' + str(e[0]))
            # role_set.add('p_' + str(e[1]))
            role_set.add(str(e[0]))
            role_set.add(str(e[1]))
        roles_mapped[ctr] = role_set
        ctr += 1
    return roles_mapped


def get_roles_as_edges(roles_mapped):
    roles_created_as_edges = []
    for role in roles_mapped:
        new_role = set()
        for elem1 in roles_mapped[role]:
            for elem2 in roles_mapped[role]:
                if elem1 != elem2 and elem1.startswith('u_') and elem2.startswith('p_'):
                    new_role.add((int(elem1[2:]), int(elem2[2:])))
                elif elem1 != elem2 and elem1.startswith('u') and elem2.startswith('p'):
                    new_role.add((elem1, elem2))
                else:
                    continue

        roles_created_as_edges.append(new_role)
    return roles_created_as_edges


def make_biclique(role: set):
    users = set()
    perms = set()

    for e in role:
        users.add(e[0])
        perms.add(e[1])

    for u in users:
        for p in perms:
            role.add((u, p))
    return role


def is_biclique(role):
    users = set()
    perms = set()

    for e in role:
        users.add(e[0])
        perms.add(e[1])

    for u in users:
        for p in perms:
            if (u, p) not in role:
                return False
    return True


def bicliques_to_roles_as_edges(bicliques: set):
    roles_as_edges = list()
    for biclique in bicliques:
        users = set()
        perms = set()
        for v in biclique:
            if v.startswith('u_'):
                users.add(int(v[2:]))
            elif v.startswith('p_'):
                perms.add(int(v[2:]))
        role_as_edges = set(product(users, perms))
        roles_as_edges.append(role_as_edges)
    return roles_as_edges


def inverse_map(mymap: dict) -> dict:
    map_inv = dict()
    for k in mymap:
        for v in mymap[k]:
            if v in map_inv:
                map_inv[v].add(k)
            else:
                map_inv[v] = {k}
    return map_inv


def find_partitions(up: dict) -> List[dict]:
    def bfs(node):
        component = []
        q = deque()
        q.append(f'u_{node}')
        explored.add(f'u_{node}')

        while len(q) > 0:
            current = q.popleft()
            component.append(current)

            if current.startswith('u_'):
                for neighbor in up[int(current[2:])]:
                    if f'p_{neighbor}' not in explored:
                        explored.add(f'p_{neighbor}')
                        q.append(f'p_{neighbor}')
            elif current.startswith('p_'):
                for neighbor in up_inv[int(current[2:])]:
                    if f'u_{neighbor}' not in explored:
                        explored.add(f'u_{neighbor}')
                        q.append(f'u_{neighbor}')
        return component

    def create_up_component(component: list, up: dict) -> dict:
        ret = dict()
        for c in component:
            if c.startswith('u_'):
                ret[int(c[2:])] = up[int(c[2:])]
        return ret

    up_inv = inverse_map(up)
    V = {u for u in up}
    explored = set()
    components = []

    for u in V:
        if f'u_{u}' not in explored:
            components.append(bfs(u))

    up_components = list()
    for component in components:
        up_components.append(create_up_component(component, up))

    return up_components


def break_up(up: dict, threshold: int) -> List[dict]:
    num_edges = 0
    ret = []
    curr_up = dict()
    prev_u = None
    for u in up:
        num_edges += len(up[u])
        if num_edges >= threshold:
            num_edges = 0
            if len(curr_up) > 0:
                ret.append(curr_up)
            curr_up = dict()
            curr_up[u] = up[u]
            if prev_u is not None:
                curr_up[prev_u] = up[prev_u]
        else:
            curr_up[u] = up[u]
            prev_u = u
    if len(curr_up) > 0:
        ret.append(curr_up)
    return ret


def getResults(roles_created_as_edges: List):
    roles_created_mapped = get_roles_mapped(roles_created_as_edges)
    # calculate the number of edges belonging to these roles from the original input
    # num_edges_in_bicliques = 0
    # for role in roles_created_as_edges:
    #     num_edges_in_bicliques += len(role)

    # calculate the number of edges in RBAC policy for these roles
    num_edges_created = 0
    for role in roles_created_as_edges:
        num_edges_created += calculate_number_of_edges(role)

    print('Roles: ', roles_created_as_edges)
    print('Roles mapped: ')
    pprint(roles_created_mapped)
    # print('Number of edges in the bicliques at the end of this: ', num_edges_in_bicliques)
    print('Number of edges in the RBAC policy at the end of this: ', num_edges_created)
    print('Number of roles in the RBAC policy at the end of this: ', len(roles_created_mapped))
    return len(roles_created_mapped), num_edges_created


def get_unique_items(lst):
    newlst = list()
    for item in lst:
        if item not in newlst:
            newlst.append(item)
    return newlst