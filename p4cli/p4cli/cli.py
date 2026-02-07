from p4cli import P4CLI

import argparse
from pprint import pprint as pp  # pprint.pp() only available from Python 3.8+

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="P4CLI test script")
    parser.add_argument('args', nargs=argparse.REMAINDER, help="Arguments to pass to P4CLI")
    return parser.parse_args()

def main():
    p4 = P4CLI()
    args = parse_args()
    print(args)
    cmd = args.args[0]
    match cmd:
        case _:
            pp(getattr(p4, f"run_{cmd}")(*args.args[1:]))

if __name__ == '__main__':
    main()