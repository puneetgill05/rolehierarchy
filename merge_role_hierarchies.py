#!/usr/bin/env python3

import argparse
import json
import os
from pathlib import Path
from pprint import pprint
from typing import Dict, Iterable, Any, Set, List, Tuple, Optional
from collections import defaultdict

import RBAC_to_RH
from RBAC_to_RH import reconstruct_roles_from_RH
from readup import readup_and_usermap_permmap

from minedgerolemining.RoleHierarchy.rh_metrics import get_metrics



def read_rh_file(rh_file_path: Path) -> dict:
    RH = json.load(open(rh_file_path, 'r'))
    RH_new = dict()
    for r in RH.keys():
        if isinstance(r, str) and r.isdigit():
            RH_new[int(r)] = set(RH[r])

    for r in RH_new.keys():
        for v in RH_new[r]:
            if isinstance(v, str) and v.isdigit():
                RH_new[r].remove(v)
                RH_new[r].add(int(v))
    return RH_new


def main(args: argparse.Namespace):
    upfilename = args.input_up_file
    up, usermap, permmap = readup_and_usermap_permmap(upfilename)

    rh_dir_path = Path(args.input_rh_dir_path)
    rh_files = os.listdir(rh_dir_path)
    full_rbac = dict()
    for rh_file in rh_files:
        rh_file_path = rh_dir_path.joinpath(rh_file)
        RH = read_rh_file(rh_file_path)
        rbac = reconstruct_roles_from_RH(RH)
        if len(full_rbac) == 0:
            full_rbac = rbac
        else:
            max_r = max(full_rbac.keys()) + 1
            for r in rbac:
                full_rbac[max_r + r] = rbac[r]
                for v in rbac[r]:
                    if isinstance(v, int):
                        full_rbac[max_r + r].remove(v)
                        full_rbac[max_r + r].add(max_r + v)
    # print('Full RBAC:')
    # pprint(full_rbac)

    full_rbac_mapped = dict()
    for r in full_rbac:
        users_r_mapped = {usermap[e] for e in full_rbac[r] if isinstance(e, str) and (e.startswith('u') or
                                                                                      e.startswith('U'))}
        perms_r_mapped = {permmap[e] for e in full_rbac[r] if isinstance(e, str) and (e.startswith('p') or
                                                                                      e.startswith('P'))}
        if r not in full_rbac_mapped:
            full_rbac_mapped[r] = set()
        for u in users_r_mapped:
            for p in perms_r_mapped:
                full_rbac_mapped[r].add((u, p))

    RH_final = RBAC_to_RH.rbac_to_rh_no_new_roles(upfilename, full_rbac_mapped)
    RH_to_write = dict()
    for r in RH_final:
        RH_to_write[r] = list(RH_final[r])
    u_name = upfilename.split('/')[-1]
    rh_fname = f'MERGED_RH_{u_name}'
    with open(rh_dir_path.joinpath(rh_fname), 'w') as f:
        json.dump(RH_to_write, f, indent=4, sort_keys=True)
    metrics = get_metrics(RH_final, use_sampling=True)
    return RH_final, metrics


# ---------------------- Demo ----------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Read RH files")
    parser.add_argument("input_rh_dir_path", type=str, help="Input RH directory path")
    parser.add_argument("input_up_file", type=str, help="Input UP file")
    args = parser.parse_args()
    main(args)
