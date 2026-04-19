#! /usr/bin/python3

import datetime
import sys
import time

from readup import readup, uptopu
from removedominatorsbp import removedominators, isneighbour
import gurobipy as gp
from gurobipy import GRB
from gurobipy import LinExpr

import shutil
import os

def concatenate_files_chunked(output_filename, input_filenames, char=b'\n', chunk_size=1024):
    """
    Concatenates a list of input files into a single output file by streaming data in chunks.
    """
    with open(output_filename, 'wb') as outfile:
        for fname in input_filenames:
            with open(fname, 'rb') as infile:
                shutil.copyfileobj(infile, outfile)
'''                while True:
                   # Read a chunk
                    chunk = infile.read(chunk_size)
                    if not chunk:
                        break

                    # Write the chunk
                    outfile.write(chunk)

                    # Write the new character (must be bytes)
                    outfile.write(char)
'''
#    write_str_to_file('\n', output_filename)

def replace_1c(input_filename, output_filename):
    """
    Reads a large file line by line, replaces '1c' with '1\nc',
    and writes to a new output file.
    """
    try:
        with open(input_filename, 'r') as fin, open(output_filename, 'w') as fout:
            for line in fin:
                # Replace all occurrences of '1c' with '1\nc' in the current line
                modified_line = line.replace('1c', '1\nc')
                fout.write(modified_line)
    except IOError as e:
        print(f"Error processing file: {e}")
        return

    # Optional: Replace the original file with the new file
    # Ensure this is what you want before running!
    try:
        os.replace(output_filename, input_filename)
        print(f"File processing complete. Original file updated: {input_filename}")
    except OSError as e:
        print(f"Error replacing original file: {e}")


def write_str_to_file(content: str, filename: str):
    with open(filename, 'a') as f:
        f.write(content)



def bicliquesbinsearch(em, up, pu):
    totaltime = 0.0

    nusers = len(up)
    nperms = len(pu)
    eset = set()
    for u in up:
        for p in up[u]:
            t = tuple((u,p))
            if t in em:
                continue
            eset.add(t)

    nedges = len(eset)

    hi = nusers
    if hi > nperms:
        hi = nperms
    if hi > nedges:
        hi = nedges
    lo = 1
    sol = hi

    while lo <= hi:
        mid = (lo + hi)//2
        timeone = time.time()
        env = gp.Env(empty=True)
        env.setParam("OutputFlag", 0)
        env.start()

        #construct and solve ILP instance
        print('Constructing bicliques LP with mid:', mid)
        sys.stdout.flush()

#       m = gp.Model("maxset", env=env)

#       print('Adding variables...', end='')
        sys.stdout.flush()
        variables = list()
        for e in eset:
            for i in range(mid):
#               m.addVar(name='x_'+str(e[0])+'_'+str(e[1])+'_'+str(i), vtype=GRB.BINARY)
                variables.append(f'x_{e[0]}_{e[1]}_{i}')
        with open('constraints/binsearch_variables.txt', 'w') as f:
            f.write('\n'.join(variables))
#        m.update()

        print('done!')
        sys.stdout.flush()

        # Constraints 1: every edge in at least 1 biclique
        print('Adding Constraints 1...', end='')
        sys.stdout.flush()
        constraints1 = list()
        with open('constraints/binsearch_constraint1.txt', 'w') as f:
            f.write('')

        for e in eset:
#            l = LinExpr()
            constraint1_terms = list()
            for i in range(mid):
                #u = m.getVarByName('x_'+str(e[0])+'_'+str(e[1])+'_'+str(i))
                term_str = f'x_{e[0]}_{e[1]}_{i}'
                constraint1_terms.append(term_str)
                #l.addTerms(1.0, u)
            constraint1_str = ' + '.join(constraint1_terms)
            #constraints1.append( f'c_1_{e[0]}_{e[1]}: {constraint1_str} >= 1')
            constraints1.append( f'c_1: {constraint1_str} >= 1')

            if len(constraints1) > 500000000:
                with open('constraints/binsearch_constraint1.txt', 'a') as f:
                    f.write('\n'.join(constraints1))
                    constraints1 = list()


        if len(constraints1) > 0:
            with open('constraints/binsearch_constraint1.txt', 'a') as f:
                f.write('\n'.join(constraints1))
                constraints1 = list()
#            m.addConstr(l >= 1, 'c_1_'+str(e[0])+'_'+str(e[1]))
        print('done!')
        sys.stdout.flush()
#        return

        # Constraints 2: non-adjacent edges not in same biclique
        print('Adding Constraints 2...')
        sys.stdout.flush()
        constraints2 = list()
        with open('constraints/binsearch_constraint2.txt', 'w') as fc2:
            fc2.write('')

        print('mid:', mid)
        print('upper bound of the number of entries:', len(eset)*len(eset)*mid)
        edge_pairs_skipped = 0
        for e in eset:
            for f in eset:
                if e >= f or isneighbour(e, f, up):
                    edge_pairs_skipped += 1
                    continue
                for i in range(mid):

