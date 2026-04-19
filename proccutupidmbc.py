#! /usr/bin/python3

import sys
import datetime

import re

from minedgerolemining.readup import readup
from minedgerolemining.readup import uptopu
from minedgerolemining.removedominatorsbp import readem
from minedgerolemining.removedominatorsbp import dmfromem
from minedgerolemining.removedominatorsbp import hasbeenremoved
from mapup import mapup

def removembc(thismbc, em, seq, thresh):
    emkeys = set(em.keys())

    if len(thismbc.difference(set(em.keys()))) < thresh:
        return False, seq

    nedges = 0
    firstedge = None
    for e in thismbc:
        if hasbeenremoved(e, em):
            continue
        nedges += 1
        seq += 1
        if not firstedge:
            # first edge to be removed
            em[e] = tuple((-1, -1, seq))
            firstedge = e
        else:
            em[e] = tuple((firstedge[0], firstedge[1], seq))

    print('removembc, # edges removed:', nedges)
    sys.stdout.flush()

    return True, seq

def main():
    print('Start time:', datetime.datetime.now())
    sys.stdout.flush()

    if len(sys.argv) != 2:
        print('Usage: ', end = '')
        print(sys.argv[0], end = ' ')
        print('<input-file>')
        return


    upfilename = sys.argv[1]
    if '-cutup-' not in upfilename:
        print('Input file is not -cutup-; exiting...')
        sys.exit(0)

    up = readup(upfilename)

    up = mapup(up, upfilename)

    if not up:
        return

    pu = uptopu(up)
    
    #emfile
    emfilename = upfilename + '-em.txt'

    print('Reading em from', emfilename, '...', end='')
    sys.stdout.flush()

    em = readem(emfilename)
    dm = dmfromem(em)

    print('done!')
    sys.stdout.flush()

    #logfile
    logfilename = upfilename + '-idmbc.log'
    print('Reading log from', logfilename, '...')
    sys.stdout.flush()

    MBC_SAVE_THRESHOLD = 100

    mbcnum = 0
    mbcsizes = dict()
    savedmbcs = dict()

    f = open(logfilename, 'r')
    for line in f:
        if line[0] == '{':
            mbcnum += 1
            thismbc = set()
            r = re.findall(r'-?\d+\.?\d*', line)
            for i in range(0, len(r), 2):
                t = tuple((int(r[i]), int(r[i+1])))
                thismbc.add(t)

            if len(thismbc) not in mbcsizes:
                mbcsizes[len(thismbc)] = 0
            mbcsizes[len(thismbc)] += 1

            #print('mbc #', mbcnum, '; size:', len(thismbc))
            #sys.stdout.flush()

            if len(thismbc) >= MBC_SAVE_THRESHOLD:
                if len(thismbc) not in savedmbcs:
                    savedmbcs[len(thismbc)] = list()
                (savedmbcs[len(thismbc)]).append(thismbc)
    
    f.close()

    diffsizes = list(mbcsizes.keys())
    diffsizes.sort(reverse=True)

    """
    print('mbcsizes:')
    for d in diffsizes:
        print('\t'+str(d)+':'+str(mbcsizes[d]))
    """

    bucketsizes = dict()
    for i in range(MBC_SAVE_THRESHOLD, 1000, 100):
        bucketsizes[i] = 0

    for m in mbcsizes:
        for b in bucketsizes:
            if m >= b:
                bucketsizes[b] += mbcsizes[m]

    sb = list(bucketsizes.keys())
    sb.sort()

    print('mbc sizes by bucket:')
    for b in sb:
        print('\t'+str(b)+': '+str(bucketsizes[b]))

    """
    ###########################################################################
    #REMOVAL CODE START
    ###########################################################################

    seq = 0
    for e in em:
        if em[e][2] > seq:
            seq = em[e][2]

    MBC_REM_THRESHOLD = 200

    print('len(em) at start:', len(em))

    remmbcnum = 0
    k = list(savedmbcs.keys())
    k.sort(reverse=True)
    for s in k:
        while savedmbcs[s]:
            thismbc = (savedmbcs[s]).pop()
            ret, seq = removembc(thismbc, em, seq, MBC_REM_THRESHOLD)
            if ret:
                remmbcnum += 1
                print('mbc #', remmbcnum, 'removed.')
                print('new len(em):', len(em))

    print('Writing new em to file:', emfilename, '...', end='')
    sys.stdout.flush()

    saveem(em, emfilename)

    print('done!')
    sys.stdout.flush()

    ###########################################################################
    #REMOVAL CODE END
    ###########################################################################
    """

    print('End time:', datetime.datetime.now())

if __name__ == '__main__':
    main()
