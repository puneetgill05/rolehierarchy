# from MBEA.NSet import NSet


class Vertex(object):

    def __init__(self, label):
        self.label = label
        self.neighbours = set()


    def to_dict(self):
        ret = dict()
        ret['label'] = self.label
        ret['neighbours'] = []
        for neighbour in self.neighbours:
            ret['neighbours'].append(neighbour.label)
        return ret

    @staticmethod
    def from_dict(vertex_dict: dict):
        v = Vertex(vertex_dict['label'])

        for n in vertex_dict['neighbours']:
            vertex_n = Vertex(n)
            # if vertex_n in vertices:
            v.add_neighbour_symmetric(vertex_n)
        return v




    def __repr__(self):
        return f"Vertex(label={self.label}, neighbours={list(self.neighbours)})"


    def __str__(self):
        # neighbours_str = ', '.join(str(n) for n in self.neighbours)
        return f'Vertex(label: {str(self.label)})'

    def __eq__(self, other):
        if not isinstance(other, Vertex):
            return False
        return self.label == other.label

    def __hash__(self):
        try:
            if self.label:
                return hash(self.label)
        except:
            print('Something wrong')
        return None

    def get_neighbours(self):
        return self.neighbours

    def get_label(self):
        return self.label

    def add_neighbour(self, v):
        if not self.is_neighbour(v):
            self.neighbours.add(v)

    def add_neighbours(self, vertices: set):
        for v in vertices:
            self.add_neighbour(v)

    def remove_neighbour(self, v):
        if v in self.neighbours:
            self.neighbours.remove(v)

    def add_neighbour_symmetric(self, v):
        if not self.is_neighbour(v):
            self.add_neighbour(v)
        if not v.is_neighbour(self):
            v.add_neighbour(self)

    def add_neighbours_symmetric(self, vertices: set):
        for v in vertices:
            self.add_neighbour_symmetric(v)

    def remove_neighbour_symmetric(self, v):
        if self.is_neighbour(v):
            self.remove_neighbour(v)
        if v.is_neighbour(self):
            v.remove_neighbour(self)

    def num_neighbours(self):
        return len(self.neighbours)

    # Returns true if v is in the neighbours of self, false otherwise
    def is_neighbour(self, v):
        return v in self.neighbours


def add_edge(v1: Vertex, v2: Vertex):
    if v1 not in v2.neighbours:
        v2.neighbours.add(v1)
    if v2 not in v1.neighbours:
        v1.neighbours.add(v2)


def remove_edge(v1: Vertex, v2: Vertex):
    if v1 in v2.neighbours:
        v2.neighbours.remove(v1)
    if v2 in v1.neighbours:
        v1.neighbours.remove(v2)
