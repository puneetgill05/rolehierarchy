import json
from os import listdir
from os.path import join, isfile

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import MaxNLocator
from scipy.interpolate import make_interp_spline

plt.style.use('ggplot')

# Example data
# x = np.linspace(0, 10, 100)
# y = np.sin(x)
# ci = 0.2  # constant confidence interval width
#
# plt.plot(x, y, label='Mean')
# plt.fill_between(x, y - ci, y + ci, color='blue', alpha=0.2, label='95% CI')
# plt.legend()
# plt.title("Mean with 95% Confidence Interval")
# plt.show()


# data_file = 'data.json'
# stats_file = 'stats.json'

plot_data = dict()

benchmark_names = {
    'univ': 'univ',
    'al': 'al',
    'as': 'as',
    'emea': 'ema',
    'mailer': 'mailer',
    'fw1': 'fw1',
    'fw2': 'fw2',
    'apj': 'apj',
    'domino': 'domino',
    'hc': 'hc',
    'ps01': 'small 1',
    'ps02': 'small 2',
    'ps03': 'small 3',
    'ps04': 'small 4',
    'ps05': 'small 5',
    'ps06': 'small 6',
    'ps07': 'small 7',
    'ps08': 'small 8',
    'pm01': 'medium 1',
    'pm02': 'medium 2',
    'pm03': 'medium 3',
    'pm04': 'medium 4',
    'pm05': 'medium 5',
    'pm06': 'medium 6',
    'pl01': 'large 1',
    'pl02': 'large 2',
    'pl03': 'large 3',
    'pl04': 'large 4',
    'pl05': 'large 5',
    'pl06': 'large 6',
    'c01.1': 'comp 1.1',
    'c01.2': 'comp 1.2',
    'c01.3': 'comp 1.3',
    'c01.4': 'comp 1.4',

    'c02.1': 'comp 2.1',
    'c02.2': 'comp 2.2',
    'c02.3': 'comp 2.3',
    'c02.4': 'comp 2.4',

    'c03.1': 'comp 3.1',
    'c03.2': 'comp 3.2',
    'c03.3': 'comp 3.3',
    'c03.4': 'comp 3.4',

    'c04.1': 'comp 4.1',
    'c04.2': 'comp 4.2',
    'c04.3': 'comp 4.3',
    'c04.4': 'comp 4.4',

    'rw01': 'rw 1',
    '2l01': '2 level 1',
    '2l02': '2 level 2',
    '2l03': '2 level 3',
    '2l04': '2 level 4',
    '2l05': '2 level 5',
    '2l06': '2 level 6',
    '2l07': '2 level 7',
    '2l08': '2 level 8',
    '2l09': '2 level 9',
    '2l10': '2 level 10'
}


def confidence_interval_percent_role_pairs_shrinking(log_file, stats_file, fig, ax):
    with open(stats_file, 'r') as file:
        stats = json.load(file)
    with open(log_file, 'r') as file:
        data = json.load(file)
        for k in data:
            if data[k]['actual']['percent_role_pairs_shrinkage'] > 5 \
                    or data[k]['actual']['percent_role_pairs_shrinkage'] == 0 \
                    or data[k]['sample']['percent_role_pairs_shrinkage'] == 0:
                continue
            plot_data[k] = {
                'percent_role_pairs_shrinkage': data[k]['actual']['percent_role_pairs_shrinkage'],
                'sample_percent_role_pairs_shrinkage': data[k]['sample']['percent_role_pairs_shrinkage'],
                'confidence_interval': stats[k]['percentage_roles_shrinking']['confidence_interval']
            }
    x = [benchmark_names[k] for k in plot_data]
    y = [plot_data[k]['percent_role_pairs_shrinkage'] for k in plot_data]
    y_sample = [plot_data[k]['sample_percent_role_pairs_shrinkage'] for k in plot_data]

    ci_lower = [plot_data[k]['confidence_interval'][0] for k in plot_data]
    ci_upper = [plot_data[k]['confidence_interval'][1] for k in plot_data]

    # ax.plot(x, y, color='#000', linewidth=1, label='% of role pairs shrinking edges')
    # ax.plot(x, y_sample, linestyle=':', color='#000', alpha=0.5, linewidth=2,
    #         label=('% of role pairs shrinking edges in '
    #                'sample'))
    ax.fill_between(x, ci_lower, ci_upper, color='#000', alpha=0.1, label='95% CI')
    # ax.grid(False)
    ax.grid(True, which='major', linestyle='--', color='gray', linewidth=0.4)

    # ax.xaxis.set_major_locator(MaxNLocator(integer=True))

    ax.set_xticklabels(x, rotation=45)

    ax.set_xlabel('Benchmark')
    ax.set_ylabel('Percentage')
    fig.patch.set_facecolor('white')  # full figure background
    ax.set_facecolor('white')
    # ax.legend(loc='upper left')
    plt.tight_layout()
    # plt.savefig("confidence_interval.png", dpi=300, bbox_inches='tight')  # save before plt.show()
    # plt.show()
    return plt, plot_data


