import datetime
import json
import math
import os.path
import sys
from os import listdir
from os.path import isfile, join
from pathlib import Path

import numpy as np
from scipy import stats

# Computer confidence interval for proportion. Assuming normal distribution
def compute_confidence_interval(confidence: float, p_hat: float, n: int):
    se = math.sqrt(p_hat * (1 - p_hat) / n)

    z = stats.norm.ppf(1 - (1 - confidence) / 2)

    margin_of_error = z * se
    lower_bound = p_hat - margin_of_error
    upper_bound = p_hat + margin_of_error
    if lower_bound < 0:
        lower_bound = 0
    return 100 * lower_bound, 100 * upper_bound


# Compute confidence interval for mean. Assuming standard deviation for population is unknown, so t-distribution
def compute_confidence_interval_mean(confidence: float, sample_data: list, quantity_to_measure: float):
    n = len(sample_data)
    mean = quantity_to_measure
    std = np.std(sample_data, ddof=1)
    df = n - 1

    # compute t-critical value
    t_crit = stats.t.ppf(1-(1 - confidence) / 2, df)
    se = std / np.sqrt(n)
    margin_of_error = t_crit * se
    lower_bound = mean - margin_of_error
    upper_bound = mean + margin_of_error
    if lower_bound < 0:
        lower_bound = 0
    return lower_bound, upper_bound


def compute_stats(data_file: str, confidence: float):
    with open(data_file, 'r') as file:
        data = json.load(file)

    stats_data = dict()
    for k in data:
        percentage_roles_shrinking = data[k]['sample']['percent_role_pairs_shrinkage'] / 100
        num_role_pairs = data[k]['sample']['num_role_pairs']

        num_edges_shrunk_data = []
        num_edges_shrunk_in_sample = data[k]['sample']['num_edges_shrunk']
        initial_num_edges = data[k]['initial_rbac_data']['num_edges']
        num_edges_shrunk_in_sample_normalized = num_edges_shrunk_in_sample / initial_num_edges
        # for role_pair_data in data[k]['sample']['role_pairs']:
        #     num_edges_shrunk_data.append(role_pair_data['num_edges_shrunk'])


        # compute confidence interval
        ci_percentage_roles_shrinking = compute_confidence_interval(confidence=confidence,
                                                                    p_hat=percentage_roles_shrinking,
                                                                    n=num_role_pairs)
        # ci_num_edges_shrunk = compute_confidence_interval_mean(confidence=confidence,
        #                                                         sample_data=num_edges_shrunk_data,
        #                                                        quantity_to_measure=num_edges_shrunk_in_sample)

        ci_percent_edges_shrunk = compute_confidence_interval(confidence=confidence,
                                                                p_hat=num_edges_shrunk_in_sample_normalized,
                                                               n=num_role_pairs)
        stats_data[k] = {
            'percentage_roles_shrinking': {
                'confidence_interval': [round(ci, 2) for ci in list(ci_percentage_roles_shrinking)]
            },
            # 'percentage_edges_shrunk': {
            #     'confidence_interval': list(ci_percent_edges_shrunk)
            # },
            'num_edges_shrunk': {
                'confidence_interval': [round(ci_bound * initial_num_edges / 100, 2) for ci_bound in list(
                    ci_percent_edges_shrunk)]
            }
        }
    return stats_data


def main():
    print('Start time:', datetime.datetime.now())
    sys.stdout.flush()

    # if len(sys.argv) != 3:
    #     print('Usage: ', end='')
    #     print(sys.argv[0], end=' ')
    #     print('<data-file> <stats_file>')
    #     return
    #
    # data_file = sys.argv[1]
    # stats_file = sys.argv[2]

    log_data_dir = '/home/puneet/Projects/minedgerolemining/minedgerolemining/random_sampling/log_data_experiments'
    stats_data_dir = '/home/puneet/Projects/minedgerolemining/minedgerolemining/random_sampling/stats_data'


    log_files = [join(log_data_dir, f) for f in listdir(log_data_dir) if isfile(join(log_data_dir, f))]
    # filenames = [f.split('/')[-1] for f in listdir(log_data_dir) if isfile(join(log_data_dir, f))]



    i = 0
    for data_file in log_files:
        stats_data = compute_stats(data_file, 0.95)

        stats_data_filename = f'stats_data_{i}.json'
        stats_data_filepath = os.path.join(stats_data_dir, stats_data_filename)
        filepath = Path()
        if not filepath.exists():
            filepath.touch()
            json.dump({}, filepath.open('w'))
        with open(stats_data_filepath, 'w') as f:
            json.dump(stats_data, f, indent=4)
        i += 1




    print('End time:', datetime.datetime.now())


if __name__ == '__main__':
    main()