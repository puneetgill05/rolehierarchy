import os
import sys
from typing import Set

prefix_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(f'{prefix_dir}')
sys.path.append(f'{prefix_dir}/Utils')
sys.path.append(f'{prefix_dir}/../..')
print(sys.path)

from Vertex import Vertex


class BipartiteGraph:
    def __init__(self, L: Set[Vertex], R: Set[Vertex]):
        self.L = L
        self.R = R
        self.E = set()
        for u in self.L:
            for v in u.neighbours:
                self.E.add((u, v))

    def update(self):
        self.E = set()

        for u in self.L:
            for v in u.neighbours:
                self.E.add((u, v))

    def edges(self) -> Set:
        E = set()
        for u in self.L:
            for v in u.neighbours:
                E.add((u, v))
        return E

    @classmethod
    def from_dict(cls, G: dict):
        L = set()
        R = set()
        for l in G:
            vl = Vertex(l)
            if vl in L:
                vl = get(L, vl)
            for r in G[l]:
                vr = Vertex(r)
                if vr in R:
                    vr = get(R, vr)
                vl.add_neighbour_symmetric(vr)
                R.add(vr)
            L.add(vl)
        return BipartiteGraph(L, R)

    def get_vertex_from_L(self, label: str) -> Vertex:
        for l in self.L:
            if l.label == label:
                return l

    def get_vertex_from_R(self, label: str) -> Vertex:
        for r in self.R:
            if r.label == label:
                return r

    def __str__(self):
        ret = ''
        for l in self.L:
            R_str = ', '.join([r.label for r in l.neighbours])
            ret += str(l.label) + ': [' + R_str + ']\n'
        return ret


def get(items: Set[Vertex], item: Vertex):
    for it in items:
        if item == it:
            return it
    return None


def add_all(items: Set[Vertex], items_to_add: Set[Vertex]) -> Set[Vertex]:
    for item in items_to_add:
        items.add(item)
    return items