def confidence_interval_num_edges_shrunk(log_file, stats_file, fig, ax):
    with open(stats_file, 'r') as file:
        stats = json.load(file)
    with open(log_file, 'r') as file:
        data = json.load(file)
        for k in data:
            if data[k]['actual']['num_edges_shrunk'] == 0 \
                    or data[k]['sample']['num_edges_shrunk'] == 0:
                continue
            plot_data[k] = {
                'num_edges_shrunk': data[k]['actual']['num_edges_shrunk'],
                'sample_num_edges_shrunk': data[k]['sample']['num_edges_shrunk'],
                'confidence_interval': stats[k]['num_edges_shrunk']['confidence_interval']
            }
    x = [benchmark_names[k] for k in plot_data]
    y = [plot_data[k]['num_edges_shrunk'] for k in plot_data]
    y_sample = [plot_data[k]['sample_num_edges_shrunk'] for k in plot_data]

    ci_lower = [plot_data[k]['confidence_interval'][0] for k in plot_data]
    ci_upper = [plot_data[k]['confidence_interval'][1] for k in plot_data]

    # ax.plot(x, y, color='#000', linewidth=1, label='Number of edges shrunk')
    # ax.plot(x, y_sample, linestyle=':', color='#000', alpha=0.5, linewidth=2,
    #         label=('Number of edges shrunk in sample'))
    ax.fill_between(x, ci_lower, ci_upper, color='#000', alpha=0.1, label='95% CI')
    # ax.grid(False)
    ax.grid(True, which='major', linestyle='--', color='gray', linewidth=0.4)

    # ax.xaxis.set_major_locator(MaxNLocator(integer=True))

    ax.set_xticklabels(x, rotation=45)

    ax.set_xlabel('Benchmark')
    ax.set_ylabel('Number of edges shrunk')
    fig.patch.set_facecolor('white')  # full figure background
    ax.set_facecolor('white')
    # ax.legend(loc='upper left')
    plt.tight_layout()
    # plt.savefig("confidence_interval_num_edges_shrunk.png", dpi=300, bbox_inches='tight')  # save before plt.show()
    # plt.show()
    return plt, plot_data


def get_data_from_log_file(log_file, parameter):
    log_data = dict()
    with open(log_file, 'r') as file:
        data = json.load(file)
        for k in data:
            if data[k]['actual'][parameter] == 0 \
                    or data[k]['sample'][parameter] == 0:
                continue
            log_data[k] = {
                parameter: data[k]['actual'][parameter],
                f'sample_{parameter}': data[k]['sample'][parameter],
            }
    return log_data

def plot_ci(confidence_intervals_dict, true_values):
    confidence = 0.95
    for k in confidence_intervals_dict:
        true_p = true_values[k]
        confidence_intervals = confidence_intervals_dict[k]
        num_samples = len(confidence_intervals)
        contains_true_p = []
        for i, (low, high) in enumerate(confidence_intervals):
            contains_true_p.append(low <= true_p <= high)

        plt.figure(figsize=(10, 8))
        for i, (low, high) in enumerate(confidence_intervals):
            color = 'green' if contains_true_p[i] else 'red'
            plt.plot([low, high], [i, i], color=color, linewidth=2)
            plt.plot(true_p, i, 'ko', markersize=3)

        plt.axvline(true_p, color='black', linestyle='--', label=f"True p = {true_p}")
        plt.xlabel("Proportion")
        plt.ylabel("Sample index")
        plt.title(f"{num_samples} Repeated Samples — {int(confidence * 100)}% Confidence Intervals for "
                  f"{benchmark_names[k]}")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.show()


log_data_dir = '/home/puneet/Projects/minedgerolemining/minedgerolemining/random_sampling/log_data_experiments'
stats_data_dir = '/home/puneet/Projects/minedgerolemining/minedgerolemining/random_sampling/stats_data'

log_files = [join(log_data_dir, f) for f in listdir(log_data_dir) if isfile(join(log_data_dir, f))]
stats_data_files = [join(stats_data_dir, f) for f in listdir(stats_data_dir) if isfile(join(stats_data_dir, f))]

fig, ax = plt.subplots(figsize=(10, 6))

j = 0
confidence_intervals = dict()
true_values = dict()

parameter = 'num_edges_shrunk'
for log_file in log_files:
    log_data = get_data_from_log_file(log_file, parameter)
    for k in log_data:
        if k not in true_values:
            true_values[k] = log_data[k][parameter]




for log_file in log_files:
    for stats_data_file in stats_data_files:
        if log_file.split('_')[-1] == stats_data_file.split('_')[-1]:
            # plot num of edges
            # plt, plot_data = confidence_interval_num_edges_shrunk(log_file, stats_data_file, fig, ax)
            # x = [benchmark_names[k] for k in plot_data]
            # y = [plot_data[k]['num_edges_shrunk'] for k in plot_data]
            # ax.plot(x, y, color='#0ff', linewidth=1, label='Number of edges shrunk')

            # plot percent of role pairs
            plt, plot_data = confidence_interval_percent_role_pairs_shrinking(log_file, stats_data_file, fig, ax)
            x = [benchmark_names[k] for k in plot_data]
            y = [plot_data[k]['percent_role_pairs_shrinkage'] for k in plot_data]
            ax.plot(x, y, color='#0ff', linewidth=1, label='% of role pairs shrinking edges')

            for k in plot_data:
                if k in confidence_intervals:
                    confidence_intervals[k].append(plot_data[k]['confidence_interval'])
                else:
                    confidence_intervals[k] = [plot_data[k]['confidence_interval']]

            print(f'j: {j}')
            j += 1

            break

# plot_ci(confidence_intervals, true_values)

plt.show()



