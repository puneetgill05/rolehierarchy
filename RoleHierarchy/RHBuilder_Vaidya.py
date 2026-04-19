#!/usr/bin/env python3
import argparse
import json
import os
import sys
from collections import defaultdict, deque
from pprint import pprint

from RBAC_to_RH import remove_redundant_edges, check_RH
from RoleHierarchy import RandomWalk

from minedgerolemining import greedythenlattice
from rh_utils import read_rbac_file
from rh_metrics import get_metrics

prefix_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(f'{prefix_dir}/..')
sys.path.append(f'{prefix_dir}/../..')

import greedythenlattice_greedy
import maxsetsbp
from readup import readup_and_usermap_permmap


class RoleHierarchy:
    def __init__(self, roles_perms: dict[int, set]):
        self.roles = {r: set(p) for r, p in roles_perms.items() if p}
        if not self.roles:
            raise ValueError("No non-empty roles provided.")
        # Create a single super role with union of all permissions
        self.SUPER_ROLE = "__SUPER_ROLE__"
        super_perms = set().union(*self.roles.values())
        self.roles[self.SUPER_ROLE] = super_perms

        self.children = defaultdict(set)
        self.E = set()

    def build(self) -> dict[int, set]:
        for r in self.roles:
            if r != self.SUPER_ROLE:
                self._add_edge(self.SUPER_ROLE, r)

        for r in list(self.roles.keys()):
            if r == self.SUPER_ROLE:
                continue
            self._rh_builder_iteration(r, self.SUPER_ROLE)

        return self._adjacency(drop_top=True)

    def _rh_builder_iteration(self, r: int, parent: int):
        if (parent, r) not in self.E:
            self._add_edge(parent, r)

        for ri in list(self.children[parent]):
            if ri == r:
                continue

            Pi, Pr = self.roles[ri], self.roles[r]
            inter = Pi & Pr

            if not inter:
                continue

            # if r is a superset of ri
            if Pr.issuperset(Pi):
                self._remove_edge(parent, ri)
                self._add_edge(r, ri)
                for rj in self._descendants(ri):
                    if (r, rj) in self.E:
                        self._remove_edge(r, rj)
                continue

            if Pr.issubset(Pi):
                self._remove_edge(parent, r)
                self._rh_builder_iteration(r, ri)

            for rj in self._bfs_nodes(ri):
                if self.roles[r].issuperset(self.roles[rj]):
                    self._add_edge(r, rj)
                    for rk in self._descendants(rj):
                        if (r, rk) in self.E:
                            self._remove_edge(r, rk)

    def _add_edge(self, parent: int, child: int):
        if child == parent:
            return
        if (parent, child) not in self.E:
            self.E.add((parent, child))
            self.children[parent].add(child)

    def _remove_edge(self, parent: int, child: int):
        if (parent, child) in self.E:
            self.E.remove((parent, child))
            if child in self.children[parent]:
                self.children[parent].remove(child)

    def _descendants(self, node: str) -> set[str]:
        seen, q = set(), deque(self.children[node])
        while q:
            x = q.popleft()
            if x in seen:
                continue
            seen.add(x)
            for y in self.children[x]:
                if y not in seen:
                    q.append(y)
        return seen

    def _bfs_nodes(self, root: str):
        seen, q = set(), deque([root])
        while q:
            x = q.popleft()
            if x in seen:
                continue
            seen.add(x)
            yield x
            for y in self.children[x]:
                if y not in seen:
                    q.append(y)

    def _adjacency(self, drop_top: bool = True) -> dict[int, set]:
        adj = {u: set(vs) for u, vs in self.children.items()}
        if drop_top:
            adj.pop(self.SUPER_ROLE, None)
        return adj


def compute_layer(r, hierarchy: dict, orig_layer: int, layers: set):
    if r not in hierarchy or len(hierarchy[r]) == 0:
        layers.add(orig_layer)
        return orig_layer
    for s in hierarchy[r]:
        layer = compute_layer(s, hierarchy, orig_layer + 1, layers)
    return max(layers)



def main(args):
    input_file = args.input_file
    upfilename = input_file
    # Example usage
    up, usermap, permmap = readup_and_usermap_permmap(upfilename)
    inv_usermap = {v: k for k, v in usermap.items()}
    inv_permmap = {v: k for k, v in permmap.items()}

    u_name = upfilename.split('/')[-1]
    # rbac_fname = f'MERGED_RBAC_{u_name}'
    # roles = read_rbac_file(rbac_fname)
    # roles = [v for v in roles.values()]
    num_roles, roles = maxsetsbp.run(upfilename)
    #roles, _ = greedythenlattice.run(upfilename)

    roles_perms_dict = dict()
    roles_users_dict = dict()
    r_index = 0
    for role in roles:
        role_perms = {inv_permmap[e[1]] for e in role}
        role_users = {inv_usermap[e[0]] for e in role}
        roles_perms_dict[r_index] = role_perms
        roles_users_dict[r_index] = role_users
        r_index += 1

    # roles_perms = {5: {'p1', 'p2', 'p3', 'p4'}, 0: {'p1', 'p3', 'p4'}, 1: {'p1', 'p2'}, 2: {'p1'}, 3: {'p1', 'p3'}}

    # print('RBAC')
    # pprint(roles_perms_dict)

    rh = RoleHierarchy(roles_perms_dict)
    hierarchy = rh.build()

    for r in roles_perms_dict:
        if r not in hierarchy:
            hierarchy[r] = set()

    # print('hierarchy')
    # pprint(hierarchy)

    RH = dict()
    for r in hierarchy:
        if len(hierarchy[r]) == 0:
            if r not in RH:
                RH[r] = set()
            RH[r].update(roles_perms_dict[r])
            RH[r].update(roles_users_dict[r])
        else:
            if r not in RH:
                RH[r] = set()
            RH[r].update(hierarchy[r])
            RH[r].update(roles_perms_dict[r])
            RH[r].update(roles_users_dict[r])
    for r in hierarchy:
        for s in hierarchy[r]:
            # print(r, s, roles_perms_dict[r] - roles_perms_dict[s], RH[r])
            # print(r, s, roles_users_dict[s] - roles_users_dict[r], RH[r])
            RH[r] = RH[r] - roles_perms_dict[s]
            RH[s] = RH[s] - roles_users_dict[r]
    # RH = remove_redundant_edges(RH)
    check_RH(RH, up, usermap, permmap)

    # print('RH')
    # pprint(RH)
    # UR = {(e, r) for r in RH for e in RH[r] if isinstance(e, str) and (e.startswith('U') or e.startswith('u'))}
    # RP = {(r, e) for r in RH for e in RH[r] if isinstance(e, str) and (e.startswith('P') or e.startswith('p'))}
    # RR = {(r, e) for r in RH for e in RH[r] if isinstance(e, int)}
    #
    # RandomWalk.run_random_walk(UR, RR, RP)

    RH_to_write = dict()
    for r in RH:
        RH_to_write[r] = list(RH[r])
    u_name = upfilename.split('/')[-1]
    rh_fname = f'VAIDYA_RH_{u_name}'
    with open(rh_fname, 'w') as f:
        json.dump(RH_to_write, f, indent=4, sort_keys=True)

    metrics = get_metrics(RH, use_sampling=True)
    return RH, metrics


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Read input UP file")
    parser.add_argument("input_file", type=str, help="Input UP file")

    args = parser.parse_args()
    result = main(args)
    # print(result)
