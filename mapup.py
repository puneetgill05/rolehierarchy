#! /usr/bin/python3

def  mapup(up, upfilename):
    # upfilename = upfilename.replace('.txt', '')
    myupmapfilename = upfilename + '-upmap.txt'
    masterupmapfilename = upfilename[0:upfilename.index('-cutup-')] + '-upmap.txt'

    print('myupmapfilename:', myupmapfilename)
    print('masterupmapfilename:', masterupmapfilename)

    masf = open(masterupmapfilename, 'r')
    masumap = dict() # name --> id
    maspmap = dict() # name --> id

    for line in masf:
        l = line.split(':')
        if l[0][0] == 'u' or l[0][0] == 'U':
            masumap[int(l[0][1:])] = int(l[1])
        else:
            maspmap[int(l[0][1:])] = int(l[1])
    masf.close()

    myf = open(myupmapfilename, 'r')
    myumap = dict() # id --> name
    mypmap = dict() # id --> name

    for line in myf:
        l = line.split(':')
        if l[0][0] == 'u' or l[0][0] == 'U':
            myumap[int(l[1])] = int(l[0][1:])
        else:
            mypmap[int(l[1])] = int(l[0][1:])

    myf.close()

    #print('up:', up)
    #print('masumap:', masumap)
    #print('myumap:', myumap)
    #print('maspmap:', maspmap)
    #print('mypmap:', mypmap)

    newup = dict() # return value
    for u in up:
        masu = masumap[myumap[u]]
        newup[masu] = set()
        for p in up[u]:
            masp = maspmap[mypmap[p]]
            (newup[masu]).add(masp)

    return newup

# if __name__ == '__main__':
    # main()
