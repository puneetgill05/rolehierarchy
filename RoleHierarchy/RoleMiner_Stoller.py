#!/usr/bin/env python3

from __future__ import annotations

import json
import signal
import sys
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from pprint import pprint
from typing import Dict, Set, Tuple, Iterable, List, Optional, Callable
from collections import defaultdict, deque
import math
import argparse, csv, os

from rh_metrics import get_metrics

prefix_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(f'{prefix_dir}/..')
sys.path.append(f'{prefix_dir}/../..')
# print(sys.path)

from readup import readup, readup_and_usermap_permmap
import maxsetsbp

User = str
Perm = str
RoleId = int


@dataclass
class RBAC:
    U: Set[User]
    P: Set[Perm]
    UA: Set[Tuple[User, RoleId]] = field(default_factory=set)
    PA: Set[Tuple[RoleId, Perm]] = field(default_factory=set)
    RH: Set[Tuple[RoleId, RoleId]] = field(default_factory=set)
    DA: Set[Tuple[User, Perm]] = field(default_factory=set)
    R: Set[RoleId] = field(default_factory=set)

    def copy(self) -> "RBAC":
        return RBAC(
            U=set(self.U), P=set(self.P),
            UA=set(self.UA), PA=set(self.PA), RH=set(self.RH), DA=set(self.DA), R=set(self.R)
        )

    def assignedP(self, r: RoleId) -> Set[Perm]:
        return {p for rr, p in self.PA if rr == r}

    def assignedU(self, r: RoleId) -> Set[User]:
        return {u for u, rr in self.UA if rr == r}

    def _descendants(self, r: RoleId) -> Set[RoleId]:
        out = defaultdict(set)
        for a, b in self.RH:
            out[a].add(b)
        seen, q = set(), [r]
        while q:
            x = q.pop()
            for y in out.get(x, ()):
                if y not in seen:
                    seen.add(y)
                    q.append(y)
        return seen

    def _ancestors(self, r: RoleId) -> Set[RoleId]:
        inp = defaultdict(set)
        for a, b in self.RH:
            inp[b].add(a)
        seen, q = set(), [r]
        while q:
            x = q.pop()
            for y in inp.get(x, ()):
                if y not in seen:
                    seen.add(y)
                    q.append(y)
        return seen

    def authP(self, r: RoleId) -> Set[Perm]:
        perms = set(self.assignedP(r))
        for d in self._descendants(r):
            perms |= self.assignedP(d)
        return perms

    def authU(self, r: RoleId) -> Set[User]:
        users = set(self.assignedU(r))
        for a in self._ancestors(r):
            users |= self.assignedU(a)
        return users

    def authUP_pairs(self, r: RoleId, UP: Set[Tuple[User, Perm]]) -> Set[Tuple[User, Perm]]:
        A = self.authU(r)
        P = self.authP(r)
        return {(u, p) for (u, p) in UP if u in A and p in P}


