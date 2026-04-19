import numpy as np
import networkx as nx
from collections import defaultdict

class Node2Vec:
    def __init__(self, G: nx.Graph, p=1.0, q=1.0):
        self.G = G
        self.p = p
        self.q = q
        self.alias_nodes = {}
        self.alias_edges = {}
        self._preprocess_transition_probs()

    def _alias_setup(self, probs):
        K = len(probs)
        q = np.zeros(K)
        J = np.zeros(K, dtype=int)
        smaller, larger = [], []
        for kk, prob in enumerate(probs):
            q[kk] = K * prob
            (smaller if q[kk] < 1.0 else larger).append(kk)
        while smaller and larger:
            small = smaller.pop()
            large = larger.pop()
            J[small] = large
            q[large] = q[large] - (1.0 - q[small])
            (smaller if q[large] < 1.0 else larger).append(large)
        return J, q

    def _alias_draw(self, J, q):
        K = len(J)
        kk = int(np.floor(np.random.rand() * K))
        return kk if np.random.rand() < q[kk] else J[kk]

    def _get_alias_edge(self, src, dst):
        unnormalized = []
        for nbr in self.G.neighbors(dst):
            if nbr == src:
                unnormalized.append(1 / self.p)
            elif self.G.has_edge(nbr, src):
                unnormalized.append(1)
            else:
                unnormalized.append(1 / self.q)
        norm_const = sum(unnormalized)
        normalized = [u / norm_const for u in unnormalized]
        return self._alias_setup(normalized)

    def _preprocess_transition_probs(self):
        for node in self.G.nodes():
            probs = np.array([self.G[node][nbr].get("weight", 1.0)
                              for nbr in self.G.neighbors(node)])
            probs /= probs.sum()
            self.alias_nodes[node] = self._alias_setup(probs)
        for edge in self.G.edges():
            self.alias_edges[edge] = self._get_alias_edge(*edge)
            self.alias_edges[(edge[1], edge[0])] = self._get_alias_edge(edge[1], edge[0])

    def _node2vec_walk(self, walk_length, start_node):
        G = self.G
        walk = [start_node]
        while len(walk) < walk_length:
            cur = walk[-1]
            cur_nbrs = list(G.neighbors(cur))
            if len(cur_nbrs) == 0:
                break
            if len(walk) == 1:
                J, q = self.alias_nodes[cur]
                next_node = cur_nbrs[self._alias_draw(J, q)]
            else:
                prev = walk[-2]
                J, q = self.alias_edges[(prev, cur)]
                next_node = cur_nbrs[self._alias_draw(J, q)]
            walk.append(next_node)
        return walk

    def simulate_walks(self, num_walks, walk_length):
        nodes = list(self.G.nodes())
        walks = []
        for _ in range(num_walks):
            np.random.shuffle(nodes)
            for node in nodes:
                walks.append(self._node2vec_walk(walk_length, node))
        return walks


def run_node2vec(G, num_walks):
    node2vec = Node2Vec(G, p=0.25, q=4.0)  # DFS bias
    walks = node2vec.simulate_walks(num_walks=5, walk_length=10)

    for w in walks[:5]:
        print(w)