#!/usr/bin/env python3

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# ---- Raw data from the user ----
vaidya = {
    "fw1":3,
    "fw2":2,
    "hc":3,
    "domino":2,
    "apj":3,
    "as":3,
    "al":3,
    "emea":1,
    "univ":2,
    "mailer":3,
    "small 01":1,
    "small 02":2,
    "small 03":2,
    "small 04":1,
    "small 05":2,
    "small 06":2,
    "small 07":2,
    "small 08":1,
    "medium 01":1,
    "medium 02":1,
    "medium 03":2,
    "medium 04":1,
    "medium 05":1,
    "medium 06":2,
    "large 01":1,
    "large 02":1,
    "large 03":2,
    "large 04":1,
    "large 05":1,
    "large 06":2,
    "comp 01.1":2,
    "comp 01.2":2,
    "comp 01.3":1,
    "comp 01.4":1,
    "comp 02.1":3,
    "comp 02.2":1,
    "comp 02.3":2,
    "comp 02.4":1,
    "comp 03.1":2,
    "comp 03.2":2,
    "comp 03.3":4,
    "comp 03.4":2,
    "comp 04.1":3,
    "comp 04.2":3,
    "comp 04.3":3,
    "comp 04.4":0,
    "rw 01":4,
    "2 level 01":2,
    "2 level 02":1,
    "2 level 03":2,
    "2 level 04":2,
    "2 level 05":1,
    "2 level 06":1,
    "2 level 07":1,
    "2 level 08":1,
    "2 level 09":2,
    "2 level 10":2
}

alg1 = {
    "fw1":4,
    "fw2":3,
    "hc":3,
    "domino":3,
    "apj":3,
    "as":4,
    "al":3,
    "emea":1,
    "univ":3,
    "mailer":5,
    "small 01":2,
    "small 02":2,
    "small 03":2,
    "small 04":1,
    "small 05":2,
    "small 06":2,
    "small 07":2,
    "small 08":1,
    "medium 01":1,
    "medium 02":1,
    "medium 03":2,
    "medium 04":1,
    "medium 05":1,
    "medium 06":2,
    "large 01":1,
    "large 02":1,
    "large 03":2,
    "large 04":1,
    "large 05":1,
    "large 06":2,
    "comp 01.1":2,
    "comp 01.2":2,
    "comp 01.3":1,
    "comp 01.4":1,
    "comp 02.1":3,
    "comp 02.2":3,
    "comp 02.3":4,
    "comp 02.4":3,
    "comp 03.1":6,
    "comp 03.2":5,
    "comp 03.3":9,
    "comp 03.4":6,
    "comp 04.1":3,
    "comp 04.2":3,
    "comp 04.3":3,
    "comp 04.4":3,
    "rw 01":5,
    "2 level 01":2,
    "2 level 02":2,
    "2 level 03":2,
    "2 level 04":2,
    "2 level 05":1,
    "2 level 06":1,
    "2 level 07":1,
    "2 level 08":2,
    "2 level 09":2,
    "2 level 10":2
}

alg2 = {
    "fw1":7,
    "fw2":6,
    "hc":7,
    "domino":5,
    "apj":6,
    "as":9,
    "al":4,
    "emea":1,
    "univ":5,
    "mailer":8,
    "small 01":4,
    "small 02":5,
    "small 03":4,
    "small 04":4,
    "small 05":4,
    "small 06":5,
    "small 07":6,
    "small 08":4,
    "medium 01":4,
    "medium 02":6,
    "medium 03":7,
    "medium 04":5,
    "medium 05":5,
    "medium 06":6,
    "large 01":5,
    "large 02":6,
    "large 03":6,
    "large 04":5,
    "large 05":6,
    "large 06":6,
    "comp 01.1":8,
    "comp 01.2":7,
    "comp 01.3":8,
    "comp 01.4":8,
    "comp 02.1":13,
    "comp 02.2":12,
    "comp 02.3":14,
    "comp 02.4":0,
    "comp 03.1":11,
    "comp 03.2":5,
    "comp 03.3":9,
    "comp 03.4":8,
    "comp 04.1":10,
    "comp 04.2":8,
    "comp 04.3":12,
    "comp 04.4":0,
    "rw 01":11,
    "2 level 01":5,
    "2 level 02":4,
    "2 level 03":4,
    "2 level 04":4,
    "2 level 05":4,
    "2 level 06":4,
    "2 level 07":5,
    "2 level 08":5,
    "2 level 09":3,
    "2 level 10":6
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
plot_series(df["alg1_layers_after_pruning"].tolist(), "MinRolesRH", 's')
plot_series(df["alg2_layers_after_pruning"].tolist(), "NewRolesRH", '^')

ax.set_xticks(x)
# ax.set_xticklabels(df["label"].tolist(), rotation=60, ha='right')
ax.set_xticklabels(df["label"].tolist(), rotation=90)
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
