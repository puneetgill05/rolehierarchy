#!/usr/bin/env python3

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# ---- Raw data from the user ----
vaidya = {
    "up_fw1":3,"up_fw2":2,"up_hc":3,"up_domino":2,"up_apj":3,"up_as":3,"up_al":3,"up_emea":1,"up_univ":2,"mailer":3,
    "PLAIN_SMALL_01":1,"PLAIN_SMALL_02":2,"PLAIN_SMALL_03":2,"PLAIN_SMALL_04":1,"PLAIN_SMALL_05":2,"PLAIN_SMALL_06":2,
    "PLAIN_SMALL_07":2,"PLAIN_SMALL_08":1,"PLAIN_MEDIUM_01":1,"PLAIN_MEDIUM_02":1,"PLAIN_MEDIUM_03":2,"PLAIN_MEDIUM_04":1,
    "PLAIN_MEDIUM_05":1,"PLAIN_MEDIUM_06":2,"PLAIN_LARGE_01":1,"PLAIN_LARGE_02":1,"PLAIN_LARGE_03":2,"PLAIN_LARGE_04":1,
    "PLAIN_LARGE_05":1,"PLAIN_LARGE_06":2,"COMP 01.01":2,"COMP 01.02":2,"COMP 01.03":1,"COMP 01.04":1,"COMP 02.01":3,
    "COMP 02.02":3,
    # "COMP 02.03":3,"COMP 02.04":2,"COMP 03.01":None,"COMP 03.02":None,"COMP 03.03":None,"COMP 03.04":None,
    # "COMP 04.01":None,"COMP 04.02":None,"COMP 04.03":None,"COMP 04.04":None,
    "RW 01":4,"2Level_01":2,"2Level_02":1,
    "2Level_03":2,"2Level_04":2,"2Level_05":1,"2Level_06":1,"2Level_07":1,"2Level_08":1,"2Level_09":2,"2Level_10":2
}

alg1 = {
    "up_fw1":4,"up_fw2":3,"up_hc":3,"up_domino":3,"up_apj":3,"up_as":4,"up_al":3,"up_emea":1,"up_univ":3,"mailer":3,
    "PLAIN_SMALL_01":2,"PLAIN_SMALL_02":2,"PLAIN_SMALL_03":2,"PLAIN_SMALL_04":1,"PLAIN_SMALL_05":2,"PLAIN_SMALL_06":2,
    "PLAIN_SMALL_07":2,"PLAIN_SMALL_08":1,"PLAIN_MEDIUM_01":1,"PLAIN_MEDIUM_02":1,"PLAIN_MEDIUM_03":2,"PLAIN_MEDIUM_04":1,
    "PLAIN_MEDIUM_05":1,"PLAIN_MEDIUM_06":2,"PLAIN_LARGE_01":1,"PLAIN_LARGE_02":1,"PLAIN_LARGE_03":2,"PLAIN_LARGE_04":1,
    "PLAIN_LARGE_05":1,"PLAIN_LARGE_06":2,"COMP 01.01":2,"COMP 01.02":2,"COMP 01.03":1,"COMP 01.04":1,"COMP 02.01":3,
    "COMP 02.02":3,
    # "COMP 02.03":3,"COMP 02.04":4,
    # "COMP 03.01":None,"COMP 03.02":None,"COMP 03.03":None,"COMP 03.04":None,
    # "COMP 04.01":3,"COMP 04.02":None,"COMP 04.03":None,"COMP 04.04":None,
    "RW 01":4,"2Level_01":2,"2Level_02":2,
    "2Level_03":2,"2Level_04":2,"2Level_05":1,"2Level_06":1,"2Level_07":1,"2Level_08":2,"2Level_09":2,"2Level_10":2
}

