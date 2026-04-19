#!/usr/bin/env python3

import argparse
import copy
import json
import os
import time
from pathlib import Path
from pprint import pprint
from typing import Dict, Iterable, Any, Set, List, Tuple, Optional
from collections import defaultdict

import networkx as nx

import RBAC_to_RH
from RBAC_to_RH import reconstruct_roles_from_RH
from readup import readup_and_usermap_permmap
import maxsetsbp

from minedgerolemining.RoleHierarchy import RBAC_RH_IP_V2
from minedgerolemining.RoleHierarchy.graph_dict import dict_to_networkx, networkx_to_html_with_zoom
from minedgerolemining.RoleHierarchy.rh_utils import RH_to_adj, dict_to_digraph
from rh_metrics import get_metrics


def read_rh_file(rh_file_path: Path) -> dict:
    RH = json.load(open(rh_file_path, 'r'))
    RH_new = dict()
    for r in RH.keys():
        if isinstance(r, str) and r.isdigit():
            RH_new[int(r)] = set(RH[r])

    for r in RH_new.keys():
        for v in RH_new[r]:
            if isinstance(v, str) and v.isdigit():
                RH_new[r].remove(v)
                RH_new[r].add(int(v))
    return RH_new


def join(existing_rh, rh, up_mapped, usermap, permmap, up):
    new_rh = copy.deepcopy(existing_rh) | copy.deepcopy(rh)
    RBAC_to_RH.check_RH(new_rh, up, usermap, permmap)

    all_perms = set()
    for u in up_mapped:
        all_perms.update(up_mapped[u])

    inherited_perms_exrh = RBAC_to_RH.get_inherited_perms_in_RH(existing_rh)
    inherited_users_exrh = RBAC_to_RH.get_inherited_users_in_RH(existing_rh)
    inherited_roles_exrh = RBAC_to_RH.get_inherited_roles_in_RH(existing_rh)

    inherited_perms_rh = RBAC_to_RH.get_inherited_perms_in_RH(rh)
    inherited_users_rh = RBAC_to_RH.get_inherited_users_in_RH(rh)
    inherited_roles_rh = RBAC_to_RH.get_inherited_roles_in_RH(rh)

    assigned = False
    # find if there is any overlap of roles, i.e. overlap of permissions
    for er in existing_rh:
        assigned_perms_er = {e for e in existing_rh[er] if
                             isinstance(e, str) and (e.startswith('P') or e.startswith('p'))}
        assigned_users_er = {e for e in existing_rh[er] if
                             isinstance(e, str) and (e.startswith('U') or e.startswith('u'))}
        assigned_roles_er = {e for e in existing_rh[er] if isinstance(e, int)}

        all_perms_er = inherited_perms_exrh[er].union(assigned_perms_er)
        all_users_er = inherited_users_exrh[er].union(assigned_users_er)
        all_roles_er = inherited_roles_exrh[er].union(assigned_roles_er)

        for r in rh:
            assigned_perms_r = {e for e in rh[r] if isinstance(e, str) and (e.startswith('P') or e.startswith('p'))}
            assigned_users_r = {e for e in rh[r] if isinstance(e, str) and (e.startswith('U') or e.startswith('u'))}
            assigned_roles_r = {e for e in rh[r] if isinstance(e, int)}

            all_perms_r = inherited_perms_rh[r].union(assigned_perms_r)
            all_users_r = inherited_users_rh[r].union(assigned_users_r)
            all_roles_r = inherited_roles_rh[r].union(assigned_roles_r)

            # check if er can inherit r
            # check if all users of er can inherit perms of r
            req_perms_by_all_users_of_er = all_perms
            for eu in all_users_er:
                req_perms_by_all_users_of_er = req_perms_by_all_users_of_er.intersection(up_mapped[eu])
            if all_perms_r.issubset(req_perms_by_all_users_of_er):
                new_rh[er].add(r)
                print(f'Assigning {er} -> {r}')
                assigned = True

                # add r to existing_rh
                new_RH_adj = RH_to_adj(new_rh)
                new_RH_G = dict_to_digraph(new_RH_adj)
                if not nx.is_directed_acyclic_graph(new_RH_G):
                    new_rh[er].remove(r)
                    print(f'Reverting {er} -> {r}')
    G = dict_to_networkx(new_rh, directed=True)

    # Export to interactive HTML
    out_file = networkx_to_html_with_zoom(G, title="NetworkX from Dict → Interactive HTML", filename="nx_graph.html")
    print(out_file)
    if not assigned:
        for r in rh:
            assigned_perms_r = {e for e in rh[r] if isinstance(e, str) and (e.startswith('P') or e.startswith('p'))}
            assigned_users_r = {e for e in rh[r] if isinstance(e, str) and (e.startswith('U') or e.startswith('u'))}
            assigned_roles_r = {e for e in rh[r] if isinstance(e, int)}

            all_perms_r = inherited_perms_rh[r].union(assigned_perms_r)
            all_users_r = inherited_users_rh[r].union(assigned_users_r)
            all_roles_r = inherited_roles_rh[r].union(assigned_roles_r)

            for er in existing_rh:
                assigned_perms_er = {e for e in existing_rh[er] if
                                     isinstance(e, str) and (e.startswith('P') or e.startswith('p'))}
                assigned_users_er = {e for e in existing_rh[er] if
                                     isinstance(e, str) and (e.startswith('U') or e.startswith('u'))}
                assigned_roles_er = {e for e in existing_rh[er] if isinstance(e, int)}

                all_perms_er = inherited_perms_exrh[er].union(assigned_perms_er)
                all_users_er = inherited_users_exrh[er].union(assigned_users_er)
                all_roles_er = inherited_roles_exrh[er].union(assigned_roles_er)

                # check if r can inherit er
                # check if all users of r can inherit perms of er
                req_perms_by_all_users_of_r = all_perms
                for u in all_users_r:
                    req_perms_by_all_users_of_r = req_perms_by_all_users_of_r.intersection(up_mapped[u])
                if all_perms_er.issubset(req_perms_by_all_users_of_r):
                    new_rh[r].add(er)
                    print(f'Assigning {r} -> {er}')

                    new_RH_adj = RH_to_adj(new_rh)
                    new_RH_G = dict_to_digraph(new_RH_adj)
                    if not nx.is_directed_acyclic_graph(new_RH_G):
                        new_rh[r].remove(er)
                        print(f'Reverting {r} -> {er}')
    return new_rh


