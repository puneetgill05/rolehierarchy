import datetime
import os
import random
import sys

prefix_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(f'{prefix_dir}/..')
print(sys.path)

from BicliqueCoverToILP import greedyBicliqueToILP_opt
from maxsetsbp import run
from largebicliques import run_largebicliques
from readup import readup_and_usermap_permmap, readup
from itertools import chain, combinations

from utils import calculate_delta, calculate_number_of_edges, get_roles_mapped,check_roles, getResults


def powerset(items: set):
    s = tuple(items)
    # Generate the powerset
    all_subsets = tuple(chain.from_iterable(combinations(s, r) for r in range(len(s)+1)))
    # Filter out the empty set and singletons
    filtered_subsets = tuple(subset for subset in all_subsets if len(subset) > 1)
    return filtered_subsets


# def find_matching(up: dict):


def find_minrole_sol(upfilename, percent):
    up, usermap, permmap = readup_and_usermap_permmap(upfilename)
    inv_usermap = {v: k for k, v in usermap.items()}
    inv_permmap = {v: k for k, v in permmap.items()}

    if not up:
        return

    objval, roles = run(upfilename)
    # objval, roles = run_largebicliques(upfilename, 200, )
    print('#Role (using minroles):', objval)
    roles_mapped_back = dict()
    role_index = 0
    num_edges_in_original_sol = 0
    for role in roles:
        new_role = set()
        for item in role:
            new_role.add(inv_usermap[item[0]])
            new_role.add(inv_permmap[item[1]])
        roles_mapped_back[role_index] = new_role
        role_index += 1

        num_edges_in_original_sol += calculate_number_of_edges(role)

    print(objval, roles)
    print(f'Roles created (minroles): {objval}, {len(roles)}')
    print('Edges created (minroles):', num_edges_in_original_sol)

    # get a subset of roles
    role_indices_to_solve_for = random.sample(list(range(len(roles))), int(percent * len(roles)))

    roles_to_solve_for = []
    roles_not_solved_for = []
    for i in range(len(roles)):
        if i in role_indices_to_solve_for:
            roles_to_solve_for.append(roles[i])
        else:
            roles_not_solved_for.append(roles[i])

    new_roles_collected = []

    # add roles that are not used when solving for edges greedily
    for role in roles_not_solved_for:
        if len(role) > 0:
            new_roles_collected.append(role)

    while True:
        rolesprime, new_roles = find2(roles_to_solve_for, up)
        print('Roles remaining:', rolesprime)
        if len(new_roles) == 0:
            break
        for n_role in new_roles:
            if len(n_role) > 0:
                new_roles_collected.append(n_role)
        if len(rolesprime) == 0 or rolesprime == roles_to_solve_for:
            roles_to_solve_for = rolesprime
            break
        roles_to_solve_for = rolesprime

    # FINAL SOLUTION
    # add the roles that are still remaining
    for role in roles_to_solve_for:
        if len(role) > 0:
            new_roles_collected.append(role)
    print('New roles collected: ', new_roles_collected)
    return new_roles_collected


def find2(existing_roles: list, up: dict):
    # create a subgraph based on the existing_roles
    upprime = dict()
    for role in existing_roles:
        for u, p in role:
            if u in upprime:
                upprime[u].add(p)
            else:
                upprime[u] = {p}
    # get an edge greedily based on best delta = #Edges - #Vertices
    up1, sol, new_role_created_mapped = greedyBicliqueToILP_opt(upprime)
    new_role_created = set()
    for elem1 in new_role_created_mapped:
        for elem2 in new_role_created_mapped:
            if elem1 != elem2 and elem1.startswith('u_') and elem2.startswith('p_'):
                new_role_created.add((int(elem1[2:]), int(elem2[2:])))

    new_roles = []
    delta_of_new_role_better = True
    for bc in existing_roles:
        # check if the new role has more than 2 edges
        if calculate_delta(new_role_created) < calculate_delta(bc) or calculate_number_of_edges(new_role_created) <= 2:
        # if calculate_number_of_edges(new_role_created) <= 2:
            delta_of_new_role_better = False
        # check if new role is a subset of the existing role and compare the number of edges in the roles,
        # we want a role with most number of edges "covered" from the input up
        if new_role_created.issubset(bc) and calculate_number_of_edges(new_role_created) < calculate_number_of_edges(bc):
        # if bc.issubset(new_role_created):
            print("# edges new:  ", calculate_number_of_edges(new_role_created))
            print("new role:  ", new_role_created)
            print("# edges existing:  ", calculate_number_of_edges(bc))
            print("existing:  ", bc)
            delta_of_new_role_better = False
    if delta_of_new_role_better:
        print('New role created:', sol, new_role_created)
        roles = consolidate(up, roles=existing_roles, new_role=new_role_created)
        new_roles.append(new_role_created)
        return roles, new_roles
    return existing_roles, new_roles


def consolidate(up: dict, roles: list, new_role: set):
    roles_updated = []
    for role in roles:
        role = set(role)
        roleprime = set()
        roleprime = roleprime.union(role.difference(new_role))
        roles_updated.append(roleprime)
    for role in roles_updated:
        if len(role) == 0:
            roles_updated.remove(role)
    return roles_updated


def main():
    start_time = datetime.datetime.now()
    print('Start time:', start_time)

    if len(sys.argv) != 3:
        print('Usage: ', end='')
        print(sys.argv[0], end=' ')
        print('<input-file> <percent>')
        return

    upfilename = sys.argv[1]
    percent = float(sys.argv[2])

    up = readup(upfilename)
    if not up:
        return

    roles_as_edges = find_minrole_sol(upfilename, percent)
    getResults(roles_as_edges)




    # check_roles(roles_as_edges, up)

    end_time = datetime.datetime.now()
    print('End time:', end_time)
    print('Time taken:', (end_time - start_time).total_seconds(), 'seconds')


if __name__ == '__main__':
    main()