alg2 = {
    "up_fw1":7,"up_fw2":6,"up_hc":7,"up_domino":5,"up_apj":6,"up_as":9,"up_al":4,"up_emea":1,"up_univ":5,"mailer":7,
    "PLAIN_SMALL_01":4,"PLAIN_SMALL_02":5,"PLAIN_SMALL_03":4,"PLAIN_SMALL_04":4,"PLAIN_SMALL_05":4,"PLAIN_SMALL_06":5,
    "PLAIN_SMALL_07":6,"PLAIN_SMALL_08":4,"PLAIN_MEDIUM_01":4,"PLAIN_MEDIUM_02":6,"PLAIN_MEDIUM_03":7,"PLAIN_MEDIUM_04":5,
    "PLAIN_MEDIUM_05":5,"PLAIN_MEDIUM_06":6,"PLAIN_LARGE_01":5,"PLAIN_LARGE_02":6,"PLAIN_LARGE_03":6,"PLAIN_LARGE_04":5,
    "PLAIN_LARGE_05":6,"PLAIN_LARGE_06":6,"COMP 01.01":8,"COMP 01.02":7,"COMP 01.03":8,"COMP 01.04":8,"COMP 02.01":10,
    "COMP 02.02":4,
    # "COMP 02.03":None,"COMP 02.04":None,"COMP 03.01":None,"COMP 03.02":None,"COMP 03.03":None,"COMP 03.04":None,
    # "COMP 04.01":None,"COMP 04.02":None,"COMP 04.03":None,"COMP 04.04":None,
    "RW 01":8,"2Level_01":5,"2Level_02":4,
    "2Level_03":4,"2Level_04":4,"2Level_05":4,"2Level_06":4,"2Level_07":5,"2Level_08":5,"2Level_09":3,"2Level_10":6
}

# ---- Normalize order (use the order from Vaidya dict) ----
order = list(vaidya.keys())

# ---- Create a DataFrame ----
df = pd.DataFrame({
    "benchmark": order,
    "vaidya_layers": [vaidya[k] for k in order],
    "alg1_layers_after_pruning": [alg1.get(k) for k in order],
    "alg2_layers_after_pruning": [alg2.get(k) for k in order],
})

# Pretty labels
def pretty_name(name: str) -> str:
    s = name.lower().replace("up_","").replace("plain_","")
    s = s.replace("_", " ")
    return s

df["label"] = df["benchmark"].map(pretty_name)

# ---- Plot ----
fig, ax = plt.subplots(figsize=(12, 5))

x = np.arange(len(df))

def plot_series(y, label, marker):
    xs, ys = [], []
    segments = []
    for i, val in enumerate(y):
        if val is None or (isinstance(val, float) and np.isnan(val)):
            if xs:
                segments.append((xs, ys))
                xs, ys = [], []
        else:
            xs.append(i)
            ys.append(val)
    if xs:
        segments.append((xs, ys))
    for (xs_seg, ys_seg) in segments:
        if marker == 'o':
            ax.plot(xs_seg, ys_seg, marker=marker, linestyle=':', label=label, color='k')
        elif marker == '^':
            ax.plot(xs_seg, ys_seg, marker=marker, linestyle='--', label=label, color='k')
        else:
            ax.plot(xs_seg, ys_seg, marker=marker, linestyle='-', label=label, color='k')

plot_series(df["vaidya_layers"].tolist(), "RHMiner", 'o')
plot_series(df["alg1_layers_after_pruning"].tolist(), "MinRolesRH (after pruning)", 's')
plot_series(df["alg2_layers_after_pruning"].tolist(), "NewRolesRH (after pruning)", '^')

ax.set_xticks(x)
ax.set_xticklabels(df["label"].tolist(), rotation=60, ha='right')
ax.set_ylabel(" # layers")
# ax.set_title("Layers per benchmark: Vaidya vs. Alg 1/2 (after pruning)")
ax.grid(True, axis='y', linestyle=':', linewidth=0.7)

# Deduplicate legend entries
handles, labels = ax.get_legend_handles_labels()
dedup = dict(zip(labels, handles))
ax.legend(dedup.values(), dedup.keys(), loc='best', frameon=False)

plt.tight_layout()

# Save outputs
png_path = "layers_lineplot.pdf"
# csv_path = "/mnt/data/layers_lineplot_data.csv"
plt.savefig(png_path, dpi=200, bbox_inches='tight')
# df.to_csv(csv_path, index=False)
#
# png_path, csv_path