def join_v2(existing_rh, rh, up_mapped, usermap, permmap, up):
    new_rh = copy.deepcopy(existing_rh) | copy.deepcopy(rh)
    RBAC_to_RH.check_RH(new_rh, up, usermap, permmap)
    # return new_rh
    all_perms = set()
    for u in up_mapped:
        all_perms.update(up_mapped[u])

    inherited_perms_exrh = RBAC_to_RH.get_inherited_perms_in_RH(existing_rh)
    inherited_users_exrh = RBAC_to_RH.get_inherited_users_in_RH(existing_rh)
    inherited_roles_exrh = RBAC_to_RH.get_inherited_roles_in_RH(existing_rh)

    inherited_perms_rh = RBAC_to_RH.get_inherited_perms_in_RH(rh)
    inherited_users_rh = RBAC_to_RH.get_inherited_users_in_RH(rh)
    inherited_roles_rh = RBAC_to_RH.get_inherited_roles_in_RH(rh)

    assigned = False
    # find if there is any overlap of roles, i.e. overlap of permissions

    can_be_assigned = set()
    for r in rh:
        assigned_perms_r = {e for e in rh[r] if isinstance(e, str) and (e.startswith('P') or e.startswith('p'))}
        assigned_users_r = {e for e in rh[r] if isinstance(e, str) and (e.startswith('U') or e.startswith('u'))}
        assigned_roles_r = {e for e in rh[r] if isinstance(e, int)}

        all_perms_r = inherited_perms_rh[r].union(assigned_perms_r)
        all_users_r = inherited_users_rh[r].union(assigned_users_r)
        all_roles_r = inherited_roles_rh[r].union(assigned_roles_r)
        max_er = None
        for er in existing_rh:
            assigned_perms_er = {e for e in existing_rh[er] if
                                 isinstance(e, str) and (e.startswith('P') or e.startswith('p'))}
            assigned_users_er = {e for e in existing_rh[er] if
                                 isinstance(e, str) and (e.startswith('U') or e.startswith('u'))}
            assigned_roles_er = {e for e in existing_rh[er] if isinstance(e, int)}

            all_perms_er = inherited_perms_exrh[er].union(assigned_perms_er)
            all_users_er = inherited_users_exrh[er].union(assigned_users_er)
            all_roles_er = inherited_roles_exrh[er].union(assigned_roles_er)

            # check if er can inherit r
            # check if all users of er can inherit perms of r
            req_perms_by_all_users_of_er = all_perms
            for eu in all_users_er:
                req_perms_by_all_users_of_er = req_perms_by_all_users_of_er.intersection(up_mapped[eu])
            if all_perms_r.issubset(req_perms_by_all_users_of_er):
                if not max_er:
                    max_er = er
                # else:
                assigned_users_max_er = {e for e in existing_rh[max_er] if
                                         isinstance(e, str) and (e.startswith('U') or e.startswith('u'))}
                all_users_max_er = inherited_users_exrh[max_er].union(assigned_users_max_er)
                # pick er to connect with that satisfies max number of users
                if len(all_users_er) >= len(all_users_max_er):
                    max_er = er

        if max_er:
            can_be_assigned.add((max_er, r))

    max_possible_edge = None
    for possible_edge1 in can_be_assigned:
        er1 = possible_edge1[0]
        assigned_users_er1 = {e for e in existing_rh[er1] if isinstance(e, str) and (e.startswith('U') or
                                                                                     e.startswith('u'))}
        all_users_er1 = inherited_users_exrh[er1].union(assigned_users_er1)
        if not max_possible_edge:
            max_possible_edge = possible_edge1
        if possible_edge1 == max_possible_edge: continue
        max_er = max_possible_edge[0]
        assigned_users_max_er = {e for e in existing_rh[max_er] if isinstance(e, str) and (e.startswith('U') or
                                                                                     e.startswith('u'))}
        all_users_max_er = inherited_users_exrh[max_er].union(assigned_users_max_er)
        if len(all_users_er1) > len(all_users_max_er):
            max_possible_edge = possible_edge1

    if max_possible_edge:
        max_er = max_possible_edge[0]
        r = max_possible_edge[1]
        new_rh[max_er].add(r)
        print(f'Assigning {max_er} -> {r}')
        assigned = True

        # add r to existing_rh
        new_RH_adj = RH_to_adj(new_rh)
        new_RH_G = dict_to_digraph(new_RH_adj)
        if not nx.is_directed_acyclic_graph(new_RH_G):
            new_rh[max_er].remove(r)
            print(f'Reverting {max_er} -> {r}')

    # G = dict_to_networkx(new_rh, directed=True)

    # Export to interactive HTML
    # out_file = networkx_to_html_with_zoom(G, title="NetworkX from Dict → Interactive HTML", filename="nx_graph.html")
    # print(out_file)
    # if not assigned:
    #     for r in rh:
    #         assigned_perms_r = {e for e in rh[r] if isinstance(e, str) and (e.startswith('P') or e.startswith('p'))}
    #         assigned_users_r = {e for e in rh[r] if isinstance(e, str) and (e.startswith('U') or e.startswith('u'))}
    #         assigned_roles_r = {e for e in rh[r] if isinstance(e, int)}
    #
    #         all_perms_r = inherited_perms_rh[r].union(assigned_perms_r)
    #         all_users_r = inherited_users_rh[r].union(assigned_users_r)
    #         all_roles_r = inherited_roles_rh[r].union(assigned_roles_r)
    #
    #         for er in existing_rh:
    #             assigned_perms_er = {e for e in existing_rh[er] if
    #                                  isinstance(e, str) and (e.startswith('P') or e.startswith('p'))}
    #             assigned_users_er = {e for e in existing_rh[er] if
    #                                  isinstance(e, str) and (e.startswith('U') or e.startswith('u'))}
    #             assigned_roles_er = {e for e in existing_rh[er] if isinstance(e, int)}
    #
    #             all_perms_er = inherited_perms_exrh[er].union(assigned_perms_er)
    #             all_users_er = inherited_users_exrh[er].union(assigned_users_er)
    #             all_roles_er = inherited_roles_exrh[er].union(assigned_roles_er)
    #
    #             # check if r can inherit er
    #             # check if all users of r can inherit perms of er
    #             req_perms_by_all_users_of_r = all_perms
    #             for u in all_users_r:
    #                 req_perms_by_all_users_of_r = req_perms_by_all_users_of_r.intersection(up_mapped[u])
    #             if all_perms_er.issubset(req_perms_by_all_users_of_r):
    #                 new_rh[r].add(er)
    #                 print(f'Assigning {r} -> {er}')
    #
    #                 new_RH_adj = RH_to_adj(new_rh)
    #                 new_RH_G = dict_to_digraph(new_RH_adj)
    #                 if not nx.is_directed_acyclic_graph(new_RH_G):
    #                     new_rh[r].remove(er)
    #                     print(f'Reverting {r} -> {er}')

    return new_rh


