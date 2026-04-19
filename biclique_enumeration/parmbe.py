import multiprocessing as mp
from collections import defaultdict

def parLMBC(X: set, neighbours, tail, ms):
    # sort vertices of tail(X) into ascending order of neighbours(X + {v})
    def sort_vertices(tailXvertices: list):
        neighbourhood_size = dict()
        for u in tailXvertices:
            neighbourhood_size[u] = len(neighbours(X.union({v})))
        sorted(tailXvertices, key=neighbourhood_size.get)


    tailX = tail(X)
    neighboursX = neighbours(X)
    for v in tailX:
        if len(neighbours(X.union({v}))) < ms:
            tailX = tailX.difference({v})

    if len(X) + len(tailX) < ms:
        return

    sorted_tailX = sort_vertices(list(tailX))
    k = len(sorted_tailX)
    for i in range(k):
        ntailX = sorted_tailX[i+1 : k-1]
        if len(X.union({v})) + len(ntailX) > ms:
            Y = neighbours(neighbours(X.union({v})))
            if Y.difference(X.union({v})).issubset(ntailX):
                if len(Y) >= ms:
                    print(Y, neighbours(X.union({v})))
                parLMBC(Y, neighbours(X.union({v})), ntailX.difference(Y), ms)







# ---- Example usage ----
if __name__ == "__main__":
    mp.set_start_method("fork" if hasattr(mp, "fork") else "spawn", force=True)

    graph = {
        'u1': ['p1', 'p2'],
        'u2': ['p2', 'p3'],
        'u3': ['p1', 'p3'],
        'p1': ['u1', 'u3'],
        'p2': ['u1', 'u2'],
        'p3': ['u2', 'u3']
    }

    X = []
    tail = ['u1', 'u2', 'u3']
    ms = 2

    output = ParLMBC(graph, X, tail, ms)
    print("Maximal Bicliques:")
    for biclique in output:
        print(biclique)
