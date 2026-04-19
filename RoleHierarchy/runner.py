#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys

import RHBuilder_Vaidya, RBAC_to_RH, RBAC_RH_IP_V2, RoleMiner_Stoller


def main():
    parser = argparse.ArgumentParser(description="Run specified python script")
    parser.add_argument("algorithm", type=str, help="Algorithm to run")
    parser.add_argument("input_file", type=str, help="Input file to read")
    parser.add_argument("output_file", type=str, help="Output file to write data to")
    args = parser.parse_args()

    VAIDYA = 'RHBuilder_Vaidya'
    STOLLER = 'RoleMiner_Stoller'
    ALG1 = 'RBAC_to_RH'
    ALG2 = 'RBAC_RH_IP_V2'

    algorithms = {
        'alg1': ALG1,
        'alg2': ALG2,
        'vaidya': VAIDYA,
        'stoller': STOLLER
    }

    python_script_to_run = algorithms[args.algorithm]

    input_file = args.input_file
    output_file = args.output_file

    with open(input_file, 'r') as f:
        input_files_data = json.load(f)
        input_files = input_files_data['files']
        for input_file in input_files:
            if python_script_to_run == VAIDYA:
                args = argparse.Namespace(input_file=input_file)
                _, metrics = RHBuilder_Vaidya.main(args)
            elif python_script_to_run == ALG1:
                args = argparse.Namespace(input_file=input_file, rbac_algorithm='maxsetsbp')
                _, metrics = RBAC_to_RH.main(args)
            elif python_script_to_run == ALG2:
                args = argparse.Namespace(input_file=input_file)
                _, metrics = RBAC_RH_IP_V2.main(args)
            elif python_script_to_run == STOLLER:
                args = argparse.Namespace(input_file=input_file, wR=1, wUA=1, wPA=1, wRH=1, wDA=0, timeout=10800,
                                          attrs=None,
                                          delta=1.001, polq='WSC-INT', roleq='redundancy')

                _, metrics = RoleMiner_Stoller.main(args)
            else:
                print('Nothing to do ...')
                return
            # result = subprocess.run([python_script_to_run, input_file], capture_output=True, text=True, check=True)
            data_to_write = {
                'script': python_script_to_run,
                'UP input file': input_file,
                'metrics': metrics
            }

            if not os.path.exists(output_file):
                with open(output_file, "w") as f2:
                    f2.write("[]")  # write an empty JSON object

            data_so_far = []
            with open(output_file, 'r') as f2:
                data_so_far = json.load(f2)
                data_so_far.append(data_to_write)

            with open(output_file, 'w') as f2:
                json.dump(data_so_far, f2, indent=4, sort_keys=True)


if __name__ == "__main__":
    main()
