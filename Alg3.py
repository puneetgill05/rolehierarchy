import os
import sys

prefix_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(f'{prefix_dir}/..')
sys.path.append(f'{prefix_dir}/../..')

from largebicliques import run_largebicliques


def main():
    run_largebicliques()