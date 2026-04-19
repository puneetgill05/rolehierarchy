import collections
import datetime
import json
import os
import random
import sys
from pathlib import Path
from pprint import pprint
from os import listdir
from os.path import isfile, join

import numpy as np
from scipy import stats as stats
from termcolor import colored

TOTAL_NUMBER_ROLES_ROUND_0 = 'Total # roles after round 0'
TOTAL_NUMBER_EDGES_ROUND_0 = 'Total # edges after round 0'
TOTAL_NUMBER_ROLES_ROUND_1 = 'Total # roles after round 1'
TOTAL_NUMBER_EDGES_ROUND_1 = 'Total # edges after round 1'
RSUBSET = 'rsubset'
CURRNEDGES = 'currnedges'
NEW_NEDGES = 'new_nedges'
CURRNROLES = 'curr_roles'
NUM_NEW_ROLES = 'num_new_roles'


def read_log_file(log_filepath: str):
    # list of role pairs observed between round 0 and 1
    rsubsets = []
    # list of role pairs potentially shrinkign the edges
    rsubsets_potential_shrinking = []

    rsubsets_map = dict()

    round_0_roles_encountered = False
    round_0_edges_encountered = False
    round_1_edges_encountered = False
    rsubset_encountered = False

    num_edges_round_0 = 0
    num_edges_round_1 = 0
    num_roles_round_0 = 0
    num_roles_round_1 = 0

    with open(log_filepath, 'r') as f:
        for line in f:
            if line.startswith(TOTAL_NUMBER_ROLES_ROUND_0):
                line_split = line.split(':')
                value = line_split[1].strip()
                num_roles_round_0 = int(value)
                round_0_roles_encountered = True
                num_role_pairs = int(num_roles_round_0 * (num_roles_round_0 - 1) / 2)
                print(f'Number of role pairs (Theoretical): {num_role_pairs}')
            elif line.startswith(TOTAL_NUMBER_EDGES_ROUND_0):
                line_split = line.split(':')
                value = line_split[1].strip()
                num_edges_round_0 = int(value)
                round_0_edges_encountered = True
            elif line.startswith(TOTAL_NUMBER_ROLES_ROUND_1):
                line_split = line.split(':')
                value = line_split[1].strip()
                num_roles_round_1 = int(value)
                round_1_roles_encountered = True
            elif line.startswith(TOTAL_NUMBER_EDGES_ROUND_1):
                line_split = line.split(':')
                value = line_split[1].strip()
                num_edges_round_1 = int(value)
                round_1_edges_encountered = True
                print(colored(f'Number of edges decreased: {num_edges_round_0} - {num_edges_round_1} = '
                              f' {num_edges_round_0 - num_edges_round_1}', 'white', 'on_blue'))

            round_0_encountered = round_0_edges_encountered and round_0_roles_encountered
            round_1_encountered = round_1_edges_encountered and round_1_roles_encountered
            if round_0_encountered and not round_1_encountered:
                if line.startswith(RSUBSET):
                    line_split = line.split(':')
                    value = line_split[1].strip()
                    curr_rsubset = tuple(eval(value))
                    if curr_rsubset not in rsubsets:
                        rsubsets.append(curr_rsubset)
                        rsubsets_map[curr_rsubset] = {}
                        rsubset_encountered = True
                elif rsubset_encountered and line.startswith(CURRNEDGES):
                    line_split = line.split(',')
                    for split in line_split:
                        split = split.strip()
                        if split.startswith(CURRNEDGES):
                            curr_num_edges = int(split.split(':')[1].strip())
                            rsubsets_map[curr_rsubset][CURRNEDGES] = curr_num_edges
                        elif split.startswith(NEW_NEDGES):
                            new_num_edges = int(split.split(':')[1].strip())
                            rsubsets_map[curr_rsubset][NEW_NEDGES] = new_num_edges
                        elif split.startswith(NUM_NEW_ROLES):
                            new_num_roles = int(split.split(':')[1].strip())
                            rsubsets_map[curr_rsubset][NUM_NEW_ROLES] = new_num_roles
                    rsubset_encountered = False
    print(f'Number of role pairs: {len(rsubsets_map)}')
    if num_roles_round_1 == 0:
        actual_num_edges_shrunk = 0
    else:
        actual_num_edges_shrunk = num_edges_round_0 - num_edges_round_1
    print('Num edges shrunk:', actual_num_edges_shrunk)
    return ({'num_edges': num_edges_round_0, 'num_roles': num_roles_round_0},
            {'num_edges': num_edges_round_1, 'num_roles': num_roles_round_1}, rsubsets_map,
            actual_num_edges_shrunk)


