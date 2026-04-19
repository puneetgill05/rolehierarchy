### ```BicliqueCoverToILP.py```
Functions of interest in the file

1. ```bicliqueCoverToILP_opt(dict, ObjType)```: This function reduces the problem of maximizing the biclique cover 
   in a bipartite graph.

   The question it tries to answer is: **What is the maximum biclique in the input bipartite graph G?**

   Here, *maximum* varies depends on whether we wish to a biclique with the maximum number of vertices or we wish 
   to maximize the number of edges.

   **Input**: This functions takes two inputs: The first is a ``dict`` which is the representation of the input 
   bipartite 
   graph. In this case, ``up``. The second input is an enum ``ObjType`` it can be either ``ObjType.VERTICES`` or 
   ``ObjType.EDGES``, representing the objective type for the problem. When we want to maximize the number 
   of vertices in the biclique, ``ObjType.VERTICES`` is 
   passed and  ``ObjType.EDGES`` is passed when we want to maximize the number of edges in the biclique.

   **Output**: This function returns the objective value from Gurobi (``int``) and roles created based on Gurobi's 
   ``.sol`` file. The roles returned is a ``dict`` where the key is the role number and value is a set of users and 
   permissions assigned to this role. 
   
   *Note*: To distinguish between users and permissions, we prepend a user with ``u_`` 
   and a permission with ``p_``.

   We later use the roles returned by this function to create roles such that every role is a ``set`` of edges from the 
input graph.

   **Usage**: We use this function in the greedy approach.
   
   **Example**: ``sol, roles_created_mapped = bicliqueCoverToILP_opt(up, objType=ObjType.EDGES)``
   
   **Configuration**: Takes in a user-permission file. Eg: ``{path-to-project}/inputsup/vaidya.txt`` 

### ```createILP.py```

Functions of interest in this file

1  ``reduce_to_ilp(dict, set, set, int, gp.Model) -> gp.Model``: This function reduces the ``Edge-RMP`` to ``ILP``. 
This is our *exact* algorithm.
   
**Input**: The first is the input bipartite graph ``up``, the second input is the set of users, followed by the set 
of permissions. The fourth input is an upper bound on the number of roles, we use 
2 max(|users|, |perms|). The last input is the gurobi model.


**Output**: Gurobi model, the model returned has the objectives and constraints but is not yet optimized. We use 
this model to optimize and write the ``.lp`` and ``.sol`` files.


**Usage**: We use this function in the exact approach.
   
**Example**: ``m = reduce_to_ilp(up, users, perms, nroles, m)``

**Configuration**: Takes in a user-permission file. Eg: ``{path-to-project}/inputsup/vaidya.txt`` 




