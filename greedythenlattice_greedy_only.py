#! /usr/bin/python3

import datetime
import sys
import time

from utils import get_roles_mapped, inverse_map, getResults
from minedgerolemining.readup import readup
from minedgerolemining.readup import uptopu


def latticeshrink(rolesasperms):
    print('Running lattice-based shrinking...')
    niter = 0
    fixpoint = False
    while not fixpoint:
        fixpoint = True #optimistically

        for j in range(len(rolesasperms)):
            niter += 1
            if not (niter % 1000):
                print('niter:', niter, '...')
                sys.stdout.flush()

            r = rolesasperms.pop(0)
            #identify set of roles that are contained in this one
            otherpset = set()
            for i in range(len(rolesasperms)):
                if (rolesasperms[i]).issubset(r):
                    otherpset.update(rolesasperms[i])

            if otherpset:
                fixpoint = False
                r.difference_update(otherpset)
                if r:
                    rolesasperms.append(r)
                #else:
                #    print('removing role', r)
                break
            else:
                rolesasperms.append(r)

def getdegtoverts(up, pu):
    verttodeg = dict()
    degtoverts = dict()

    for u in up:
        du = len(up[u])
        if du not in degtoverts:
            degtoverts[du] = set()
        verttodeg['u'+str(u)] = du
        (degtoverts[du]).add('u'+str(u))

    for p in pu:
        dp = len(pu[p])
        if dp not in degtoverts:
            degtoverts[dp] = set()
        verttodeg['p'+str(p)] = dp
        (degtoverts[dp]).add('p'+str(p))

    return degtoverts, verttodeg

def smallestdeg(degtoverts):
    if not degtoverts:
        #print('smallestdeg, returning None')
        return None
    ks = list(degtoverts.keys())
    ks.sort()
    #print('smallestdeg, returning', ks[0], ', verts:', degtoverts[ks[0]])
    return ks[0] 

def largestdeg(degtoverts):
    if not degtoverts:
        #print('largestdeg, returning None')
        return None
    ks = list(degtoverts.keys())
    ks.sort(reverse=True)
    #print('largestdeg, returning', ks[0], ', verts:', degtoverts[ks[0]])
    return ks[0] 