#                    u = m.getVarByName('x_'+str(e[0])+'_'+str(e[1])+'_'+str(i))
#                    v = m.getVarByName('x_'+str(f[0])+'_'+str(f[1])+'_'+str(i))
#                    m.addConstr(u + v <= 1, 'c_2_'+str(e[0])+'_'+str(e[1])+'_'+str(f[0])+'_'+str(f[1]))
                    u_str = f'x_{e[0]}_{e[1]}_{i}'
                    v_str = f'x_{f[0]}_{f[1]}_{i}'
                    #constraint2_str = f'c_2_{e[0]}_{e[1]}_{f[0]}_{f[1]}: {u_str} + {v_str} <= 1'
                    constraint2_str = f'c_2: {u_str} + {v_str} <= 1'
                    constraints2.append(constraint2_str)

                    if len(constraints2) > 500000000:
                        with open('constraints/binsearch_constraint2.txt', 'a') as fc2:
                            fc2.write('\n'.join(constraints2))
                            constraints2 = list()

        if len(constraints2) > 0:
            with open('constraints/binsearch_constraint2.txt', 'a') as fc2:
                fc2.write('\n'.join(constraints2))
                print('Size of constraint 2 in bytes: ', len('\n'.join(constraints2).encode('utf-8')))
                constraints2 = list()

        print('edge pairs skipped:', edge_pairs_skipped, ', net number of entries:', len(eset)*len(eset)*mid-edge_pairs_skipped)
        outfilename = 'constraints/binsearch_model.lp'
        tempfilename = 'constraints/binsearch_temp.lp'

        if os.path.exists(outfilename):
            os.remove(outfilename)
            print(f"File '{outfilename}' has been deleted.")
        else:
            print(f"File '{outfilename}' does not exist.")

        if os.path.exists(tempfilename):
            os.remove(tempfilename)
            print(f"File '{tempfilename}' has been deleted.")
        else:
            print(f"File '{tempfilename}' does not exist.")

        write_str_to_file('Minimize\n\n', tempfilename)
        write_str_to_file('Subject To\n', tempfilename)
        concatenate_files_chunked(outfilename, [tempfilename, 'constraints/binsearch_constraint1.txt'])
        shutil.copy2(outfilename, tempfilename)
        write_str_to_file('\n', tempfilename)
        concatenate_files_chunked(outfilename, [tempfilename, 'constraints/binsearch_constraint2.txt'])
        shutil.copy2(outfilename, tempfilename)
        write_str_to_file('\nBounds\n', tempfilename)
        write_str_to_file('Binaries\n', tempfilename)
        concatenate_files_chunked(outfilename, [tempfilename, 'constraints/binsearch_variables.txt'])
        shutil.copy2(outfilename, tempfilename)
        write_str_to_file('\nEnd\n', tempfilename)

        replace_1c(tempfilename, outfilename)
        shutil.copy2(tempfilename, outfilename)

        m = gp.read(outfilename)

#        return


#        m.update()
        print('done! Solving...')
        sys.stdout.flush()

        # m.optimize()
 #       m.write('irreducible_binsearch.lp')
        timetwo = time.time()
        totaltime += timetwo - timeone

        print('Status for mid = ', mid, ':', m.status)
        print('Time taken:', timetwo - timeone, '; totaltime:', totaltime)
        sys.stdout.flush()

        if m.status == GRB.OPTIMAL:
            sol = mid
            print('New sol:', sol)
            sys.stdout.flush()
            hi = mid - 1
        else:
            lo = mid + 1

    return sol

def main():
    print('Start time:', datetime.datetime.now())
    sys.stdout.flush()

    if len(sys.argv) != 2:
        print('Usage: ', end = '')
        print(sys.argv[0], end = ' ')
        print('<input-file>')
        return
    run(sys.argv[1])


def run(upfilename: str):
    up = readup(upfilename)
    if not up:
        return

    pu = uptopu(up)

    """
    em = dict()
    emfilename = sys.argv[1]+'-em.txt'

    if not os.path.isfile(emfilename):
        print('Removing doms + zero-neighbour edges...')
        sys.stdout.flush()

        timeone = time.time()
        em = dict()
        dm = dict()
        seq = 0
        seq = removedominators(em, dm, up, seq)
        timetwo = time.time()

        print('done! Time taken:', timetwo - timeone)
        sys.stdout.flush()

        print('Saving em to', emfilename, end=' ')
        sys.stdout.flush()
        saveem(em, emfilename)
        print('done!')
        sys.stdout.flush()
    else:
        print('Reading em from', emfilename, end=' ')
        sys.stdout.flush()
        em = readem(emfilename)
        print('done!')
        print('Determining em and seq', end=' ')
        sys.stdout.flush()
        dm = dmfromem(em)
        seq = 0
        for e in em:
            if seq < em[e][2]:
                seq = em[e][2]
        print('done!')
        sys.stdout.flush()
    """

    print('Removing dominators + 0-deg...', end='')
    sys.stdout.flush()
    em = dict()
    dm = dict()
    seq = 0
    seq = removedominators(em, dm, up, seq)
    print('done!')
    sys.stdout.flush()

    nedges = 0
    for u in up:
        nedges += len(up[u])

    print("Original # edges:", nedges)
    print('# dominators + zero neighbour edges removed:', seq)
    print('# remaining edges:', nedges - seq)

    """
    print('em:')
    for e in em:
        print('\t'+str(e)+': '+str(em[e]))

    print('dm:')
    for d in dm:
        print('\t'+str(d)+': '+str(dm[d]))
    """

    nzerodeg = 0
    for e in em:
        if em[e][0] < 0:
            nzerodeg += 1

    print('# edges with no neighbours:', nzerodeg)
    sys.stdout.flush()

    if nedges - seq > 0:
        # em = dict()
        obj = int(bicliquesbinsearch(em, up, pu))
    else:
        obj = 0

    print('Obj:', obj)
    print('Final solution:', nzerodeg + obj)

    print('End time:', datetime.datetime.now())


if __name__ == '__main__':
    main()
