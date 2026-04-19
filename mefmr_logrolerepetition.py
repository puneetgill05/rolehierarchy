#! /usr/bin/python3

import sys
import re

def addOneSetOfRoles(d, f):
    for m in f:
        s = m.split()
        if not s:
            break
        t = re.findall(r'-?\d+\.?\d*', s[0])
        if (not t) or (not (t[0]).isdigit()):
            break
        #else
        tasint = int(t[0])
        d[tasint] = list()
        thisusers = set()
        i = 1
        while i < len(s):
            thisusers.add(int(re.findall(r'-?\d+\.?\d*', s[i])[0]))
            i += 1
            if ']' in s[i-1]:
                #last user
                break

        thisperms = set()
        while i < len(s):
            thisperms.add(int(re.findall(r'-?\d+\.?\d*', s[i])[0]))
            i += 1

        (d[tasint]).append(thisusers)
        (d[tasint]).append(thisperms)


def checkLogFileForRoleRepetitions(fname):
    f = open(fname, 'r')
    itnum = 0

    for l in f:
        if 'curr_roles' in l:
            #print('curr_roles:')
            curr_roles = dict()
            addOneSetOfRoles(curr_roles, f)
            #print(curr_roles)

            #print('new_roles:')
            new_roles = dict()
            addOneSetOfRoles(new_roles, f)
            #print(new_roles)

            #Is there a new role that is a current role?
            newRoleIsCurrRole = False
            for r in new_roles:
                for s in curr_roles:
                    if new_roles[r][0] == curr_roles[s][0] and new_roles[r][1] == curr_roles[s][1]:
                        newRoleIsCurrRole = True
                        print('new_roles['+str(r)+'] = '+str(new_roles[r])+' == curr_roles['+str(s)+'] = '+str(curr_roles[s]))
                        break
                if newRoleIsCurrRole:
                    break
            if not newRoleIsCurrRole:
                print('curr_roles:', end=' ')
                for r in curr_roles:
                    print(r, end=' ')
                print('none occurs in new_roles:', end=' ')
                for r in new_roles:
                    print(r, end=' ')
                print()

    f.close()

def main():
    if len(sys.argv) != 2:
        print('Usage: ', end='')
        print(sys.argv[0], end=' ')
        print('<input-log-file>')
        return

    print('Invoked as:', sys.argv)
    sys.stdout.flush()

    checkLogFileForRoleRepetitions(sys.argv[1])

if __name__ == '__main__':
    main()