def run(upfilename: str):
    up = readup(upfilename)

    if not up:
        return

    pu = uptopu(up)

    # print('up:', up)
    # print('pu:', pu)

    print('# vertices:', len(up) + len(pu))

    # Remove dominators first; create those roles
    # print('Removing dominators...')
    # sys.stdout.flush()
    # emfilename = sys.argv[1] + '-em.txt'
    # if os.path.exists(emfilename):
    #     em = readem(emfilename)
    #     dm = dmfromem(em)
    #     print('em read from', emfilename)
    #     sys.stdout.flush()
    # else:
    #     em = dict()
    #     dm = dict()
    #     seq = 0
    #     seq = removedominators(em, dm, up, seq)
    #     saveem(em, emfilename)
    #     print('em saved to', emfilename)
    #     sys.stdout.flush()
    #
    # print('done!')
    # sys.stdout.flush()

    # print('em:', em)
    # print('dm:', dm)

    # nzerodeg = 0
    # if tuple((-1,-1)) in dm:
    #    nzerodeg = len(dm[tuple((-1,-1))])
    # print('# roles identified:', nzerodeg)
    # sys.stdout.flush()

    rolesasperms = list()

    # create rolesasperms for those roles
    # if tuple((-1, -1)) in dm:
    #     G = nx.Graph()
    #     for e in dm:
    #         if e == tuple((-1, -1)):
    #             for f in dm[e]:
    #                 G.add_node(f)
    #         else:
    #             for f in dm[e]:
    #                 G.add_edge(e, f)
    #
    #     roleedges = dm[tuple((-1, -1))]
    #     for c in nx.connected_components(G):
    #         if c.intersection(roleedges):
    #             # print('c.intersection(roleedges):', c.intersection(roleedges))
    #             # print('connected component:', c)
    #             r = set()
    #             myrole = set()
    #             for t in c:
    #                 r.add(t[1])
    #                 myrole.add((t[0], t[1]))
    #             rolesasperms.append(r)
    #             # roles_as_edges.append(myrole)
    #
    #             # remove those edges from up and pu
    #             for t in c:
    #                 if t[0] in up and t[1] in up[t[0]]:
    #                     (up[t[0]]).remove(t[1])
    #                     if not up[t[0]]:
    #                         del up[t[0]]
    #                 if t[0] in pu[t[1]]:
    #                     (pu[t[1]]).remove(t[0])
    #                     if not pu[t[1]]:
    #                         del pu[t[1]]
    #
    # print('len(rolesasperms):', len(rolesasperms))
    # Onto our greedy algorithm...

    starttime = time.time()
    # vertices and degrees
    degtoverts, verttodeg = getdegtoverts(up, pu)

    # print('degtoverts:', degtoverts)
    # print('verttodeg:', verttodeg)

    print('Running greedy algorithm...')
    sys.stdout.flush()

    niter = 0
    s = smallestdeg(degtoverts)
    # s = largestdeg(degtoverts)
    while s:
        niter += 1
        if not (niter % 100000):
            print('niter:', str(niter), '...')
            sys.stdout.flush()

        # print('Smallest deg:', s)
        vert = (degtoverts[s]).pop()
        if not degtoverts[s]:
            del degtoverts[s]

        # print('popped', vert)
        # if vert[0] == 'u':
        #    print('is user', int(vert[1:]))
        # else:
        #    print('is perm', int(vert[1:]))

        # get max biclique for vert
        m = set()
        if vert[0] == 'u':
            u = int(vert[1:])
            nu = up[u]
            nv = set()  # users who are neighbours of all perms
            for v in nu:
                t = tuple((u, v))
                m.add(t)
                if not nv:
                    nv.update(pu[v])
                else:
                    nv.intersection_update(pu[v])

            if u not in nv:
                # BUG!
                print('BUG! user', u, 'not in nv')
                sys.exit(0)

            for w in nv:
                for v in nu:
                    t = tuple((w, v))
                    m.add(t)
        else:
            p = int(vert[1:])
            np = pu[p]
            nv = set()  # perms who are neighbours of all users
            for v in np:
                t = tuple((v, p))
                m.add(t)
                if not nv:
                    nv.update(up[v])
                else:
                    nv.intersection_update(up[v])

            if p not in nv:
                # BUG!
                print('BUG! perm', p, 'not in nv')
                sys.exit(0)

            for w in nv:
                for v in np:
                    t = tuple((v, w))
                    m.add(t)

        # print('max biclique:', m)
        umodded = set()
        pmodded = set()  # keep track of u's and p's impacted
        myrole = set()
        for t in m:
            umodded.add(t[0])
            pmodded.add(t[1])
            myrole.add((t[0], t[1]))

        rolesasperms.append(pmodded)
        # roles_as_edges.append(myrole)

        for u in umodded:
            (up[u]).difference_update(pmodded)
            degu = len(up[u])
            olddegu = verttodeg['u' + str(u)]
            if (olddegu in degtoverts) and (('u' + str(u)) in degtoverts[olddegu]):
                (degtoverts[olddegu]).remove('u' + str(u))
                if not degtoverts[olddegu]:
                    del degtoverts[olddegu]
            if degu == 0:
                del verttodeg['u' + str(u)]
            else:
                verttodeg['u' + str(u)] = degu
                if degu not in degtoverts:
                    degtoverts[degu] = set()
                (degtoverts[degu]).add('u' + str(u))

        for p in pmodded:
            (pu[p]).difference_update(umodded)
            degp = len(pu[p])
            olddegp = verttodeg['p' + str(p)]
            if (olddegp in degtoverts) and (('p' + str(p)) in degtoverts[olddegp]):
                (degtoverts[olddegp]).remove('p' + str(p))
                if not degtoverts[olddegp]:
                    del degtoverts[olddegp]
            if degp == 0:
                del verttodeg['p' + str(p)]
            else:
                verttodeg['p' + str(p)] = degp
                if degp not in degtoverts:
                    degtoverts[degp] = set()
                (degtoverts[degp]).add('p' + str(p))

        s = smallestdeg(degtoverts)
        # s = largestdeg(degtoverts)

    # print('find_bicliquesbp:')
    # for c in find_bicliquesbp(dict(), up, pu, list()):
    #    print(c)

    # print('rolesasperms:', rolesasperms)
    print('len(rolesasperms):', len(rolesasperms))


    # latticeshrink(rolesasperms)
    # print('len(rolesasperms):', len(rolesasperms))

    up = readup(upfilename)
    roles_as_edges = from_roles_as_perms_to_edges(rolesasperms, up)
    # print('myroles:', roles_as_edges)
    print('len(roles_as_edges):', len(roles_as_edges))
    roles_mapped = get_roles_mapped(roles_as_edges)


    endtime = time.time()
    print('End time:', datetime.datetime.now())
    print('Total time (seconds):', endtime - starttime)
    sys.stdout.flush()
    return roles_as_edges, roles_mapped


def from_roles_as_perms_to_edges(rolesasperms: list, up: dict) -> list:
    pu = inverse_map(up)
    roles_as_edges = list()
    for role in rolesasperms:
        role_as_edges = set()
        users = set(up.keys())
        for perm in role:
            users = users.intersection(pu[perm])

        for u in users:
            for perm in role:
                role_as_edges.add((u, perm))
        roles_as_edges.append(role_as_edges)
    return roles_as_edges


def main():
    print('Start time:', datetime.datetime.now())
    sys.stdout.flush()

    if len(sys.argv) != 2:
        print('Usage: ', end = '')
        print(sys.argv[0], end = ' ')
        print('<input-file>')
        return
    upfilename = sys.argv[1]
    # up = readup(upfilename)
    roles_as_edges, _ = run(upfilename)
    total_num_roles, total_num_edges = getResults(roles_as_edges)
    print('Total # roles: ', total_num_roles)
    print('Total # edges: ', total_num_edges)

if __name__ == '__main__':
    main()
