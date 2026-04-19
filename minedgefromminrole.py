#! /usr/bin/python3
import os
import sys
import datetime
import time
import random


prefix_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(f'{prefix_dir}')
sys.path.append(f'{prefix_dir}/..')
sys.path.append(f'{prefix_dir}/../..')

from readup import readup, readup_and_usermap_permmap
from readup import dumpup
from readup import uptopu
from removedominators import readem
from removedominators import dmfromem
from minedgetoilp import minedgetoilp

from itertools import combinations


def countedges(roletousersmap, roletopermsmap):
    n = 0  # return value
    for r in roletousersmap:
        n += len(roletousersmap[r])
    for r in roletopermsmap:
        n += len(roletopermsmap[r])
    return n


def nextrolesubset(roletousersmap, roletopermsmap):
    rset = set(roletousersmap.keys())
    k = 2  # for each k-sized subset of roles

    # sort roles by num edges per role, non-increasing
    l = list()
    for r in rset:
        nedges = len(roletousersmap[r]) + len(roletopermsmap[r])
        l.append(tuple((r, nedges)))
    l.sort(key=lambda e: e[1], reverse=False)
    print('Sorted roles by edges:')
    print(l)

    indexset = set()
    for i in range(len(rset)):
        indexset.add(i)

    for t in combinations(indexset, k):
        s = set()
        for i in t:
            s.add(l[i][0])
        # print('yielding:', s)
        yield s