class RoleMiner:
    def __init__(self, U: Iterable[User], P: Iterable[Perm], UP: Iterable[Tuple[User, Perm]], upfilename: str):
        self.U: Set[User] = set(U)
        self.P: Set[Perm] = set(P)
        self.UP: Set[Tuple[User, Perm]] = set(UP)
        self.UP_FILENAME = upfilename
        self._UPu: Dict[User, Set[Perm]] = defaultdict(set)
        for u, p in self.UP:
            self._UPu[u].add(p)

        self.attributes: Optional[Dict[User, Dict[str, int]]] = None

    def _compute_initial_roles(self) -> List[frozenset]:
        permsets = set()
        for u in self.U:
            ps = frozenset(self._UPu.get(u, set()))
            if ps:
                permsets.add(ps)
        return sorted(list(permsets), key=lambda s: (len(s), tuple(sorted(s))))

    def _compute_maxsetsbp(self) -> List:
        num_roles, roles = maxsetsbp.run(self.UP_FILENAME)
        up, usermap, permmap = readup_and_usermap_permmap(self.UP_FILENAME)
        inv_permmap = {v: k for k, v in permmap.items()}
        inv_usermap = {v: k for k, v in usermap.items()}
        permsets = list()
        for role_edges in roles:
            perms_r = set()
            for e in role_edges:
                p = inv_permmap[e[1]]
                perms_r.add(p)
            permsets.append(perms_r)
        return [frozenset(s) for s in permsets]

    def _compute_all_intersections(self, init_sets: List[frozenset]) -> List[frozenset]:
        Rsets: Set[frozenset] = set()
        init = list(init_sets)
        for i, A in enumerate(init):
            for B in init[i + 1:]:
                I = A & B
                if I:
                    Rsets.add(I)
            changed = True
            while changed:
                changed = False
                for C in list(Rsets):
                    I = A & C
                    if I and I not in Rsets:
                        Rsets.add(I)
                        changed = True
        return sorted(list(Rsets | set(init)), key=lambda s: (len(s), tuple(sorted(s))))

    def build_candidate_policy(self) -> RBAC:
        # init_sets = self._compute_initial_roles()
        init_sets = self._compute_maxsetsbp()
        all_sets = self._compute_all_intersections(init_sets)

        rbac = RBAC(U=set(self.U), P=set(self.P))
        permset_to_role: Dict[frozenset, RoleId] = {}
        next_id = 0
        for ps in all_sets:
            r = next_id
            next_id += 1
            rbac.R.add(r)
            permset_to_role[ps] = r
            for p in ps:
                rbac.PA.add((r, p))

        for u in self.U:
            P_u = self._UPu.get(u, set())
            for r in rbac.R:
                if rbac.assignedP(r).issubset(P_u):
                    rbac.UA.add((u, r))

        self._build_full_inheritance_and_prune(rbac)
        return rbac

    def _build_full_inheritance_and_prune(self, rbac: RBAC) -> None:
        roles = list(rbac.R)
        for r in roles:
            for rprime in roles:
                if rprime == r:
                    continue
                if rbac.authP(rprime).issubset(rbac.authP(r)):
                    parents = {x for (x, y) in rbac.RH if y == r}
                    if any(rbac.authP(rprime).issubset(rbac.authP(pp)) for pp in parents):
                        continue
                    rbac.RH.add((r, rprime))
                    inheritedP = rbac.authP(rprime)
                    to_remove = {(rr, p) for (rr, p) in rbac.PA if rr == r and p in inheritedP}
                    rbac.PA.difference_update(to_remove)
                    users_of_r = rbac.assignedU(r)
                    to_remove_ua = {(u, rr) for (u, rr) in rbac.UA if rr == rprime and u in users_of_r}
                    rbac.UA.difference_update(to_remove_ua)
                    old_parents = list(parents)
                    for pp in old_parents:
                        if rbac.authP(pp).issubset(rbac.authP(rprime)):
                            rbac.RH.discard((pp, r))

    @staticmethod
    def WSC(rbac: RBAC, wR=1, wUA=1, wPA=1, wRH=1, wDA=0, DA: Optional[Set[Tuple[User, Perm]]] = None) -> int:
        DA = rbac.DA if DA is None else DA
        return wR * len(rbac.R) + wUA * len(rbac.UA) + wPA * len(rbac.PA) + wRH * len(rbac.RH) + wDA * len(
            DA) + wUA * len(rbac.UA) + wPA * len(rbac.PA) + wRH * len(rbac.RH) + wDA * len(DA)

    @staticmethod
    def lexicographic(a: Tuple[int, int], b: Tuple[int, int]) -> bool:
        return a < b

    def _clsSz(self, rbac: RBAC, r: RoleId) -> float:
        members = rbac.assignedU(r)
        if not members:
            return 0.0
        covered = 0
        total = 0
        perms_r = rbac.assignedP(r)
        for u in members:
            Pu = self._UPu.get(u, set())
            total += len(Pu)
            covered += len(Pu & perms_r)
        return covered / total if total else 0.0

    def _attrFit(self, rbac: RBAC, r: RoleId, attrs: Optional[Dict[User, Dict[str, int]]]) -> float:
        if not attrs:
            return 0.0
        members = rbac.assignedU(r)
        if not members:
            return 0.0
        mismatch = self.INT(_rbac_single_role_view(rbac, r), attrs)
        return 1.0 - (mismatch / max(1, len(members)))

    def _redundancy(self, rbac: RBAC, r: RoleId) -> Tuple[int, int]:
        authUP = rbac.authUP_pairs(r, self.UP)
        if not authUP:
            return (0, 0)
        counts = []
        for (u, p) in authUP:
            c = 0
            for r2 in rbac.R:
                if r2 == r:
                    continue
                if (u, p) in rbac.authUP_pairs(r2, self.UP):
                    c += 1
            counts.append(c)
        m = min(counts) if counts else 0
        return (-m, -len(authUP))

    def _role_quality(self, rbac: RBAC, r: RoleId, kind: str, attrs: Optional[Dict[User, Dict[str, int]]] = None):
        if kind == "redundancy":
            return self._redundancy(rbac, r)
        elif kind == "clssz":
            return self._clsSz(rbac, r)
        elif kind == "max_attr_clssz":
            return max(self._attrFit(rbac, r, attrs), self._clsSz(rbac, r))
        else:
            raise ValueError(f"Unknown role-quality metric: {kind}")

    def _removable(self, rbac: RBAC, r: RoleId) -> bool:
        authUP = rbac.authUP_pairs(r, self.UP)
        for (u, p) in authUP:
            ok = False
            for r2 in rbac.R:
                if r2 == r:
                    continue
                if (u, p) in rbac.authUP_pairs(r2, self.UP):
                    ok = True
                    break
            if not ok:
                return False
        return True

    def _remove_role(self, rbac: RBAC, r: RoleId) -> RBAC:
        pi = rbac.copy()
        if r not in pi.R:
            return pi
        pi.R.remove(r)
        parents = [(a, b) for (a, b) in list(pi.RH) if b == r]
        for (r1, _) in parents:
            pi.RH.discard((r1, r))
            children = [(a, b) for (a, b) in list(pi.RH) if a == r]
            for (_, r2) in children:
                if not reachable(pi.RH, r1, r2):
                    pi.RH.add((r1, r2))
            authP_r1 = pi.authP(r1)
            for (rr, p) in list(pi.PA):
                if rr == r and p not in authP_r1:
                    pi.PA.add((r1, p))
        children = [(a, b) for (a, b) in list(pi.RH) if a == r]
        for (_, r2) in children:
            pi.RH.discard((r, r2))
            authU_r2 = pi.authU(r2)
            for (u, rr) in list(pi.UA):
                if rr == r and u not in authU_r2:
                    pi.UA.add((u, r2))
        pi.PA = {(rr, p) for (rr, p) in pi.PA if rr != r}
        pi.UA = {(u, rr) for (u, rr) in pi.UA if rr != r}
        return pi

    def replace_roles_with_DA(self,
                              rbac: RBAC,
                              policy_quality: str = "WSC-INT",
                              q_delta: float = 1.0,
                              wR=1, wUA=1, wPA=1, wRH=1, wDA=1,
                              user_attrs: Optional[Dict[User, Dict[str, int]]] = None) -> RBAC:

        def Qpol(pi: RBAC) -> Tuple[int, int]:
            wsc = self.WSC(pi, wR=wR, wUA=wUA, wPA=wPA, wRH=wRH, wDA=wDA)
            intl = self.INT(pi, user_attrs)
            return (wsc, intl) if policy_quality == "WSC-INT" else (intl, wsc)

        pi = rbac.copy()
        q = Qpol(pi)
        changed = True
        while changed:
            changed = False

            def benefit_est(r: RoleId) -> int:
                return len(pi.authUP_pairs(r, self.UP))

            roles = sorted(list(pi.R), key=benefit_est, reverse=True)
            for r in roles:
                pi2 = pi.copy()
                da_add = pi2.authUP_pairs(r, self.UP)
                if not da_add:
                    continue
                pi2.DA |= da_add
                pi2 = self._remove_role(pi2, r)
                covered = set(pi2.DA)
                for rr in pi2.R:
                    covered |= pi2.authUP_pairs(rr, self.UP)
                if any(pair not in covered for pair in self.UP):
                    continue
                q2 = Qpol(pi2)
                if lex_lt_with_tolerance(q2, q, q_delta):
                    pi = pi2
                    q = q2
                    changed = True
        return pi

    def eliminate(self,
                  rbac: RBAC,
                  policy_quality: str = "WSC-INT",
                  role_quality: str = "redundancy",
                  q_delta: float = 1.001,
                  wR=1, wUA=1, wPA=1, wRH=1,
                  user_attrs: Optional[Dict[User, Dict[str, int]]] = None,
                  allow_restore: bool = True, timeout=10600) -> RBAC:

        def Qpol(pi: RBAC) -> Tuple[int, int]:
            wsc = self.WSC(pi, wR=wR, wUA=wUA, wPA=wPA, wRH=wRH)
            intl = self.INT(pi, user_attrs)
            return (wsc, intl) if policy_quality == "WSC-INT" else (intl, wsc)

        pi = rbac.copy()
        q = Qpol(pi)
        removed_stack: List[RoleId] = []

        signal.signal(signal.SIGALRM, _timeout_handler_while)
        signal.alarm(timeout)
        try:
            changed = True
            while changed:
                changed = False
                work = [r for r in list(pi.R) if self._removable(pi, r)]

                def rq_key(r: RoleId):
                    val = self._role_quality(pi, r, role_quality, user_attrs)
                    if isinstance(val, tuple):
                        return val
                    return (val,)

                work.sort(key=rq_key)

                for r in work:
                    if not self._removable(pi, r):
                        continue
                    pi2 = self._remove_role(pi, r)
                    q2 = Qpol(pi2)
                    if lex_lt_with_tolerance(q2, q, q_delta):
                        pi = pi2
                        q = q2
                        removed_stack.append(r)
                        changed = True
        except Exception as e:
            print('while time out!', end=' ')

        if allow_restore and removed_stack:
            for r in removed_stack:
                pi2 = self.restore_role(pi, r, rbac)
                if pi2 is None:
                    continue
                if lex_lt_with_tolerance(Qpol(pi2), q, 1.0):
                    pi = pi2
                    q = Qpol(pi)
        return pi

    def restore_role(self, pi: RBAC, r: RoleId, reference: RBAC) -> Optional[RBAC]:
        if r not in reference.R:
            return None
        new = pi.copy()
        if r in new.R:
            return None
        new.R.add(r)
        for (rr, p) in reference.PA:
            if rr == r:
                new.PA.add((r, p))
        for (u, rr) in reference.UA:
            if rr == r:
                new.UA.add((u, r))
        for r2 in list(new.R):
            if r2 == r:
                continue
            if reference.authP(r).issubset(reference.authP(r2)):
                parents = {a for (a, b) in new.RH if b == r}
                if not any(reference.authP(r).issubset(reference.authP(pp)) for pp in parents):
                    new.RH.add((r2, r))
                    # prune redundant parents
                    for pp in list(parents):
                        if reference.authP(pp).issubset(reference.authP(r2)):
                            new.RH.discard((pp, r))
            if reference.authP(r2).issubset(reference.authP(r)):
                parents = {a for (a, b) in new.RH if b == r2}
                if not any(reference.authP(r2).issubset(reference.authP(pp)) for pp in parents):
                    new.RH.add((r, r2))
                    for pp in list(parents):
                        if reference.authP(pp).issubset(reference.authP(r)):
                            new.RH.discard((pp, r2))
        return new