def merge_rh(all_rhs: list, up: dict, usermap: dict, permmap: dict):
    inv_permmap = {v: k for k, v in permmap.items()}
    inv_usermap = {v: k for k, v in usermap.items()}
    up_mapped = dict()
    for u in up:
        U = inv_usermap[u]
        up_mapped[U] = {inv_permmap[p] for p in up[u]}

    merged_rh = dict()
    for rh in all_rhs:
        if len(merged_rh) == 0:
            merged_rh = copy.deepcopy(rh)
            continue

        for i in range(1):
            new_rh = RBAC_to_RH.minimize_edges_subgraph(rh, up, usermap, permmap)
            print('Ran minimize_edges')
            check = RBAC_to_RH.check_RH(new_rh, up, usermap, permmap)
            if check:
                rh = new_rh
            else:
                print('here')

        inherited_perms_rh = RBAC_to_RH.get_inherited_perms_in_RH(rh)
        inherited_users_rh = RBAC_to_RH.get_inherited_users_in_RH(rh)
        inherited_roles_rh = RBAC_to_RH.get_inherited_roles_in_RH(rh)
        for r in rh:
            # get permissions assigned to r
            assigned_perms_r = {e for e in rh[r] if isinstance(e, str) and (e.startswith('P') or e.startswith('p'))}
            assigned_users_r = {e for e in rh[r] if isinstance(e, str) and (e.startswith('U') or e.startswith('u'))}
            assigned_roles_r = {e for e in rh[r] if isinstance(e, int)}

            all_perms_r = inherited_perms_rh[r].union(assigned_perms_r)
            all_users_r = inherited_users_rh[r].union(assigned_users_r)
            all_roles_r = inherited_roles_rh[r].union(assigned_roles_r)
        merged_rh = join(merged_rh, rh, up_mapped, usermap, permmap, up)
    # print('NEW RH:')
    # pprint(merged_rh)

    merged_rh = RBAC_to_RH.remove_redundant_roles(merged_rh)
    merged_rh = RBAC_to_RH.remove_redundant_edges(merged_rh)

    descendants = dict()
    for r in merged_rh:
        desc = RBAC_to_RH.descendant_of(merged_rh, r)
        descendants[r] = desc
    print("descendants:")
    pprint(descendants)

    merged_rh = RBAC_to_RH.remove_edges_if_common_perms(merged_rh)


    new_merged_rh = RBAC_to_RH.minimize_edges_subgraph(merged_rh, up, usermap, permmap)
    print('Ran minimize_edges')
    check = RBAC_to_RH.check_RH(new_merged_rh, up, usermap, permmap)
    if check:
        merged_rh = new_merged_rh

    num_tries = 1
    for i in range(num_tries):
        new_merged_rh = RBAC_to_RH.remove_more_edges_subgraph(merged_rh, up, usermap, permmap)
        print('Ran remove_more_edges')
        check = RBAC_to_RH.check_RH(new_merged_rh, up, usermap, permmap)
        if check:
            merged_rh = new_merged_rh

    # merged_rh = RBAC_to_RH.remove_more_edges(merged_rh, up, usermap, permmap, persolve_time=100)
    # merged_rh = RBAC_to_RH.minimize_edges(merged_rh, up, usermap, permmap, edges_to_keep=set(), persolve_time=100)

    # RBAC_to_RH.check_RH(merged_rh, up, usermap, permmap)
    return merged_rh


