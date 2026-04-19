import sys
import time
from datetime import datetime

from minedgerolemining import maxsetsbp
from minedgerolemining.procsol import process_em
from minedgerolemining.readup import uptopu, readup, writefile, readup_and_usermap_permmap
from minedgerolemining.removedominators import neighbours


# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'minrolemining')))

def min_edge_to_min_role(up: dict, upfilepath: str):
    pu = uptopu(up)

    up_min_role = dict()
    for u in up:
        for p in up[u]:
            e = (u, p)

            for ne in neighbours(e, dict(), up, pu):
                e_str = 'e_({u} {p})'.format(u=u, p=p)
                ne_str = 'e_({u} {p})'.format(u=ne[0], p=ne[1])

                r_same_str = 'r_same_({u} {p})_({ne_u} {ne_p})'.format(u=u, p=p, ne_u=ne[0], ne_p=ne[1])
                r_diff_str = 'r_diff_({u} {p})_({ne_u} {ne_p})'.format(u=u, p=p, ne_u=ne[0], ne_p=ne[1])

                a_str = 'a_({u} {p})_({ne_u} {ne_p})'.format(u=u, p=p, ne_u=ne[0], ne_p=ne[1])
                b_str = 'b_({u} {p})_({ne_u} {ne_p})'.format(u=u, p=p, ne_u=ne[0], ne_p=ne[1])
                c_str = 'c_({u} {p})_({ne_u} {ne_p})'.format(u=u, p=p, ne_u=ne[0], ne_p=ne[1])

                z1_str = 'z_({u} {p})_1'.format(u=u, p=p)
                z2_str = 'z_({u} {p})_2'.format(u=u, p=p)
                z3_str = 'z_({u} {p})_3'.format(u=u, p=p)

                if e_str in up_min_role:
                    r_ne_same_str = 'r_same_({u} {p})_({ne_u} {ne_p})'.format(u=ne[0], p=ne[1], ne_u=u, ne_p=p)
                    r_ne_diff_str = 'r_diff_({u} {p})_({ne_u} {ne_p})'.format(u=ne[0], p=ne[1], ne_u=u, ne_p=p)
                    if (not (r_same_str in up_min_role[e_str] and r_diff_str in up_min_role[e_str]) and
                            not (r_ne_same_str in up_min_role[e_str] and r_ne_diff_str in up_min_role[e_str])):
                        up_min_role[e_str].add(r_same_str)
                        up_min_role[e_str].add(r_diff_str)
                else:
                    up_min_role[e_str] = {r_same_str, r_diff_str}

                if ne_str in up_min_role:
                    r_ne_same_str = 'r_same_({u} {p})_({ne_u} {ne_p})'.format(u=ne[0], p=ne[1], ne_u=u, ne_p=p)
                    r_ne_diff_str = 'r_diff_({u} {p})_({ne_u} {ne_p})'.format(u=ne[0], p=ne[1], ne_u=u, ne_p=p)
                    if (not (r_same_str in up_min_role[ne_str] and r_diff_str in up_min_role[ne_str]) and
                            not (r_ne_same_str in up_min_role[ne_str] and r_ne_diff_str in up_min_role[ne_str])):
                        up_min_role[ne_str].add(r_same_str)
                        up_min_role[ne_str].add(r_diff_str)
                else:
                    up_min_role[ne_str] = {r_same_str, r_diff_str}

                if z1_str in up_min_role:
                    up_min_role[z1_str].add(r_same_str)
                    up_min_role[z1_str].add(a_str)
                    up_min_role[z1_str].add(b_str)
                else:
                    up_min_role[z1_str] = {r_same_str, a_str, b_str}

                if z2_str in up_min_role:
                    up_min_role[z2_str].add(r_diff_str)
                    up_min_role[z2_str].add(b_str)
                    up_min_role[z2_str].add(c_str)
                else:
                    up_min_role[z2_str] = {r_diff_str, b_str, c_str}

                if z3_str in up_min_role:
                    up_min_role[z3_str].add(a_str)
                    up_min_role[z3_str].add(b_str)
                    up_min_role[z3_str].add(c_str)
                else:
                    up_min_role[z3_str] = {a_str, b_str, c_str}

    print(up_min_role)
    upfilepath = upfilepath.replace('.txt', '')
    up_reduced_filepath = upfilepath + '-reduced.txt'
    writefile(up_min_role, up_reduced_filepath)
    _, usermap, permmap = readup_and_usermap_permmap(up_reduced_filepath)
    maxsetsbp.run(up_reduced_filepath)
    up_reduced_em_filepath = up_reduced_filepath.replace('.txt', '') + '-em.txt'
    roles_assigned = process_em(up_reduced_em_filepath)
    print(roles_assigned)

    inv_usermap = {v: k for k, v in usermap.items()}
    inv_permmap = {v: k for k, v in permmap.items()}

    roles_assigned_mapped = dict()
    for r in roles_assigned:
        for e in roles_assigned[r]:
            if e[0] in inv_usermap and e[1] in inv_permmap:
                u = inv_usermap[e[0]]
                p = inv_permmap[e[1]]
                if r in roles_assigned_mapped:
                    roles_assigned_mapped[r].add((u, p))
                else:
                    roles_assigned_mapped[r] = {(u, p)}

    print(roles_assigned_mapped)
    return roles_assigned_mapped




