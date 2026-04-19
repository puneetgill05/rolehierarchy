#! /usr/bin/python3

import sys

def BK(G, R, P, X, depth, Xseen):
    if X not in Xseen:
        Xseen.append(X)

    Rstr = str(R)
    #if not R:
    #    Rstr = '{ }'
    Pstr = str(P)
    #if not P:
    #    Pstr = '{ }'
    Xstr = str(X)
    #if not X:
    #    Xstr = '{ }'

    for i in range(depth):
        print('\t',end='')
    print('BK('+Rstr+', '+Pstr+', '+Xstr+')')
    sys.stdout.flush()
    if not P and not X:
        yield R
        return
    copyP = P.copy()
    for u in copyP:
        P.remove(u)
        Rnew = R.copy()
        Rnew.add(u)
        Pnew = P.copy()
        Pnew.intersection_update(G[u])
        Xnew = X.copy()
        Xnew.intersection_update(G[u])
        for c in BK(G, Rnew, Pnew, Xnew, depth + 1, Xseen):
            yield c
        X.add(u)

def readGraphFromFile(fname):
    f = open(fname, 'r')
    G = list()
    u = 0
    for line in f:
        if line[0] == '#':
            # a comment
            continue
        thisAdjSet = set()
        neighbours = line.split()
        for n in neighbours:
            thisAdjSet.add(int(n))

        G.append(thisAdjSet)
        #print(str(u)+': '+str(thisAdjSet))
        u += 1
    f.close()
    return G

def main():
    if len(sys.argv) != 2:
        print('Usage: ', end = '')
        print(sys.argv[0], end = ' ')
        print('<graph-file>')
        return

    G = readGraphFromFile(sys.argv[1])
    #print('G:', G)

    P = set() # set of vertices in G
    u = 0
    for v in G:
        P.add(u)
        u += 1

    #print('P:', P)
    R = set()
    X = set()

    niter = 0
    Xseen = list()
    for c in BK(G, R, P, X, 0, Xseen):
        print(str(c))
        sys.stdout.flush()

    """
    print('Xseen:')
    maxssize = 0
    for s in Xseen:
        if len(s) > maxssize:
            maxssize = len(s)

    for l in range(maxssize + 1):
        for s in Xseen:
            if len(s) == l:
                print('\t'+str(s))
    """
if __name__ == '__main__':
    main()
