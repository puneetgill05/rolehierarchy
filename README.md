# minrolemining

Convert an access matrix to a role-based policy in a manner that minimizes the number of roles.

Mahesh Tripunitara
tripunit@uwaterloo.ca

Released under the MIT license (see LICENSE file). Companion paper: http://arxiv.org/abs/2407.15278

What's in this repo:

 1) README.md: this readme file

 2) irreducible.txt: the access matrix from Figure 1 of the paper

 3) PLAIN_small_08.rmp: one of the new benchmark inputs from https://github.com/RMPlib/RMPlib/wiki that the paper addresses.

 4) readup.py: basic routines for reading the user-permission input, converting it to permission-users, etc.

        $ ./readup.py irreducible.txt
        UP map written to irreducible.txt-upmap.txt
        nusers =  5
        nperms =  5
        nedges =  15
        $ ./readup.py PLAIN_small_08.rmp
        UP map written to PLAIN_small_08.rmp-upmap.txt
        nusers =  100
        nperms =  184
        nedges =  4415
        $
 
 5) removedominatorsbp.py: the algorithm from Section 3 of the paper; which is the Algorithm of Ene et al., while remaining in the world of bipartite graphs and bicliques. -em is the "edge mark" file, i.e., edges that get marked by Algorithm 1 in the paper. dm the "inverse" of em. An entry in the -em.txt file that is like "(28, 180):(-1, -1, 1012)", i.e., with -1's as the first two components to the right of the ':', means that the edge (28,180) was marked for removal in Line (6) of Algorithm 1. The last component, 1012, is the sequence in which this edge was marked for removal...that sequence is important to reconstruct the RBAC policy. An entry like "(99, 6):(84, 6, 2466)" means that the edge (99, 6) dominates the edge (84, 6). And again, 2466 is the sequence in which we marked (99, 6) for removal as a dominator, i.e., in Line (4) of Algorithm 1.

        $ ./removedominatorsbp.py irreducible.txt
        Start time: 2024-07-22 18:14:51.378075
        UP map written to irreducible.txt-upmap.txt
        Removing doms + zero-neighbour edges...
        removedominators, fixpoint iteration # 1
        removedominators, fixpoint iteration # 2
        done! Time taken: 0.00015735626220703125
        Original # edges: 15
        # dominators + zero neighbour edges removed: 7
        # remaining edges: 8
        # edges with no neighbours: 0
        Saving em into irreducible.txt-em.txt done!
        End time: 2024-07-22 18:14:51.378659
        $
        $ ./removedominatorsbp.py PLAIN_small_08.rmp
        Start time: 2024-07-22 18:14:53.541201
        UP map written to PLAIN_small_08.rmp-upmap.txt
        Removing doms + zero-neighbour edges...
        removedominators, fixpoint iteration # 1
        removedominators, edgenum: 1000
        removedominators, edgenum: 2000
        removedominators, edgenum: 3000
        removedominators, edgenum: 4000
        removedominators, fixpoint iteration # 2
        removedominators, edgenum: 1000
        removedominators, edgenum: 2000
        removedominators, edgenum: 3000
        removedominators, edgenum: 4000
        removedominators, fixpoint iteration # 3
        removedominators, edgenum: 1000
        removedominators, edgenum: 2000
        removedominators, edgenum: 3000
        removedominators, edgenum: 4000
        done! Time taken: 2.4645097255706787
        Original # edges: 4415
        # dominators + zero neighbour edges removed: 2877
        # remaining edges: 1538
        # edges with no neighbours: 3
        Saving em into PLAIN_small_08.rmp-em.txt done!
        End time: 2024-07-22 18:14:56.031911
        $

 6) findcliquesbp.py: networkx's find_cliques() adapted to maximal bicliques in a bipartite graph

 7) maxsetsbp.py: the algorithm from Section 4 that enumerate all maximal bicliques, reduces to ILP (1) and invokes gurobi to solve. It invokes removedominators() first.

        $ ./maxsetsbp.py irreducible.txt 
        Start time: 2024-07-22 18:24:16.322197
        UP map written to irreducible.txt-upmap.txt
        Total # edges: 15
        Removing doms + zero-neighbour edges...
        removedominators, fixpoint iteration # 1
        removedominators, fixpoint iteration # 2
        done! Time taken: 0.00015807151794433594
        Saving em to irreducible.txt-em.txt done!
        Original # edges: 15
        # my dominators + zero neighbour edges removed: 7
        # edges with -1 annotation: 0
        Getting edgeset...done!
        # cliques: 8
        Constructing Maxsets LP...
        Adding constraints...
        Maxsets LP constructed, time: 0.0011391639709472656
        Maxsets LP solved, time: 0.0076673030853271484
        Obj: 4
        Updating em...done!
        Saving em to irreducible.txt-em.txt...done!
        Final solution: 4
        End time: 2024-07-22 18:24:16.655694
        $ 
        $ ./maxsetsbp.py PLAIN_small_08.rmp 
        Start time: 2024-07-22 18:24:24.362078
        UP map written to PLAIN_small_08.rmp-upmap.txt
        Total # edges: 4415
        Removing doms + zero-neighbour edges...
        removedominators, fixpoint iteration # 1
        removedominators, edgenum: 1000
        removedominators, edgenum: 2000
        removedominators, edgenum: 3000
        removedominators, edgenum: 4000
        removedominators, fixpoint iteration # 2
        removedominators, edgenum: 1000
        removedominators, edgenum: 2000
        removedominators, edgenum: 3000
        removedominators, edgenum: 4000
        removedominators, fixpoint iteration # 3
        removedominators, edgenum: 1000
        removedominators, edgenum: 2000
        removedominators, edgenum: 3000
        removedominators, edgenum: 4000
        done! Time taken: 2.5664710998535156
        Saving em to PLAIN_small_08.rmp-em.txt done!
        Original # edges: 4415
        # my dominators + zero neighbour edges removed: 2877
        # edges with -1 annotation: 3
        Getting edgeset...done!
        10000 , Time: 3.0887844562530518
        20000 , Time: 2.648752212524414
        30000 , Time: 2.804671287536621
        40000 , Time: 3.1120951175689697
        50000 , Time: 3.6565845012664795
        60000 , Time: 5.0784571170806885
        70000 , Time: 4.6782073974609375
        80000 , Time: 4.776351690292358
        # cliques: 85901
        Constructing Maxsets LP...
        Added var 10000 / 85901 ...
        Added var 20000 / 85901 ...
        Added var 30000 / 85901 ...
        Added var 40000 / 85901 ...
        Added var 50000 / 85901 ...
        Added var 60000 / 85901 ...
        Added var 70000 / 85901 ...
        Added var 80000 / 85901 ...
        Added term to objective 10000 / 85901 ...
        Added term to objective 20000 / 85901 ...
        Added term to objective 30000 / 85901 ...
        Added term to objective 40000 / 85901 ...
        Added term to objective 50000 / 85901 ...
        Added term to objective 60000 / 85901 ...
        Added term to objective 70000 / 85901 ...
        Added term to objective 80000 / 85901 ...
        Adding constraints...
        Added term to constraint 100000 ...
        Added term to constraint 200000 ...
        Added term to constraint 300000 ...
        Added term to constraint 400000 ...
        Added term to constraint 500000 ...
        Added term to constraint 600000 ...
        Added term to constraint 700000 ...
        Added term to constraint 800000 ...
        Added term to constraint 900000 ...
        Edge # 1000 / 1538 ; time taken: 33.02600884437561 ...
        Added term to constraint 1000000 ...
        Added term to constraint 1100000 ...
        Added term to constraint 1200000 ...
        Added term to constraint 1300000 ...
        Added term to constraint 1400000 ...
        Maxsets LP constructed, time: 51.0537793636322
        Maxsets LP solved, time: 2.394634962081909
        Obj: 47
        Updating em...done!
        Saving em to PLAIN_small_08.rmp-em.txt...done!
        Final solution: 50
        End time: 2024-07-22 18:25:56.638119
        $ 

 8) bicliquesbinsearch.py: the more natural reduction to LP + binary search

        $ ./bicliquesbinsearch.py irreducible.txt
        Start time: 2024-07-22 18:27:05.143094
        UP map written to irreducible.txt-upmap.txt
        Removing dominators + 0-deg...removedominators, fixpoint iteration # 1
        removedominators, fixpoint iteration # 2
        done!
        Original # edges: 15
        # dominators + zero neighbour edges removed: 7
        # remaining edges: 8
        # edges with no neighbours: 0
        Constructing bicliques LP with mid: 3
        Adding variables...done!
        Adding Constraints 1...done!
        Adding Constraints 2...done! Solving...
        Status for mid =  3 : 3
        Time taken: 0.0397791862487793 ; totaltime: 0.0397791862487793
        Constructing bicliques LP with mid: 4
        Adding variables...done!
        Adding Constraints 1...done!
        Adding Constraints 2...done! Solving...
        Status for mid =  4 : 2
        Time taken: 0.009773731231689453 ; totaltime: 0.04955291748046875
        New sol: 4
        Obj: 4
        Final solution: 4
        End time: 2024-07-22 18:27:05.193830
        $

 9) mwis.py: the branch-and-price algorithm from Section 4 of the paper; relies on a routine from constructg.py. Note that this works on the networkx version of the graph, i.e., after reduction to clique partition.

 10) constructg.py: helper routines for reduction to clique partition as a networkx graph, and visualization. Used, e.g., by mwis.py

 11) mapup.py: helper routine to map the input access matrix to our format. Even if the input is u0, p1, etc., we might renumber those based on which one is seen first when we read the file in. Plus, this does not constrain us to inputs only in the u0, p1, etc. format.

 12) greedythenlattice.py: Ene et al.'s greedy, then lattic-based postprocessing from Section 5 of the paper.

	$ ./greedythenlattice.py ./irreducible.txt
	Start time: 2024-07-22 19:24:46.581885
	UP map written to ./irreducible.txt-upmap.txt
	# vertices: 10
	Removing dominators...
	removedominators, fixpoint iteration # 1
	removedominators, fixpoint iteration # 2
	em saved to ./irreducible.txt-em.txt
	done!
	len(rolesasperms): 0
	Running greedy algorithm...
	len(rolesasperms): 5
	Running lattice-based shrinking...
	len(rolesasperms): 5
	End time: 2024-07-22 19:24:46.582534
	Total time (seconds): 0.0001246929168701172
	$
	$ ./greedythenlattice.py ./PLAIN_small_08.rmp
	Start time: 2024-07-22 19:24:58.001084
	UP map written to ./PLAIN_small_08.rmp-upmap.txt
	# vertices: 284
	Removing dominators...
	removedominators, fixpoint iteration # 1
	removedominators, edgenum: 1000
	removedominators, edgenum: 2000
	removedominators, edgenum: 3000
	removedominators, edgenum: 4000
	removedominators, fixpoint iteration # 2
	removedominators, edgenum: 1000
	removedominators, edgenum: 2000
	removedominators, edgenum: 3000
	removedominators, edgenum: 4000
	removedominators, fixpoint iteration # 3
	removedominators, edgenum: 1000
	removedominators, edgenum: 2000
	removedominators, edgenum: 3000
	removedominators, edgenum: 4000
	em saved to ./PLAIN_small_08.rmp-em.txt
	done!
	len(rolesasperms): 3
	Running greedy algorithm...
	len(rolesasperms): 214
	Running lattice-based shrinking...
	niter: 1000 ...
	len(rolesasperms): 153
	End time: 2024-07-22 19:25:00.595101
	Total time (seconds): 0.018294334411621094
	$

 The following 4 are programs used for our heuristic from Section 5 of the paper. Does require manual intervention while running. So please contact the author for help running these. A quick-n-dirty description of each is provided below.

 13) cutup.py: to chop an input access matrix up into pieces. Even "1" may be provided as an argument for the # pieces so we can then run the remaining programs.
 14) idmbcscutup.py: identify large maximal bicliques. Output should be redirected to a file for later consumption, e.g., by proccutupidmbc.py below.
 15) latticecutup.py: lattice-based post-processing once we have solved for the pieces; see towards the end of Section 5 in the paper.
 16) proccutupidmbc.py: "process" the output generated by idmbcscutup.py above. 
