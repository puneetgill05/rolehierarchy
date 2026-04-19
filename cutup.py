#! /usr/bin/python3

import sys
import datetime
from readup import readup

def main():
    print('Start time:', datetime.datetime.now())
    sys.stdout.flush()

    if len(sys.argv) != 3:
        print('Usage: ', end = '')
        print(sys.argv[0], end = ' ')
        print('<input-file> <npieces>')
        return

    upfilename = sys.argv[1]

    up = readup(upfilename)
    npieces = int(sys.argv[2])

    if not up:
        return

    nu = len(up)

    print('Total # users:', nu)
    sys.stdout.flush()

    cnt = 0
    piece = 0
    f = None
    r = open(upfilename, 'r')
    for line in r:
        cnt += 1
        if cnt > piece * nu/npieces:
            if f:
                f.close()
                print('done!')
                sys.stdout.flush()

            piece += 1
            outfilename = upfilename + '-cutup-' + str(piece) + '.txt'
            f = open(outfilename, 'w')
            print('Writing piece', piece, 'to', outfilename, '...', end='')
            sys.stdout.flush()
        f.write(line)
    if f:
        f.close()
        print('done!')
        sys.stdout.flush()

    r.close()

    print('Total # users written:', cnt)
    print('End time:', datetime.datetime.now())

if __name__ == '__main__':
    main()
