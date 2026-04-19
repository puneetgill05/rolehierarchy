import datetime
import os
import sys

import networkx as nx
from colorama import Fore
from matplotlib import pyplot as plt

prefix_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(f'{prefix_dir}/..')
print(sys.path)

from minedgerolemining import maxsetsbp
from minedgerolemining.readup import dumpup, readup_and_usermap_permmap


def main():
    start_time = datetime.datetime.now()
    print('Start time:', start_time)
    sys.stdout.flush()

    if len(sys.argv) != 3:
        print('Usage: ', end='')
        print(sys.argv[0], end=' ')
        print('<input-file> <RH levels>')
        return

    orig_upfilename = sys.argv[1]
    upfilename = orig_upfilename

    roles_prefixes = {
        0: 'a',
        1: 'b',
        2: 'c',
        3: 'd',
        4: 'e'
    }

    rh_levels = int(sys.argv[2])
    for level in range(rh_levels):
        up, usermap, permmap = readup_and_usermap_permmap(upfilename)
        inv_usermap = {v: k for k, v in usermap.items()}
        inv_permmap = {v: k for k, v in permmap.items()}
        print(Fore.CYAN + '-------------------------')
        print(Fore.CYAN + 'Level: ', level)
        print(Fore.CYAN + '-------------------------')
        print(Fore.RESET)

        num_roles, roles = maxsetsbp.run(upfilename)
        new_user_role = dict()
        new_perm_role = dict()
        role_index = 0
        for role in roles:
            users = {inv_usermap[e[0]] for e in role}
            perms = {inv_permmap[e[1]] for e in role}
            for user in users:
                if user not in new_user_role:
                    new_user_role[user] = set()

                new_user_role[user].add(f'{roles_prefixes[level]}' + str(role_index))
            for perm in perms:
                if perm not in new_perm_role:
                    new_perm_role[perm] = set()
                new_perm_role[perm].add(f'{roles_prefixes[level]}' + str(role_index))
            role_index += 1
        new_upfilename = orig_upfilename.split('.txt')[0] + '_L' + str(level) + '.txt'
        new_up_permsfilename = orig_upfilename.split('.txt')[0] + '_L' + str(level) + '_perms' + '.txt'
        dumpup(new_user_role, new_upfilename, include_prefixes=False)
        dumpup(new_perm_role, new_up_permsfilename, include_prefixes=False)
        upfilename = new_upfilename

    draw_graph(orig_upfilename, levels=rh_levels)


def get_nodes_at_levels(upfilename: str, levels: int):
    nodes_at_levels = []
    edges = set()
    for level in range(levels):
        level_up_permsfilename = upfilename.split('.txt')[0] + '_L' + str(level) + '_perms' + '.txt'

        # read perms files and create the graph
        level_up, usermap, permmap = readup_and_usermap_permmap(level_up_permsfilename)
        inv_usermap = {v: k for k, v in usermap.items()}
        inv_permmap = {v: k for k, v in permmap.items()}

        nodes_at_level = set()
        for node, neighbors in level_up.items():
            for neighbor in neighbors:
                edges.add((inv_usermap[node], inv_permmap[neighbor]))
            nodes_at_level.add(inv_usermap[node])
        nodes_at_levels.append(nodes_at_level)

    # read the up for the top level
    top_level = levels - 1
    level_upfilename = upfilename.split('.txt')[0] + '_L' + str(top_level) + '.txt'

    # read up files and create the graph
    level_up, usermap, permmap = readup_and_usermap_permmap(level_upfilename)
    inv_usermap = {v: k for k, v in usermap.items()}
    inv_permmap = {v: k for k, v in permmap.items()}
    nodes_at_level_1 = set()
    nodes_at_level_2 = set()
    for node, neighbors in level_up.items():
        for neighbor in neighbors:
            edges.add((inv_usermap[node], inv_permmap[neighbor]))

            nodes_at_level_2.add(inv_permmap[neighbor])
        nodes_at_level_1.add(inv_usermap[node])

    nodes_at_levels.append(nodes_at_level_2)
    nodes_at_levels.append(nodes_at_level_1)
    return nodes_at_levels, edges


def draw_graph(upfilename: str, levels: int):
    G = nx.Graph()

    nodes_at_levels = []
    for level in range(levels):
        level_up_permsfilename = upfilename.split('.txt')[0] + '_L' + str(level) + '_perms' + '.txt'

        # read perms files and create the graph
        level_up, usermap, permmap = readup_and_usermap_permmap(level_up_permsfilename)
        inv_usermap = {v: k for k, v in usermap.items()}
        inv_permmap = {v: k for k, v in permmap.items()}
        nodes_at_level = set()
        for node, neighbors in level_up.items():
            for neighbor in neighbors:
                G.add_edge(inv_usermap[node], inv_permmap[neighbor])
            nodes_at_level.add(inv_usermap[node])
        nodes_at_levels.append(nodes_at_level)

    # read the up for the top level
    top_level = levels - 1
    level_upfilename = upfilename.split('.txt')[0] + '_L' + str(top_level) + '.txt'

    # read up files and create the graph
    level_up, usermap, permmap = readup_and_usermap_permmap(level_upfilename)
    inv_usermap = {v: k for k, v in usermap.items()}
    inv_permmap = {v: k for k, v in permmap.items()}
    nodes_at_level_1 = set()
    nodes_at_level_2 = set()
    for node, neighbors in level_up.items():
        for neighbor in neighbors:
            G.add_edge(inv_usermap[node], inv_permmap[neighbor])
            nodes_at_level_2.add(inv_permmap[neighbor])
        nodes_at_level_1.add(inv_usermap[node])

    nodes_at_levels.append(nodes_at_level_2)
    nodes_at_levels.append(nodes_at_level_1)

    pos = {}
    layer_spacing = levels
    ctr = 1
    for nodes_at_level in nodes_at_levels:
        for i, u in enumerate(sorted(nodes_at_level)):
            pos[u] = (i, ctr * layer_spacing)
        ctr += 1

    # draw
    plt.figure(figsize=(10, 6))
    nx.draw(G, pos, with_labels=True, node_size=1500, node_color='lightgray', edge_color='gray')
    plt.title(f"Role Hierarchy Graph (levels = {levels})")
    plt.show()


if __name__ == '__main__':
    main()
    # draw_graph('/home/puneet/Projects/minedgerolemining/minedgerolemining/inputsup/tripunit_irreducible.txt', 3)
