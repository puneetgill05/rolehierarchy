#!/usr/bin/env python3

# weights: {wr, wu, wp, wh, wd}
# wr: weight assigned to the number of roles in the RH
# wu: weight assigned to the user-role edges in the RH
# wp: weight assigned to the perm-role edges in the RH
# wh: weight assigned to the role-role edges in the RH
# wd: weight assigned to the direct user-perm edges in the RH
import argparse
import json
from collections import defaultdict
from pathlib import Path
from pprint import pprint

import networkx as nx
import numpy as np
from colorama import Fore

import RandomWalk_Uniform
from rh_utils import RH_to_adj, dict_to_digraph, bucketize_by_value, get_role_chains


def wsc(RH: dict, weights=None):
    if weights is None:
        weights = {'wr': 1, 'wu': 1, 'wp': 1, 'wh': 1, 'wd': 0}
    R = get_number_of_roles(RH)
    UA = get_number_of_user_role_edges(RH)
    PA = get_number_of_perm_role_edges(RH)
    H = get_number_of_role_role_edges(RH)
    wsc_metric = weights['wr'] * R + weights['wu'] * UA + weights['wp'] * PA + weights['wh'] * H + weights['wd']
    wsc_metric_full = {'wsc': wsc_metric, '# user-role edges': UA, '# role-perm edges': PA, '# role-role edges': H}
    return wsc_metric_full


def get_number_of_user_role_edges(RH: dict) -> int:
    num_user_role_edges = 0
    for r in RH:
        users_r = {e for e in RH[r] if isinstance(e, str) and (e.startswith('u') or e.startswith('U'))}
        num_user_role_edges += len(users_r)
    return num_user_role_edges


def get_number_of_perm_role_edges(RH: dict) -> int:
    num_perm_role_edges = 0
    for r in RH:
        perms_r = {e for e in RH[r] if isinstance(e, str) and (e.startswith('p') or e.startswith('P'))}
        num_perm_role_edges += len(perms_r)
    return num_perm_role_edges


def get_number_of_role_role_edges(RH: dict) -> int:
    num_role_role_edges = 0
    for r in RH:
        roles_r = {e for e in RH[r] if isinstance(e, int)}
        num_role_role_edges += len(roles_r)
    return num_role_role_edges


def get_number_of_roles(RH: dict) -> int:
    return len(set(RH.keys()))


def get_metrics(RH: dict, use_sampling=False, run_random_walk=True) -> dict:
    # count the # roles
    num_roles = len(RH.keys())

    # count # edges
    num_edges = 0
    for r in RH.keys():
        num_edges += len(RH[r])

    sum_layers = 0
    max_layer = 0
    role_layer_dict = defaultdict()

    # RH_adj = RH_to_adj(RH)

    # DG = dict_to_digraph(RH_adj)
    # longest_path = nx.dag_longest_path(DG)
    # print('Longest Path:')
    # pprint(longest_path)
    # max_layer = len(longest_path) - 2

    for r in RH.keys():
        role_chains_r = get_role_chains(r, RH, set())

        layer = max(len(chain) for chain in role_chains_r)

        # print(f'Layer for {r} --> {role_chains_r}')
        sum_layers += layer
        max_layer = max(max_layer, layer)
        role_layer_dict[r] = layer
        # pass

    layer_role_bucket_dict = bucketize_by_value(role_layer_dict)
    avg_num_layers = sum_layers / num_roles if num_roles > 0 else 0
    print(Fore.GREEN + '==================================')
    print(Fore.GREEN + 'METRICS')
    print(Fore.GREEN + '==================================')
    print(Fore.GREEN + f'Average # of layers: {round(avg_num_layers, 3)}')
    print(Fore.GREEN + f'Max # of layers: {max_layer}')
    print(Fore.GREEN + f'# of roles: {num_roles}')
    print(Fore.GREEN + f'# of edges: {num_edges}')
    print(Fore.GREEN + f'WSC: {wsc(RH)}')
    # print(Fore.GREEN + 'Roles by layers')
    # pprint(layer_role_bucket_dict)

    wsc_RH = wsc(RH)

    UR = {(e, r) for r in RH for e in RH[r] if isinstance(e, str) and (e.startswith('U') or e.startswith('u'))}
    RP = {(r, e) for r in RH for e in RH[r] if isinstance(e, str) and (e.startswith('P') or e.startswith('p'))}
    RR = {(r, e) for r in RH for e in RH[r] if isinstance(e, int)}

    if run_random_walk:
        results = RandomWalk_Uniform.run_random_walk(UR, RR, RP, use_gpu=False, use_sampling=use_sampling)
        median_steps_for_rh = 0
        mean_steps_for_rh = 0
        max_mean_steps_for_rh = 0
        num_unsuccessful = 0
        for row in results:
            if row['median_steps'] == np.inf and row['success_rate'] == 0:
                num_unsuccessful += 1
            else:
                median_steps_for_rh += row['median_steps']
                max_mean_steps_for_rh = max(max_mean_steps_for_rh, row['mean_steps'])
                mean_steps_for_rh += row['mean_steps']

        avg_median_steps_for_rh = median_steps_for_rh / len(results)
        avg_mean_steps_for_rh = mean_steps_for_rh / len(results)
    else:
        avg_median_steps_for_rh = 0
        avg_mean_steps_for_rh = 0
        max_mean_steps_for_rh = 0
        num_unsuccessful = 0
    # print('median_steps for RH: ', median_steps_for_rh)
    # print('mean_steps for RH: ', mean_steps_for_rh)
    # print('# unsuccessful walks for RH: ', num_unsuccessful)
    # print(Fore.GREEN + '==================================')
    # print(Fore.RESET)

    metric = {
        'num_roles': num_roles,
        'num_edges': num_edges,
        'max_layer': max_layer,
        'avg_num_layers': avg_num_layers,
        'wsc': wsc_RH,
        'random_walk': {
            'median_steps': avg_median_steps_for_rh,
            'mean_steps': avg_mean_steps_for_rh,
            'max_mean_steps': max_mean_steps_for_rh,
            'unsuccessful_walks': num_unsuccessful
        }
    }

    print(Fore.GREEN + '==================================')
    print(Fore.GREEN + 'METRICS')
    print(Fore.GREEN + '==================================')
    pprint(metric)
    print(Fore.GREEN + '==================================')
    print(Fore.RESET)

    return metric


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

def main(args: argparse.Namespace):
    rh_file = args.rh_file
    RH = read_rh_file(rh_file)
    get_metrics(RH, use_sampling=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('rh_file', type=str, help='RH file path to read')

    args = parser.parse_args()
    main(args)
# def perform_random_walk(RH_adj: dict):
