#!/usr/bin/env python3

import matplotlib.pyplot as plt

percent_decrease_edges_alg2 = {
    "fw1": 85.1,
    "fw2": 78.5,
    "hc": 80.1,
    "domino": 25.7,
    "apj": 50.4,
    "as": 75.2,
    "al": 25.7,
    "emea": 0.0,
    "univ": 54.8,
    "mailer": 66.8,
    "small 01": 59.2,
    "small 02": 70.4,
    "small 03": 76.1,
    "small 04": 69.9,
    "small 05": 68.3,
    "small 06": 67.0,
    "small 07": 77.4,
    "small 08": 73.6,
    "medium 01": 67.6,
    "medium 02": 58.7,
    "medium 03": 54.3,
    "medium 04": 73.5,
    "medium 05": 77.8,
    "medium 06": 65.0,
    "large 01": 58.7,
    "large 02": 75.6,
    "large 03": 67.9,
    "large 04": 75.6,
    "large 05": 68.3,
    "large 06": 77.9,
    "comp 01.01": 87.7,
    "comp 01.02": 83.6,
    "comp 01.03": 85.9,
    "comp 01.04": 85.7,
    "rw 01": 6.9,
    "2level 01": 74.3,
    "2level 02": 65.6,
    "2level 03": 73.5,
    "2level 04": 70.1,
    "2level 05": 62.0,
    "2level 06": 59.1,
    "2level 07": 73.0,
    "2level 08": 70.5,
    "2level 09": 68.3,
    "2level 10": 76.4
}

percent_decrease_edges_alg1 = {
    "fw1": 7.3,
    "fw2": 3.3,
    "hc": 1.4,
    "domino": 0.6,
    "apj": 3.2,
    "as": 7.5,
    "al": 1.9,
    "univ": 6.4,
    "mailer": 3.96,
    "small 01": 5.9,
    "small 02": 3.8,
    "small 03": 2.6,
    "small 04": 2.4,
    "small 05": 0.9,
    "small 06": 7.0,
    "small 07": 1.7,
    "small 08": 0.8,
    "medium 01": 0.0,
    "medium 03": 0.5,
    "medium 05": 0.0,
    "large 02": 0.0,
    "large 03": 0.3,
    "large 06": 0.1,
    "comp 01.01": 0.1,
    "comp 01.02": 0.1,
    "comp 01.03": 0.0,
    "comp 01.04": 0.0,
    "rw 01": 2.1,
    "2level 01": 13.8,
    "2level 02": 9.5,
    "2level 03": 4.5,
    "2level 04": 6.1,
    "2level 05": 1.5,
    "2level 06": 2.0,
    "2level 07": 7.4,
    "2level 08": 4.6,
    "2level 09": 2.8,
    "2level 10": 5.5
}

percent_decrease_roles = {
    "fw1": 34.6,
    "fw2": 26.9,
    "hc": 0.0,
    "domino": 23.3,
    "apj": 29.6,
    "as": 31.6,
    "al": 5.5,
    "emea": 0.0,
    "univ": 28.3,
    "mailer": 39.8,
    "small 01": 27.9,
    "small 02": 31.1,
    "small 03": 27.1,
    "small 04": 27.5,
    "small 05": 20.0,
    "small 06": 26.6,
    "small 07": 42.9,
    "small 08": 37.2,
    "medium 01": 20.4,
    "medium 02": 41.9,
    "medium 03": 45.0,
    "medium 04": 26.2,
    "medium 05": 21.7,
    "medium 06": 41.1,
    "large 01": 28.5,
    "large 02": 25.4,
    "large 03": 24.4,
    "large 04": 22.2,
    "large 05": 38.4,
    "large 06": 25.5,
    "comp 01.01": 50.7,
    "comp 01.02": 49.4,
    "comp 01.03": 50.4,
    "comp 01.04": 47.2,
    "rw 01": 0.0,
    "2level 01": 23.9,
    "2level 02": 15.8,
    "2level 03": 25.8,
    "2level 04": 13.8,
    "2level 05": 25.0,
    "2level 06": 24.2,
    "2level 07": 43.4,
    "2level 08": 16.7,
    "2level 09": 14.2,
    "2level 10": 19.8
}


def plot_percent_decrease(alg1_percent_decrease, alg2_percent_decrease, alg1: str, alg2: str, quantity: str):
    # Sort by percent decrease (ascending)
    alg1_sorted_items = sorted(alg1_percent_decrease.items(), key=lambda x: x[1])
    alg2_sorted_items = sorted(alg2_percent_decrease.items(), key=lambda x: x[1])
    # sorted_items = percent_decrease.items()
    benchmarks = [item[0] for item in alg1_sorted_items]
    # values = [item[1] for item in alg1_sorted_items]

    all_keys = sorted(set(alg1_percent_decrease) | set(alg2_percent_decrease))

    # fill missing keys with 0
    alg1_percent_decrease = {k: alg1_percent_decrease.get(k, 0) for k in all_keys}
    alg2_percent_decrease = {k: alg2_percent_decrease.get(k, 0) for k in all_keys}


    plt.rcParams.update({
        "text.usetex": False,
        "font.family": "monospace"
    })
    # Plot
    plt.figure(figsize=(14, 6))


    plt.plot(alg1_percent_decrease.keys(), alg1_percent_decrease.values(), marker='o', linestyle='-', color='black',
             linewidth=1, label='MinRolesRH')
    plt.plot(alg1_percent_decrease.keys(), alg2_percent_decrease.values(), marker='^', linestyle='dashed',
             color='black', linewidth=1, label='NewRolesRH')
    # plt.fill_between(benchmarks, values, color='lightblue', alpha=0.3)

    # Labels and styling
    plt.xlabel("Benchmark", fontsize=12)
    plt.ylabel(f"% decrease in number of {quantity}", fontsize=12)
    # plt.title("Percent Decrease in Number of Edges After Pruning", fontsize=14)
    plt.xticks(rotation=90)
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend(loc='upper right', fontsize=11)
    # Annotate values
    # for i, v in enumerate(values):
    #     plt.text(i, v + 1, f"{v:.1f}%", ha='center', va='bottom', fontsize=8)

    plt.tight_layout()
    # plt.show()
    plt.tight_layout()

    # Save outputs
    png_path = f"{alg1}_{alg2}_percent_decrease_{quantity}.pdf"
    # csv_path = "/mnt/data/layers_lineplot_data.csv"
    plt.savefig(png_path, dpi=200, bbox_inches='tight')
    # plt.show()


plot_percent_decrease(percent_decrease_edges_alg1, percent_decrease_edges_alg2, "alg1", "alg2", "edges")
# plot_percent_decrease(percent_decrease_edges_alg2, "alg2", "edges")
plot_percent_decrease(percent_decrease_roles, dict(), "alg1", "alg2", "roles")