def compute_sample_size(confidence: float, margin_error: float, population_proportion: float, population_size: int):
    alpha = 1 - confidence
    z_score = stats.norm.ppf(1 - alpha / 2)

    sample_size_infinite = (z_score ** 2 * population_proportion * (1 - population_proportion)) / (margin_error ** 2)
    sample_size_finite = (sample_size_infinite * population_size) / (sample_size_infinite + population_size - 1)
    return int(np.ceil(sample_size_finite))


def randomly_sample(sample_size: int, population: set) -> set:
    return set(random.sample(list(population), sample_size))


def get_shrinkage_percent(sample_role_pairs: set, rsubsets_map: dict):
    sample_role_pairs_shrink = set()
    for role_pair in sample_role_pairs:
        if len(rsubsets_map[role_pair]) != 0:
            sample_role_pairs_shrink.add(role_pair)
    role_pairs_shrink = set()
    for role_pair in rsubsets_map:
        if len(rsubsets_map[role_pair]) != 0:
            role_pairs_shrink.add(role_pair)
    sample_shrinkage_percent = round(100 * len(sample_role_pairs_shrink) / len(sample_role_pairs), 2)
    actual_shrinkage_percent = round(100 * len(role_pairs_shrink) / len(rsubsets_map), 2)
    print(colored(f'% of sample role pairs yielding shrinkage in # edges: {sample_shrinkage_percent} %',
                  'white', 'on_green'))
    print(colored(f'% of role pairs yielding shrinkage in # edges: {actual_shrinkage_percent} %',
                  'white', 'on_green'))
    return sample_shrinkage_percent, actual_shrinkage_percent


def compute_num_edges_decreased_greedily(rsubsets_map: dict, sample_role_pairs: set):
    role_pairs_shrinking = dict()
    for role_pair in sample_role_pairs:
        if len(rsubsets_map[role_pair]) > 0:
            num_edges_decreased = rsubsets_map[role_pair][CURRNEDGES] - rsubsets_map[role_pair][NEW_NEDGES]
            if num_edges_decreased in role_pairs_shrinking:
                role_pairs_shrinking[num_edges_decreased].add(role_pair)
            else:
                role_pairs_shrinking[num_edges_decreased] = {role_pair}

    # order the dict by the number of edges decreased in descending order
    role_pairs_shrinking = collections.OrderedDict(sorted(role_pairs_shrinking.items(), reverse=True))

    num_edges_decreased_greedily = 0

    while len(role_pairs_shrinking) > 0:
        # pick the first key
        best_choice = list(role_pairs_shrinking.keys())[0]
        if len(role_pairs_shrinking[best_choice]) > 0:
            # pick a random role pair for that key
            role_pair_picked = random.choice(list(role_pairs_shrinking[best_choice]))
            num_edges_decreased_greedily += best_choice

            role_pairs_to_remove = set()

            # remove these roles from the role_pairs_shrinking
            for k in role_pairs_shrinking:
                r1, r2 = role_pair_picked
                for role_pair in role_pairs_shrinking[k]:
                    if r1 in role_pair or r2 in role_pair:
                        # remove these roles
                        role_pairs_to_remove.add(role_pair)
            keys_to_remove = set()
            for k in role_pairs_shrinking:
                role_pairs_shrinking[k] = role_pairs_shrinking[k].difference(role_pairs_to_remove)
                if len(role_pairs_shrinking[k]) == 0:
                    keys_to_remove.add(k)
            # remove the keys with no role pairs
            for k in keys_to_remove:
                del role_pairs_shrinking[k]

    return num_edges_decreased_greedily


def dump_data(data: dict, data_file: str):
    filepath = Path(data_file)
    if not filepath.exists():
        filepath.touch()
        json.dump({}, filepath.open('w'))
    with open(data_file, 'r') as file:
        existing_data = json.load(file)

        for k in data:
            existing_data[k] = data[k]

    with open(data_file, 'w') as file:
        json.dump(existing_data, file, indent=4)