def minrole_to_minedge(up, em, totalTime, perSolveTime):
    print('Start time:', datetime.datetime.now())

    # up = readup(sys.argv[1])
    if not up:
        print('Empty up; nothing to do.')
        return

    # em = readem(sys.argv[2])
    if not em:
        print('Empty em; nothing to do.')
        return

    dm = dmfromem(em)

    """
    print('em:')
    for e in em:
        print(str(e)+': '+str(em[e]))
    print('dm:')
    for d in dm:
        print(str(d)+': '+str(dm[d]))
    """

    if tuple((-1, -1)) not in dm:
        print("Hm...something wrong; no (-1,-1) in dm. Quitting...")
        return

    # totalTime = int(sys.argv[3])
    # perSolveTime = int(sys.argv[4])

    # First setup the roles
    roletoedgemap = dict()
    edgetorolemap = dict()
    oldrolenum = 0
    rolenum = 0
    for e in dm[tuple((-1, -1))]:
        roletoedgemap[rolenum] = e
        edgetorolemap[e] = rolenum
        rolenum += 1

    # Now users & perms to those roles
    roletousersmap = dict()
    roletopermsmap = dict()

    for r in roletoedgemap:
        roletousersmap[r] = set()
        roletopermsmap[r] = set()

        # A simple kind of BFS
        q = list()
        q.append(roletoedgemap[r])

        while q:
            e = q.pop(0)
            u = e[0]
            p = e[1]

            (roletousersmap[r]).add(u)
            (roletopermsmap[r]).add(p)

            if e in dm:
                q.extend(dm[e])

    """
    print('roletousersmap:')
    for r in roletousersmap:
        print(str(r)+': '+str(roletousersmap[r]))

    print('roletopermsmap:')
    for r in roletopermsmap:
        print(str(r)+': '+str(roletopermsmap[r]))
    """

    roundnum = 0
    startTimeForTotalTime = int(time.time())

    while oldrolenum < rolenum:
        roundnum += 1

        print('Total # roles after round', (roundnum - 1), ':', len(roletousersmap))
        print('Total # edges after round', (roundnum - 1), ':', countedges(roletousersmap, roletopermsmap))
        sys.stdout.flush()

        if (int(time.time()) - startTimeForTotalTime) > totalTime:
            break

        diffroles = dict()  # out catalogue of old & new

        # for rsubtuple in combinations(rset, k):
        for rsubset in nextrolesubset(roletousersmap, roletopermsmap):
            if (int(time.time()) - startTimeForTotalTime) > totalTime:
                break

            print('rsubset:', sorted(rsubset))
            sys.stdout.flush()

            tonextsubtuple = False
            for r in rsubset:
                if r < oldrolenum:
                    # This role no longer exists
                    tonextsubtuple = True
                    break
            if tonextsubtuple:
                continue

            # First, the num edges in this subset of roles
            currnedges = 0
            for r in rsubset:
                currnedges += len(roletousersmap[r])
                currnedges += len(roletopermsmap[r])

            thisup = dict()
            thisusers = set()
            thisperms = set()
            thisnedges = 0

            for r in rsubset:
                uset = roletousersmap[r]
                pset = roletopermsmap[r]
                thisusers.update(uset)
                thisperms.update(pset)
                for u in uset:
                    if u not in thisup:
                        thisup[u] = set()
                    (thisup[u]).update(pset)
                    thisnedges += len(pset)

            new_nedges, new_roletousersmap, new_roletopermsmap = minedgetoilp(thisup, perSolveTime)

            if new_nedges < 0:
                continue

            if new_nedges < currnedges:
                print('currnedges:', currnedges, ', new_nedges:', new_nedges, ', num_new_roles:',
                      len(new_roletousersmap.keys()))
                print('curr_roles + {users}, {perms}:')
                for r in rsubset:
                    print('\t' + str(r) + ': ' + str(sorted(roletousersmap[r])) + ', ' + str(sorted(roletopermsmap[r])))
                print('new_roles + {users}, {perms}:')
                for r in new_roletousersmap:
                    print('\t' + str(r) + ': ' + str(sorted(new_roletousersmap[r])) + ', ' + str(
                        sorted(new_roletopermsmap[r])))

                sys.stdout.flush()

                diff = currnedges - new_nedges
                if diff not in diffroles:
                    diffroles[diff] = list()

                thisdiffrolesentry = list()

                thisolddiffentries = list()
                for r in rsubset:
                    thisrentry = r

                    thisrentryusers = set()
                    thisrentryusers.update(roletousersmap[r])

                    thisrentryperms = set()
                    thisrentryperms.update(roletopermsmap[r])

                    oneolddiffentry = list()
                    oneolddiffentry.append(thisrentry)
                    oneolddiffentry.append(thisrentryusers)
                    oneolddiffentry.append(thisrentryperms)

                    thisolddiffentries.append(oneolddiffentry)

                thisdiffrolesentry.append(thisolddiffentries)

                thisnewdiffentries = list()
                for r in new_roletousersmap:
                    thisrentry = r

                    thisrentryusers = set()
                    thisrentryusers.update(new_roletousersmap[r])

                    thisrentryperms = set()
                    thisrentryperms.update(new_roletopermsmap[r])

                    onenewdiffentry = list()
                    onenewdiffentry.append(thisrentry)
                    onenewdiffentry.append(thisrentryusers)
                    onenewdiffentry.append(thisrentryperms)

                    thisnewdiffentries.append(onenewdiffentry)

                thisdiffrolesentry.append(thisnewdiffentries)
                (diffroles[diff]).append(thisdiffrolesentry)

        print('diffroles:')
        for d in diffroles:
            print('    ' + str(d) + ':')
            for l in diffroles[d]:
                print('        old:')
                for m in l[0]:
                    print('            ' + str(m))
                print('        new:')
                for m in l[1]:
                    print('            ' + str(m))

        alldiff = sorted(set(diffroles.keys()), reverse=True)
        oldrolenum = rolenum
        for d in alldiff:
            while diffroles[d]:
                onesub = (diffroles[d]).pop()  # one set of roles
                # to be substituted
                onesubold = onesub[0]
                onesubnew = onesub[1]

                # First check if all old roles still exist
                oldrolesexist = True
                for m in onesubold:
                    if m[0] not in roletousersmap:
                        # print('Old role', m[0], 'is not in roletousersmap')
                        oldrolesexist = False
                        break
                    # else:
                    # print('Old role', m[0], 'is indeed in roletousersmap')
                if not oldrolesexist:
                    continue

                # Remove all old roles
                for m in onesubold:
                    del roletousersmap[m[0]]
                    del roletopermsmap[m[0]]

                # Add new roles
                # WARNING: role #'s should be disregarded
                for m in onesubnew:
                    roletousersmap[rolenum] = set()
                    (roletousersmap[rolenum]).update(m[1])
                    roletopermsmap[rolenum] = set()
                    (roletopermsmap[rolenum]).update(m[2])
                    rolenum += 1

    if int(time.time()) - startTimeForTotalTime > totalTime:
        print('Total time exceeded ' + str(totalTime) + ' seconds')
    else:
        print('Fixpoint reached.')
    print('End time:', datetime.datetime.now())
    sys.stdout.flush()
    return roletousersmap, roletopermsmap




