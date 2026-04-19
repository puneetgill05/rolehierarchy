#! /usr/bin/python3

import sys
import time
import datetime

from minedgerolemining.readup import readup
from minedgerolemining.readup import uptopu
from minedgerolemining.removedominatorsbp import readem
from minedgerolemining.removedominatorsbp import dmfromem
from findcliquesbp import find_bicliquesbp, find_bicliquesbp2
from mapup import mapup

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

    if not up:
        return

    up = mapup(up, upfilename)

    pu = uptopu(up)
    
    #emfile
    emfilename = upfilename + '-em.txt'

    print('Reading em from', emfilename, '...', end='')
    sys.stdout.flush()

    em = readem(emfilename)
    dm = dmfromem(em)

    print('done!')
    sys.stdout.flush()

    THRESHOLD = 100
    nc = 0
    timeone = time.time()
    for c in find_bicliquesbp(em, up, pu, list()):
        if not nc:
            timetwo = time.time()
            print('First clique found, time:', timetwo - timeone, '...')
            sys.stdout.flush()
        nc += 1
        if not nc % 1000:
            timetwo = time.time()
            print('# cliques:', nc, '; time:', timetwo - timeone, '...')
            sys.stdout.flush()
            timeone = time.time()

        if len(c) >= THRESHOLD:
            print(set(c))

    print('End time:', datetime.datetime.now())

if __name__ == '__main__':
    main()
