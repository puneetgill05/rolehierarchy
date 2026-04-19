import os
import sys


prefix_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(f'{prefix_dir}/..')
sys.path.append(f'{prefix_dir}/../..')
print(sys.path)

from readup import readup_and_usermap_permmap, dumpup


def build_user_perm_dict(up: dict):
    inv_permmap = {v: k for k, v in permmap.items()}
    inv_usermap = {v: k for k, v in usermap.items()}


    perms = set()
    for u in up:
        for p in up[u]:
            perms.add(p)
    # index users and perms
    user_labels = dict()
    perm_labels = dict()
    i = 0
    for u in up:
        user = f'{i}'
        if user not in user_labels:
            user_labels[u] = user
        i += 1

    j = 0
    for p in perms:
        perm = f'{j}'
        perm_labels[p] = perm
        j += 1

    user_perm_dict = dict()
    for u in up:
        for p in up[u]:
            user = user_labels[u]
            perm = perm_labels[p]
            if user not in user_perm_dict:
                user_perm_dict[user] = set()
            user_perm_dict[user].add(perm)

    return user_perm_dict


upfilename = '/home/puneet/Projects/minedgerolemining/minedgerolemining/inputsup/UP-mailer'
upoutfilename = f'{upfilename}-mapped'
up, usermap, permmap = readup_and_usermap_permmap(upfilename)

user_perm_dict = build_user_perm_dict(up)
dumpup(user_perm_dict, upoutfilename)