def create_data(initial_rbac_data, final_rbac_data, sample_role_pairs: set, rsubsets_map: dict,
                actual_num_edges_shrunk: int) -> dict:
    sample_shrinkage_percent, actual_shrinkage_percent = get_shrinkage_percent(sample_role_pairs, rsubsets_map)
    num_edges_decreased_in_sample = compute_num_edges_decreased_greedily(rsubsets_map, sample_role_pairs)

    sample_role_pair_data_list = list()
    for k in sample_role_pairs:
        sample_role_pair_data = dict()
        sample_role_pair_data['role_1'] = k[0]
        sample_role_pair_data['role_2'] = k[1]
        if len(rsubsets_map[k]) == 0:
            sample_role_pair_data['num_edges_shrunk'] = 0
        else:
            sample_role_pair_data['num_edges_shrunk'] = rsubsets_map[k]['currnedges'] - rsubsets_map[k]['new_nedges']
        sample_role_pair_data_list.append(sample_role_pair_data)

    actual_role_pair_data_list = list()
    for k in rsubsets_map:
        actual_role_pair_data = dict()
        actual_role_pair_data['role_1'] = k[0]
        actual_role_pair_data['role_2'] = k[1]
        if len(rsubsets_map[k]) == 0:
            actual_role_pair_data['num_edges_shrunk'] = 0
        else:
            actual_role_pair_data['num_edges_shrunk'] = rsubsets_map[k]['currnedges'] - rsubsets_map[k]['new_nedges']
        actual_role_pair_data_list.append(actual_role_pair_data)

    data = {
        'initial_rbac_data': {
            'num_edges': initial_rbac_data['num_edges'],
            'num_roles': initial_rbac_data['num_roles']
        },
        'final_rbac_data': {
            'num_edges': final_rbac_data['num_edges'],
            'num_roles': final_rbac_data['num_roles']
        },
        'sample': {
            'percent_role_pairs_shrinkage': sample_shrinkage_percent,
            'num_role_pairs': len(sample_role_pairs),
            'num_edges_shrunk': num_edges_decreased_in_sample,
            # 'role_pairs': sample_role_pair_data_list
        },
        'actual': {
            'percent_role_pairs_shrinkage': actual_shrinkage_percent,
            'num_role_pairs': len(rsubsets_map),
            'num_edges_shrunk': actual_num_edges_shrunk,
            # 'role_pairs': actual_role_pair_data_list
        }
    }
    return data


def main():
    print('Start time:', datetime.datetime.now())
    sys.stdout.flush()

    # if len(sys.argv) != 4:
    #     print('Usage: ', end='')
    #     print(sys.argv[0], end=' ')
    #     print('<input-log-file> <dataset-name> <output-file>')
    #     return

    # log_filepath = sys.argv[1]
    # dataset_name = sys.argv[2]
    # output_filepath = sys.argv[3]


    mydir = '/home/puneet/Projects/minedgerolemining/minedgerolemining/log_files/86400-60'

    log_files = [join(mydir, f) for f in listdir(mydir) if isfile(join(mydir, f))]
    filenames = [f.split('/')[-1].split('-')[0] for f in listdir(mydir) if isfile(join(mydir, f))]

    num_experiments = 20
    start = 30
    for ex in range(start, start + num_experiments):
        i = 0
        for log_filepath in log_files:
            dataset_name = filenames[i]
            # if not dataset_name.startswith('domino'):
            #     i += 1
            #     continue
            # read log file and extract role pair information
            inital_rbac_data, final_rbac_data, rsubsets_map, num_edges_shrunk = read_log_file(log_filepath)

            # compute sample size
            sample_size = compute_sample_size(0.95, 0.05,
                                              0.5, population_size=len(rsubsets_map))
            print(f'Sample size: {sample_size}')

            # pick a random sample of role pairs
            sample_role_pairs = randomly_sample(sample_size, set(rsubsets_map.keys()))

            # get shrinkage percentage
            get_shrinkage_percent(sample_role_pairs, rsubsets_map)

            # compute the expected number of edges decreased in the sample
            num_edges_decreased_in_sample = compute_num_edges_decreased_greedily(rsubsets_map, sample_role_pairs)
            print(colored(f'Expected # edges decreased in the sample: {num_edges_decreased_in_sample}', 'white', 'on_blue'))

            data = dict()
            data[dataset_name] = create_data(inital_rbac_data, final_rbac_data, sample_role_pairs, rsubsets_map,
                                             num_edges_shrunk)

            output_filepath = '/home/puneet/Projects/minedgerolemining/minedgerolemining/random_sampling/log_data_experiments'
            dump_data(data, os.path.join(output_filepath,  f'log_{ex}.json'))
            i += 1

    print('End time:', datetime.datetime.now())


if __name__ == '__main__':
    main()
