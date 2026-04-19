# rolehierarchy

Convert an access matrix to a role-based policy in a manner that minimizes the number of roles.

Puneet Gill
p24gill@uwaterloo.ca


What's in this repo:
 paper.pdf: PDF of the paper
 1) README.md: this readme file

 2) removedominatorsbp.py:  
 3) findcliquesbp.py: networkx's find_cliques() adapted to maximal bicliques in a bipartite graph

 4) maxsetsbp.py: the algorithm from Section 4 that enumerate all maximal bicliques, reduces to ILP and invokes gurobi to solve. It invokes removedominators() first.
 5) RoleHierarchy/RBAC_to_RH.py: This is the MinRolesRH algorithm from the paper. MinRolesRH, which begins with an RBAC policy that minimizes the number of roles and restructures it into a multi-layered role hierarchy.
 6) RoleHierarchy/RBAC_RH_IP_V2.py: This is the NewRolesRH algorithm from the paper. In this algorithm, we begin with a candidate RBAC policy and introduce new roles that can be added to higher layers of the hierarchy. The goal is to construct a hierarchy with the maximum possible number of layers. Introducing new roles ensures that each role remains distinct.
 7) RoleHierarchy/RHBuilder_Vaidya.py.py: This is the RHMiner algorithm used as the baseline.