def post_process(roles_assigned_mapped):
    ret = dict()
    role_num = 0
    perms = dict()
    counter = 1
    new_roles_assigned_mapped = dict()
    for r in roles_assigned_mapped:
        edges = dict()
        edges2 = dict()
        for e in roles_assigned_mapped[r]:
            (u, p) = e
            if u.startswith('e_') and p.startswith('r_'):
                q = ''
                if p.startswith('r_diff'):
                    q = p.replace('r_diff', 'r_same')
                elif p.startswith('r_same'):
                    q = p.replace('r_same', 'r_diff')
                if u in edges:
                    if p in perms or q in perms:
                        if p.startswith('r_diff'):
                            edges[u].add(-perms[q])
                        elif p.startswith('r_same'):
                            edges[u].add(perms[p])
                    else:
                        if p.startswith('r_diff'):
                            edges[u].add(-counter)
                            perms[q] = counter
                            counter += 1
                        elif p.startswith('r_same'):
                            edges[u].add(counter)
                            perms[p] = counter
                            counter += 1
                    edges2[u].add(p)
                else:
                    if p in perms or q in perms:
                        if p.startswith('r_diff'):
                            edges[u] ={-perms[q]}
                        elif p.startswith('r_same'):
                            edges[u] = {perms[p]}
                    else:
                        if p.startswith('r_diff'):
                            edges[u] = {-counter}
                            perms[q] = counter
                            counter += 1
                        elif p.startswith('r_same'):
                            edges[u] = {counter}
                            perms[p] = counter
                            counter += 1
                    edges2[u] = {p}
                new_roles_assigned_mapped[r] = {f for f in roles_assigned_mapped[r] if f[0].startswith('e_') and f[
                    1].startswith('r_')}

        inv_perms = {v: k for k, v in perms.items()}

        for e in edges:
            role_str = 'r_{role_num}'.format(role_num=role_num)

            # create role
            for p in edges[e]:
                if p in edges[e] and -p in edges[e]:
                    p = abs(p)
                    if role_str in ret:
                        ret[role_str].add(inv_perms[p])
                    else:
                        ret[role_str] = {inv_perms[p]}

    return





def main():
    print('Start time:', datetime.now())
    sys.stdout.flush()

    if len(sys.argv) != 2:
        print('Usage: ', end='')
        print(sys.argv[0], end=' ')
        print('<input-file>')
        return

    upfilepath = sys.argv[1]
    up = readup(upfilepath)
    if not up:
        return

    timeone = time.time()
    roles_assigned = min_edge_to_min_role(up, upfilepath)
    timetwo = time.time()

    post_process(roles_assigned)

    print('done! Time taken:', timetwo - timeone)
    sys.stdout.flush()


if __name__ == '__main__':
    main()
