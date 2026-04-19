import numpy as np
import cvxpy as cp
from scipy.linalg import sqrtm


def gw(n, edges):
    X = cp.Variable((n, n), symmetric=True)
    constraints = [X >> 0]
    constraints += [
        X[i, i] == 1 for i in range(n)
    ]
    objective = sum( 0.5*(1 - X[i, j]) for (i, j) in edges)
    prob = cp.Problem(cp.Maximize(objective), constraints)
    prob.solve()

    ## Hyperplane Rounding
    Q = sqrtm(X.value).real
    r = np.random.randn(n)
    x = np.sign(Q @ r)

    return x


def cut(x, edges):
    '''Given a vector x \in {-1, 1}^n and edges of a graph G(V=[n], E=edges),
    returns the edges in cut(S) for the subset of vertices S of V represented by x.'''
    xcut = []
    for i, j in edges:
        if np.sign(x[i]*x[j]) < 0:
            xcut.append((i, j))
    return xcut


n = 6
edges = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 4), (0, 5), (2, 5)]

x = gw(n, edges)

## Find edges in the cut
xcut = cut(x, edges)

print('Chosen subset: %s' % np.where(x == 1))
print('Cut size: %i' % len(xcut))
print('Edges of the cut: %s' % xcut)