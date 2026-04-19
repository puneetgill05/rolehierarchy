from typing import Set

from Vertex import Vertex


class Biclique(object):
    def __init__(self, L: Set[Vertex], R: Set[Vertex]):
        self.L = L
        self.R = R
        for u in self.L:
            u.add_neighbours_symmetric(R)

    def __str__(self):
        ret = ''
        for l in self.L:
            R_str = ', '.join([r.label for r in self.R])
            ret += str(l.label) + ': [' + R_str + ']\n'
        return ret