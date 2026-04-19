#! /usr/bin/python3

import sys

def readup(infile):
    # map users and perms to ids 0, 1, 2...
    uid = 0
    pid = 0
    usermap = dict()
    permmap = dict()

    ret = dict()
    i = open(infile, 'r')

    for e in i:
        l = e.split(':')
        if(len(l) != 2):
            print('Error: UP file, length != 2')
            i.close()
            return None
        else:
            if l[0] not in usermap:
                usermap[l[0]] = uid
                #print('usermap;', str(l[0]), ',', str(uid))
                uid = uid + 1
            ret[usermap[l[0]]] = set()
            # Proceed assuming 1st char in l[1] is [, last is ]
            m = (l[1][1:len(l[1])-2]).split(',')
            for p in m:
                q = p.split("'")
                for r in q:
                    if not(not r or (r[0]).isspace()):
                        if r not in permmap:
                            permmap[r] = pid
                            #print('permmap;', str(r), ',', str(pid))
                            pid = pid + 1
                        (ret[usermap[l[0]]]).add(permmap[r])
    i.close()

    upmapfilename = infile + '-upmap.txt'
    w = open(upmapfilename, 'w')
    for u in usermap:
        w.write(u+':'+str(usermap[u])+'\n')
    for p in permmap:
        w.write(p+':'+str(permmap[p])+'\n')
    w.close()
    print('UP map written to', upmapfilename)
    sys.stdout.flush()

    return ret

def uptopu(up):
    pu = dict()
    for u in up:
        for p in up[u]:
            if p not in pu:
                (pu[p]) = set()
            (pu[p]).add(u)

    return pu

def dumpup(up, outfile):
    o = open(outfile, "w")
    k = list(up)
    k.sort()
    for u in k:
        o.write("U" + str(u) + ":")
        isfirst = True
        for p in up[u]:
            if not isfirst:
                o.write(",")
            else:
                o.write("[")
                isfirst = False
            o.write("\'P"+ str(p) +"\'")
        o.write("]\n")

    o.close()

def main():
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print('Usage: ', end = '')
        print(sys.argv[0], end = ' ')
        print('<input-file>')
        return

    up = readup(sys.argv[1])
    if not up:
        return

    pu = uptopu(up)

    #outfile = sys.argv[1] + "-outputUP.txt"
    #dumpup(up, outfile)
    print('nusers = ', len(up))
    print('nperms = ', len(pu))

    nedges = 0
    for u in up:
        nedges += len(up[u])
    print('nedges = ', nedges)

    """
    visualizeup(up, "up.html")
    print('Bipartite graph dumped to up.html')

    G = constructGNetworkx(up)
    visualizeG(G, "G.html")
    print('Reduced graph dumped to G.html')
    """

if __name__ == '__main__':
    main()