def main():
    print('Start time:', datetime.datetime.now())
    sys.stdout.flush()

    if len(sys.argv) != 5:
        print('Usage: ', end='')
        print(sys.argv[0], end=' ')
        print('<input-up-file> <input-em-file> <total time (s)> <per solve time (s)>')
        return

    print('Invoked as:', sys.argv)

    up = readup(sys.argv[1])
    if not up:
        print('Empty up; nothing to do.')
        return

    em = readem(sys.argv[2])
    if not em:
        print('Empty em; nothing to do.')
        return

    dm = dmfromem(em)

    """
    print('em:')
    for e in em:
        print(str(e)+': '+str(em[e]))
    print('dm:')
    for d in dm:
        print(str(d)+': '+str(dm[d]))
    """

    if tuple((-1, -1)) not in dm:
        print("Hm...something wrong; no (-1,-1) in dm. Quitting...")
        return

    totalTime = int(sys.argv[3])
    perSolveTime = int(sys.argv[4])

    # First setup the roles
    roletoedgemap = dict()
    edgetorolemap = dict()
    oldrolenum = 0
    rolenum = 0
    for e in dm[tuple((-1, -1))]:
        roletoedgemap[rolenum] = e
        edgetorolemap[e] = rolenum
        rolenum += 1

    # Now users & perms to those roles
    roletousersmap = dict()
    roletopermsmap = dict()

    for r in roletoedgemap:
        roletousersmap[r] = set()
        roletopermsmap[r] = set()

        # A simple kind of BFS
        q = list()
        q.append(roletoedgemap[r])

        while q:
            e = q.pop(0)
            u = e[0]
            p = e[1]

            (roletousersmap[r]).add(u)
            (roletopermsmap[r]).add(p)

            if e in dm:
                q.extend(dm[e])

    """
    print('roletousersmap:')
    for r in roletousersmap:
        print(str(r)+': '+str(roletousersmap[r]))

    print('roletopermsmap:')
    for r in roletopermsmap:
        print(str(r)+': '+str(roletopermsmap[r]))
    """

    roundnum = 0
    startTimeForTotalTime = int(time.time())

    while oldrolenum < rolenum:
        roundnum += 1

        print('Total # roles after round', (roundnum - 1), ':', len(roletousersmap))
        print('Total # edges after round', (roundnum - 1), ':', countedges(roletousersmap, roletopermsmap))
        sys.stdout.flush()

        if (int(time.time()) - startTimeForTotalTime) > totalTime:
            break

        diffroles = dict()  # out catalogue of old & new

        # for rsubtuple in combinations(rset, k):
        for rsubset in nextrolesubset(roletousersmap, roletopermsmap):
            if (int(time.time()) - startTimeForTotalTime) > totalTime:
                break

            print('rsubset:', sorted(rsubset))
            sys.stdout.flush()

            tonextsubtuple = False
            for r in rsubset:
                if r < oldrolenum:
                    # This role no longer exists
                    tonextsubtuple = True
                    break
            if tonextsubtuple:
                continue

            # First, the num edges in this subset of roles
            currnedges = 0
            for r in rsubset:
                currnedges += len(roletousersmap[r])
                currnedges += len(roletopermsmap[r])

            thisup = dict()
            thisusers = set()
            thisperms = set()
            thisnedges = 0

            for r in rsubset:
                uset = roletousersmap[r]
                pset = roletopermsmap[r]
                thisusers.update(uset)
                thisperms.update(pset)
                for u in uset:
                    if u not in thisup:
                        thisup[u] = set()
                    (thisup[u]).update(pset)
                    thisnedges += len(pset)

            new_nedges, new_roletousersmap, new_roletopermsmap = minedgetoilp(thisup, perSolveTime)

            if new_nedges < 0:
                continue

            if new_nedges < currnedges:
                print('currnedges:', currnedges, ', new_nedges:', new_nedges, ', num_new_roles:',
                      len(new_roletousersmap.keys()))
                print('curr_roles + {users}, {perms}:')
                for r in rsubset:
                    print('\t' + str(r) + ': ' + str(sorted(roletousersmap[r])) + ', ' + str(sorted(roletopermsmap[r])))
                print('new_roles + {users}, {perms}:')
                for r in new_roletousersmap:
                    print('\t' + str(r) + ': ' + str(sorted(new_roletousersmap[r])) + ', ' + str(
                        sorted(new_roletopermsmap[r])))

                sys.stdout.flush()

                diff = currnedges - new_nedges
                if diff not in diffroles:
                    diffroles[diff] = list()

                thisdiffrolesentry = list()

                thisolddiffentries = list()
                for r in rsubset:
                    thisrentry = r

                    thisrentryusers = set()
                    thisrentryusers.update(roletousersmap[r])

                    thisrentryperms = set()
                    thisrentryperms.update(roletopermsmap[r])

                    oneolddiffentry = list()
                    oneolddiffentry.append(thisrentry)
                    oneolddiffentry.append(thisrentryusers)
                    oneolddiffentry.append(thisrentryperms)

                    thisolddiffentries.append(oneolddiffentry)

                thisdiffrolesentry.append(thisolddiffentries)

                thisnewdiffentries = list()
                for r in new_roletousersmap:
                    thisrentry = r

                    thisrentryusers = set()
                    thisrentryusers.update(new_roletousersmap[r])

                    thisrentryperms = set()
                    thisrentryperms.update(new_roletopermsmap[r])

                    onenewdiffentry = list()
                    onenewdiffentry.append(thisrentry)
                    onenewdiffentry.append(thisrentryusers)
                    onenewdiffentry.append(thisrentryperms)

                    thisnewdiffentries.append(onenewdiffentry)

                thisdiffrolesentry.append(thisnewdiffentries)
                (diffroles[diff]).append(thisdiffrolesentry)

        print('diffroles:')
        for d in diffroles:
            print('    ' + str(d) + ':')
            for l in diffroles[d]:
                print('        old:')
                for m in l[0]:
                    print('            ' + str(m))
                print('        new:')
                for m in l[1]:
                    print('            ' + str(m))

        alldiff = sorted(set(diffroles.keys()), reverse=True)
        oldrolenum = rolenum
        for d in alldiff:
            while diffroles[d]:
                onesub = (diffroles[d]).pop()  # one set of roles
                # to be substituted
                onesubold = onesub[0]
                onesubnew = onesub[1]

                # First check if all old roles still exist
                oldrolesexist = True
                for m in onesubold:
                    if m[0] not in roletousersmap:
                        # print('Old role', m[0], 'is not in roletousersmap')
                        oldrolesexist = False
                        break
                    # else:
                    # print('Old role', m[0], 'is indeed in roletousersmap')
                if not oldrolesexist:
                    continue

                # Remove all old roles
                for m in onesubold:
                    del roletousersmap[m[0]]
                    del roletopermsmap[m[0]]

                # Add new roles
                # WARNING: role #'s should be disregarded
                for m in onesubnew:
                    roletousersmap[rolenum] = set()
                    (roletousersmap[rolenum]).update(m[1])
                    roletopermsmap[rolenum] = set()
                    (roletopermsmap[rolenum]).update(m[2])
                    rolenum += 1

    if int(time.time()) - startTimeForTotalTime > totalTime:
        print('Total time exceeded ' + str(totalTime) + ' seconds')
    else:
        print('Fixpoint reached.')
    print('End time:', datetime.datetime.now())
    sys.stdout.flush()
    return roletousersmap, roletopermsmap


if __name__ == '__main__':
    main()