def update_rh_with_offset(rh: dict, role_offset: int):
    new_rh = dict()
    for r in rh:
        new_r = r + role_offset
        if new_r not in new_rh:
            new_rh[new_r] = set()
        for e in rh[r]:
            if isinstance(e, str):
                new_rh[new_r].add(e)
            elif isinstance(e, int):
                new_rh[new_r].add(e + role_offset)
    new_role_offset = max(new_rh.keys()) + 1
    return new_rh, new_role_offset


def main(args: argparse.Namespace):
    upfilename = args.input_up_file
    up, usermap, permmap = readup_and_usermap_permmap(upfilename)

    rbac_cut_files = args.input_cut_files
    print("RBAC cut files: ", rbac_cut_files)
    print("UP files: ", upfilename)
    full_rbac = dict()
    all_rhs = list()
    role_offset = 0
    for cut_file in rbac_cut_files:
        print('Running maxsetsbp on ', cut_file)
        num_roles, roles = maxsetsbp.run(cut_file)
        roles = {idx: roles[idx] for idx in range(len(roles))}
        cutRH = RBAC_to_RH.rbac_to_rh_no_new_roles(cut_file, roles)
        # cutRH, _ = RBAC_RH_IP_V2.run_rbac_to_rh_no_new_roles(cut_file, roles)
        # get_metrics(cutRH, use_sampling=True)

        cutRH, role_offset = update_rh_with_offset(cutRH, role_offset)

        all_rhs.append(cutRH)

    merged_rh = merge_rh(all_rhs, up, usermap, permmap)
    time.sleep(2)
    RBAC_to_RH.check_RH(merged_rh, up, usermap, permmap)

    get_metrics(merged_rh, use_sampling=True)

    G = dict_to_networkx(merged_rh, directed=True)

    # Export to interactive HTML
    out_file = networkx_to_html_with_zoom(G, title="NetworkX from Dict → Interactive HTML", filename="nx_graph.html")
    print(out_file)


# ---------------------- Demo ----------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Read cut up files")
    parser.add_argument("input_cut_files", nargs="+", help="Input RBAC cut files")
    parser.add_argument("input_up_file", type=str, help="Input UP file")
    args = parser.parse_args()
    main(args)
