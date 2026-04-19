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

import maxsetsbp

from rh_utils import read_rbac_file
from rh_metrics import get_metrics
from removedominators import readem




def main(args: argparse.Namespace):
    upfilename = args.input_up_file
    up, usermap, permmap = readup_and_usermap_permmap(upfilename)

    rbac_cut_files = args.input_cut_files
    print("RBAC cut files: ", rbac_cut_files)
    print("UP files: ", upfilename)
    full_rbac = dict()
    role_offset = 0
    for cut_file in rbac_cut_files:

        num_roles, roles = maxsetsbp.run(cut_file)
        cutup, cut_usermap, cut_permmap = readup_and_usermap_permmap(cut_file)
        inv_cut_permmap = {v: k for k, v in cut_permmap.items()}
        inv_cut_usermap = {v: k for k, v in cut_usermap.items()}

        roles_mapped = dict()
        for idx in range(len(roles)):
            new_idx = role_offset + idx
            if new_idx not in roles_mapped:
                roles_mapped[new_idx] = set()
            for e in roles[idx]:
                roles_mapped[new_idx].add((inv_cut_usermap[e[0]], inv_cut_permmap[e[1]]))

        role_offset += len(roles)

        merged_roles = full_rbac | roles_mapped
        full_rbac = merged_roles


    print('Merged RBACs')
    full_rbac_mapped = dict()
    for r in full_rbac:
        users_r_mapped = {usermap[e[0]] for e in full_rbac[r]}
        perms_r_mapped = {permmap[e[1]] for e in full_rbac[r]}
        if r not in full_rbac_mapped:
            full_rbac_mapped[r] = list()
        for u in users_r_mapped:
            for p in perms_r_mapped:
                full_rbac_mapped[r].append((u, p))

    u_name = upfilename.split('/')[-1]
    rbac_fname = f'MERGED_RBAC_{u_name}'
    with open(rbac_fname, 'w') as f:
        json.dump(full_rbac_mapped, f, indent=4, sort_keys=True)

    MERGED_RBAC_read = read_rbac_file(rbac_fname)
    RH_final = RBAC_to_RH.rbac_to_rh_no_new_roles(upfilename, MERGED_RBAC_read)
    RH_to_write = dict()
    for r in RH_final:
        RH_to_write[r] = list(RH_final[r])
    u_name = upfilename.split('/')[-1]
    rh_fname = f'MERGED_RH_{u_name}'
    with open(rh_fname, 'w') as f:
        json.dump(RH_to_write, f, indent=4, sort_keys=True)
    metrics = get_metrics(RH_final, use_sampling=True)
    return RH_final, metrics


# ---------------------- Demo ----------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Read cut up files")
    parser.add_argument("input_cut_files", nargs="+", help="Input RBAC cut files")
    parser.add_argument("input_up_file", type=str, help="Input UP file")
    args = parser.parse_args()
    main(args)
