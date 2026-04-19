import sys

from minedgerolemining.readup import readup, writefile
from minedgerolemining.removedominators import readem


def readrp(rp_filepath):
    rp_content = open(rp_filepath, 'r')

    rp = dict()
    for line in rp_content:
        l = line.split(':')
        m = (l[1][1:len(l[1]) - 2]).split(',')
        role = l[0]
        permissions = set()

        for p in m:
            q = p.split("'")
            for perm in q:
                if not (not perm or perm.isspace()):
                    permissions.add(perm)
        rp[role] = permissions
    rp_content.close()
    return rp


def readur(ur_filepath):
    ur_content = open(ur_filepath, 'r')

    ur = dict()
    for line in ur_content:
        l = line.split(':')
        m = (l[1][1:len(l[1]) - 2]).split(',')
        user = l[0]
        roles = set()

        for r in m:
            q = r.split("'")
            for role in q:
                if not (not role or role.isspace()):
                    roles.add(role)
        ur[user] = roles
    ur_content.close()
    return ur


def create_up(ur, rp):
    up = dict()
    for u in ur:
        permissions = set()
        for r in rp:
            if r in ur[u]:
                permissions = permissions.union(rp[r])
        up[u] = list(permissions)
    return up


def up_to_str(up):
    ret = str()
    for u in up:
        perms = up[u]
        ret += u + ': ' + str(perms) + '\n'
    return ret


def up_as_list(up_str):
    up_list = []
    for item in up_str.split('\n'):
        if item:
            up_list.append(item)
    return up_list


def does_cross_check_pass(rp_filepath, ur_filepath, up_filepath):
    rp = readrp(rp_filepath)
    ur = readur(ur_filepath)

    up_created = create_up(ur, rp)
    writefile(up_created, 'up_created.txt')
    up_created = readup('up_created.txt')

    up = readup(up_filepath)
    print('UP:', up)
    print('UP created:', up_created)
    are_equal = up.keys() == up_created.keys()

    # return is_equal(up, up_created)
    return are_equal


# def readsolfile(fname, filenum, rmap, ru, rp):
#     rolenum = 1 + len(rmap)  # next role id
#
#     # get all the roles first
#     f = open(fname, "r")
#     for line in f.readlines():
#         if line[0] == 'e' and int((line.split())[1]) == 1:
#             # a role
#             l = line.split()
#             rmap[str(filenum) + "-" + l[0][1:]] = rolenum
#             rolenum += 1
#
#     f.close()
#
#     # Then user-role and perm-role assignments
#     f = open(fname, "r")
#     for line in f.readlines():
#         if (line[0] == 'd' or line[0] == 'c') and int((line.split())[1]) == 1:
#             # perm or user
#             l = line.split()
#             m = (l[0][1:]).split("_")
#             rname = str(filenum) + "-" + m[1]
#
#             if rname not in rmap:
#                 # This role presumably has a 0 on its exxx line
#                 print('Error! role:', rname, 'user/perm:', (line.split())[0], flush=True)
#                 continue
#
#             if line[0] == 'd':
#                 # perm
#                 if rmap[rname] not in rp:
#                     rp[rmap[rname]] = set()
#                 rp[rmap[rname]].add(int(m[0]))
#             else:
#                 # user
#                 if rmap[rname] not in ru:
#                     ru[rmap[rname]] = set()
#
#                 ru[rmap[rname]].add(int(m[0]))
#     f.close()


def process_em(emfilepath: str):
    upr = dict()
    em = readem(emfilepath)

    edges_assigned = set()
    rolenum = 0
    for e in em:
        (dm_u, dm_p, seq) = em[e]
        dm = (dm_u, dm_p)
        if dm == (-1, -1):
            upr[e] ='r{rolenum}'.format(rolenum=rolenum)
            edges_assigned.add(e)
            rolenum += 1

    while upr.keys() != em.keys():
        for e in em:
            (dm_u, dm_p, seq) = em[e]
            dm = (dm_u, dm_p)
            if e not in upr:
                if dm in upr:
                    upr[e] = upr[dm]

    roles_assigned = dict()
    for e in upr:
        if upr[e] in roles_assigned:
            roles_assigned[upr[e]].add(e)
        else:
            roles_assigned[upr[e]] = {e}

    # for r in roles_assigned:
    #     roles_assigned[r] = list(roles_assigned[r])
    return roles_assigned


def main():
    if len(sys.argv) != 2:
        print('Usage: ', end='')
        print(sys.argv[0], end=' ')
        print('<em_filepath>')
        return

    roles_assigned = process_em(sys.argv[1])
    print(roles_assigned)


    # ur_filepath = sys.argv[1]
    # ru = dict()
    # rp = dict()
    # rmap = dict()
    # sol_filepath = sys.argv[2]
    # readsolfile(sol_filepath, 0, rmap, ru, rp)
    #
    # print(ru)
    # print(rp)
    # print()
    # ret = does_cross_check_pass(rp_filepath, ur_filepath, up_filepath)
    # print('Are they equal?', 'Yes' if ret else 'No')
    # print(ret)


if __name__ == "__main__":
    main()
