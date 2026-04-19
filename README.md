## Overview

This project provides implementations of algorithms for constructing and evaluating role hierarchies from mined RBAC policies.


Convert an access matrix to a role-based policy in a manner that minimizes the number of roles.

Puneet Gill
p24gill@uwaterloo.ca


What's in this repo:
 paper.pdf: PDF of the paper
 1) README.md: this readme file
 2) removedominatorsbp.py: remove dominator edges from the input user-permission bipartite graph.
 3) findcliquesbp.py: networkx's find_cliques() adapted to maximal bicliques in a bipartite graph
 4) maxsetsbp.py: the algorithm from Section 4 that enumerate all maximal bicliques, reduces to ILP and invokes gurobi to solve. It invokes removedominators() first.
 5) RoleHierarchy/RBAC_to_RH.py: This is the MinRolesRH algorithm from the paper. MinRolesRH, which begins with an RBAC policy that minimizes the number of roles and restructures it into a multi-layered role hierarchy.
 6) RoleHierarchy/RBAC_RH_IP_V2.py: This is the NewRolesRH algorithm from the paper. In this algorithm, we begin with a candidate RBAC policy and introduce new roles that can be added to higher layers of the hierarchy. The goal is to construct a hierarchy with the maximum possible number of layers. Introducing new roles ensures that each role remains distinct.
 7) RoleHierarchy/RHBuilder_Vaidya.py.py: This is the RHMiner algorithm used as the baseline.
 
---

## Repository

Clone:

```bash
git clone git@github.com:puneetgill05/rolehierarchy.git
cd rolehierarchy
```

---

## Environment Setup

### Local Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Gurobi Requirement

A Gurobi license is required: https://www.gurobi.com/

---
## Run Algorithms

### MinRolesRH

```bash
cd RoleHierarchy
python3 RBAC_to_RH.py ../inputsup/hc
```

```
{'avg_num_layers': 1.5714285714285714,
 'max_layer': 3,
 'num_edges': 198,
 'num_roles': 14,
 'random_walk': {'max_mean_steps': 1404.4,
                 'mean_steps': 770.6476190476192,
                 'median_steps': 729.547619047619,
                 'unsuccessful_walks': 0},
 'wsc': {'# role-perm edges': 122,
         '# role-role edges': 11,
         '# user-role edges': 65,
         'wsc': 212}}
```
### NewRolesRH

```bash
cd RoleHierarchy
python3 RBAC_RH_IP_V2.py ../inputsup/hc
```
```
{'avg_num_layers': 1.9166666666666667,
 'max_layer': 4,
 'num_edges': 244,
 'num_roles': 24,
 'random_walk': {'max_mean_steps': 1739.8,
                 'mean_steps': 807.4904761904761,
                 'median_steps': 739.5238095238095,
                 'unsuccessful_walks': 0},
 'wsc': {'# role-perm edges': 158,
         '# role-role edges': 26,
         '# user-role edges': 60,
         'wsc': 268}}
```
