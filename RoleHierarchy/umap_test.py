import os
import sys

import numpy as np
from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

prefix_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(f'{prefix_dir}/..')

from readup import readup,readup_and_usermap_permmap


def draw_umap(data, n_neighbors=15, min_dist=0.1, n_components=2, metric='euclidean', title=''):
    fit = umap.UMAP(
        n_neighbors=n_neighbors,
        min_dist=min_dist,
        n_components=n_components,
        metric=metric
    )
    u = fit.fit_transform(data)
    fig = plt.figure()
    if n_components == 1:
        ax = fig.add_subplot(111)
        ax.scatter(u[:,0], range(len(u)), c=data)
    if n_components == 2:
        ax = fig.add_subplot(111)
        ax.scatter(u[:,0], u[:,1], c=data)
    if n_components == 3:
        ax = fig.add_subplot(111, projection='3d')
        ax.scatter(u[:,0], u[:,1], u[:,2], c=data, s=100)
    plt.title(title, fontsize=18)

upfilename = '/home/puneet/Projects/minedgerolemining/minedgerolemining/inputsup/UP-fw1'

up, usermap, permmap = readup_and_usermap_permmap(upfilename)
inv_usermap = {v: k for k, v in usermap.items()}
inv_permmap = {v: k for k, v in permmap.items()}

up_df = pd.DataFrame()
rows = list()
for u in up:
    # row = {'user': inv_usermap[u]}
    row = {'user': u}
    for p in inv_permmap:
        row[inv_permmap[p]] = 0
    for p in up[u]:
        row[inv_permmap[p]] = 1
    print(row)
    rows.append(row)
# print(rows)

up_df = pd.DataFrame(rows)

import umap

reducer = umap.UMAP(random_state=42, n_components=3)
scaled_up_data = StandardScaler().fit_transform(up_df)

embedding = reducer.fit_transform(scaled_up_data)
print(embedding.shape)

# plt.scatter(
#     embedding[:, 0],
#     embedding[:, 1],
#     c=up_df.user,
#     cmap='Spectral', s=64)
# plt.gca().set_aspect('equal', 'datalim')
# plt.title('UMAP projection of the Penguin dataset', fontsize=24)
#
# plt.show()

draw_umap(up_df, n_components=2)