def reachable(RH: Set[Tuple[RoleId, RoleId]], src: RoleId, dst: RoleId) -> bool:
    out = defaultdict(set)
    for a, b in RH:
        out[a].add(b)
    q = deque([src])
    seen = set([src])
    while q:
        x = q.popleft()
        if x == dst:
            return True
        for y in out.get(x, ()):
            if y not in seen:
                seen.add(y)
                q.append(y)
    return False


def get_RH_layer_info(RBAC_final: RBAC) -> dict:
    RH_dict = dict()
    for r1, r2 in RBAC_final.RH:
        if r1 not in RH_dict or r2 not in RH_dict:
            RH_dict[r1] = set()
            RH_dict[r2] = set()
    for r1, r2 in RBAC_final.RH:
        RH_dict[r1].add(r2)

    for (u, r) in RBAC_final.UA:
        if r not in RH_dict:
            RH_dict[r] = set()
        RH_dict[r].add(u)

    for (r, p) in RBAC_final.PA:
        if r not in RH_dict:
            RH_dict[r] = set()
        RH_dict[r].add(p)

    stack = []
    visited = set()
    RH_layer_info = dict()
    for r1 in RH_dict:
        stack.append(r1)
        layer = 0
        RH_layer_info[r1] = layer
        while len(stack) > 0:
            u = stack.pop()
            layer += 1
            if u in visited:
                continue
            visited.add(u)
            for r2 in RH_dict[u]:
                if isinstance(r2, int):
                    if r2 not in visited:
                        stack.append(r2)
                        break
        if layer > RH_layer_info[r1]:
            RH_layer_info[r1] = layer
    return RH_dict, RH_layer_info


