import datetime
import subprocess
import sys


def main():
    print('Start time:', datetime.datetime.now())
    sys.stdout.flush()

    if len(sys.argv) < 3:
        print('Usage: ', end='')
        print(sys.argv[0], end=' ')
        print('<command-to-run>')
        print(f'Example: {sys.executable} {sys.argv[0]} \'createILP.py <input-file>\' 10')
        return

    try:
        result = subprocess.run([sys.executable] + sys.argv[1:-1], timeout=int(sys.argv[-1]))
    except subprocess.TimeoutExpired:
        print("Process timed out")


if __name__ == '__main__':
    main()

