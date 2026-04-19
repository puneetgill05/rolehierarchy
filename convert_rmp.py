import datetime
import sys

from minedgerolemining.readup import dumpup


def to_our_format(rmpfilepath: str):
    up_dict = dict()
    with open(rmpfilepath, 'r') as file:
        for line in file:
            if line.startswith('u'):
                words = line.strip().split()
                u = None
                for word in words:
                    if word.startswith('u'):
                        u = word[1:]
                        up_dict[u] = set()
                    elif word.startswith('p'):
                        up_dict[u].add(word[1:])
    return up_dict


def main():
    print('Start time:', datetime.datetime.now())
    sys.stdout.flush()

    if len(sys.argv) != 3:
        print('Usage: ', end='')
        print(sys.argv[0], end=' ')
        print('<rmp-input-file> <up-output-file>')
        return
    rmpfilepath = sys.argv[1]
    upfilepath = sys.argv[2]
    up_dict = to_our_format(rmpfilepath)
    dumpup(up_dict, upfilepath)


if __name__ == '__main__':
    main()