def _rbac_single_role_view(rbac: RBAC, r: RoleId) -> RBAC:
    tiny = RBAC(U=set(rbac.U), P=set(rbac.P))
    tiny.R.add(r)
    for (u, rr) in rbac.UA:
        if rr == r:
            tiny.UA.add((u, r))
    for (rr, p) in rbac.PA:
        if rr == r:
            tiny.PA.add((r, p))
    return tiny


def lex_lt_with_tolerance(a: Tuple[int, int], b: Tuple[int, int], delta: float) -> bool:
    a0, a1 = a
    b0, b1 = b
    if a0 < math.floor(b0 * delta + 1e-9):
        return True
    if a0 == b0 and a1 < math.floor(b1 * delta + 1e-9):
        return True
    return False


def main(args):
    def load_edges_csv(path: str):
        U, P, UP = set(), set(), set()
        with open(path, newline="") as f:
            rdr = csv.reader(f)
            header = next(rdr, None)
            if header and len(header) > 2:
                perms = header[1:]
                for row in rdr:
                    u = row[0]
                    U.add(u)
                    for j, val in enumerate(row[1:]):
                        if val.strip() in ("1", "true", "True"):
                            p = perms[j]
                            P.add(p)
                            UP.add((u, p))
            else:
                if header and (header[0].lower() in ("user", "u") and header[1].lower() in ("perm", "permission", "p")):
                    pass
                else:
                    if header and len(header) >= 2:
                        u, p = header[0], header[1]
                        U.add(u)
                        P.add(p)
                        UP.add((u, p))
                for row in rdr:
                    if len(row) < 2:
                        continue
                    u, p = row[0], row[1]
                    U.add(u)
                    P.add(p)
                    UP.add((u, p))
        return U, P, UP

    def load_user_attrs(path: Optional[str]):
        if not path or not os.path.exists(path):
            return None
        attrs: Dict[User, Dict[str, int]] = defaultdict(dict)
        with open(path, newline="") as f:
            rdr = csv.DictReader(f)
            for row in rdr:
                u = row.get("user") or row.get("User") or row.get("u")
                if not u:
                    u = next(iter(row.values()))
                for k, v in row.items():
                    if k.lower() in ("user", "u"):
                        continue
                    try:
                        attrs[u][k] = int(v)
                    except Exception:
                        continue
        return attrs



    signal.signal(signal.SIGALRM, _timeout_handler)
    signal.alarm(args.timeout)
    try:
        if args.input_file and os.path.exists(args.input_file):
            # U, P, UP = load_edges_csv(args.input)
            upfilename = args.input_file
            up, usermap, permmap = readup_and_usermap_permmap(upfilename)
            inv_permmap = {v: k for k, v in permmap.items()}
            inv_usermap = {v: k for k, v in usermap.items()}
            # else:
            U = (usermap.keys())
            P = set(permmap.keys())
            UP_mapped = {
                (inv_usermap[u], inv_permmap[p]) for u in up for p in up[u]
            }
        else:
            upfilename = None
            U, P = set(), set()
            UP_mapped = dict()
        miner = RoleMiner(U, P, UP_mapped, upfilename)
        attrs = load_user_attrs(args.attrs)
        miner.attributes = attrs

        start_time = time.time()
        print('Start time:', start_time)
        print('Start date time:', datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S'))
        candidate = miner.build_candidate_policy()
        print("Candidate sizes → R/UA/PA/RH/DA:", len(candidate.R), len(candidate.UA), len(candidate.PA),
              len(candidate.RH),
              len(candidate.DA))

        # pprint(candidate)
        print('Time now after candidate policy: ', time.time())
        print('Time taken so far after candidate policy: ', time.time() - start_time)
        RH, RH_layer_info = get_RH_layer_info(candidate)

        metrics = get_metrics(RH)

        refined = miner.eliminate(candidate,
                                  policy_quality=args.polq,
                                  role_quality=args.roleq,
                                  q_delta=args.delta,
                                  wR=args.wR, wUA=args.wUA, wPA=args.wPA, wRH=args.wRH,
                                  user_attrs=attrs,
                                  allow_restore=True, timeout=args.timeout)
        # refined = candidate

        print("After elimination -> R/UA/PA/RH/DA:", len(refined.R), len(refined.UA), len(refined.PA), len(refined.RH),
              len(refined.DA))

        final = refined
        # pprint(final)
        end_time = time.time()
        print(f'Time taken to compute RH: {end_time - start_time} seconds')
        covered = set(final.DA)
        for rr in final.R:
            covered |= final.authUP_pairs(rr, UP_mapped)
        print("Covers input UP:", all(pair in covered for pair in UP_mapped))
        RH, RH_layer_info = get_RH_layer_info(final)

        RH_to_write = dict()
        for r in RH:
            RH_to_write[r] = list(RH[r])
        u_name = upfilename.split('/')[-1]
        rh_fname = f'STOLLER_RH_{u_name}'
        with open(rh_fname, 'w') as f:
            json.dump(RH_to_write, f, indent=4, sort_keys=True)
        metrics = get_metrics(RH)
        return RH, metrics

    except Exception as e:
        print('time out!', end=' ')
        print('Exception', e)


def _timeout_handler(signum, frame):
    raise TimeoutError("main timed out")


def _timeout_handler_while(signum, frame):
    raise TimeoutError("while timed out")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Role mining + role hierarchy (Xu–Stoller 2012)")
    ap.add_argument("input_file", help="UP filepath")
    ap.add_argument("--attrs", required=False, help="CSV: user, a1, a2, ... (ints)")
    ap.add_argument("--wR", type=int, default=1)
    ap.add_argument("--wUA", type=int, default=1)
    ap.add_argument("--wPA", type=int, default=1)
    ap.add_argument("--wRH", type=int, default=1)
    ap.add_argument("--wDA", type=int, default=0)
    ap.add_argument("--timeout", type=int, default=43200)
    ap.add_argument("--delta", type=float, default=1.001, help="quality tolerance δ for elimination")
    ap.add_argument("--polq", choices=["WSC-INT", "INT-WSC"], default="WSC-INT")
    ap.add_argument("--roleq", choices=["redundancy", "clssz", "max_attr_clssz"], default="redundancy")
    args = ap.parse_args()

    result = main(args)
