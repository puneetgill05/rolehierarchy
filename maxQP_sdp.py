import datetime
import sys

import cvxpy as cp

from minedgerolemining.algorithms.createQP import rindex
from minedgerolemining.readup import readup


def sdp_relax(n, up: dict, users: set, perms: set, nroles: int):
    C = cp.Variable((len(users), nroles), symmetric=False)
    D = cp.Variable((nroles, len(perms)), symmetric=False)

    constr_C_PSD = C >> 0
    constr_D_PSD = C >> 0

    constraints = [constr_C_PSD, constr_D_PSD]

    constr_u_has_p = None
    for u in up.keys():
        for p in up[u]:
            # for r in range(nroles):
            constr_u_has_p = C[u,:] @ D[:,p]
            constraints.append(constr_u_has_p >= 1)

    objective = None
    for r in range(nroles):
        objective = cp.sum(C) + cp.sum(D)
        # for u in users:
        #     if objective is None:
        #         objective = C[u, r]
        #     else:
        #         objective += C[u, r]
        # for p in perms:
        #     objective += D[r, p]

    prob = cp.Problem(cp.Minimize(objective), constraints)
    print('Prob is DCP: ', prob.is_dcp())
    prob.solve()
    if prob.status == cp.OPTIMAL:
        print('Optimal solution:', C.value)

    ## Hyperplane Rounding
    # Q = sqrtm(X.value).real
    # r = np.random.randn(n)
    # x = np.sign(Q @ r)
    #
    # return x


def main():
    n = 5
    edges = [(0, 1), (0, 2), (0, 3), (0, 4), (1, 2), (1, 3), (2, 4)]


    print('Start time:', datetime.datetime.now())
    sys.stdout.flush()

    if len(sys.argv) != 2:
        print('Usage: ', end='')
        print(sys.argv[0], end=' ')
        print('<input-file>')
        return

    last_sep_index = rindex(sys.argv[1], '/')
    filepath = sys.argv[1][:last_sep_index]
    filename = sys.argv[1][last_sep_index:]

    up = readup(sys.argv[1])
    if not up:
        return

    nedges = 0
    users = set()
    perms = set()
    for u in up:
        users.add(u)
        perms = perms.union(up[u])
        nedges += len(up[u])

    sdp = sdp_relax(n, up, users, perms, nroles=min(len(users), len(perms)))


if __name__ == '__main__':
    main()