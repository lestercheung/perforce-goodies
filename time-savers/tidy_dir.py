#!/usr/bin/env python3

import argparse
import os
from datetime import datetime
from pathlib import Path
from pprint import pp


def parse_args():
    ap = argparse.ArgumentParser("Tidy directory by groupping files based on mtime.")
    ap.add_argument("--dst", type=Path, help="Destination directory for tidied files")
    ap.add_argument(
        "--group-by-format",
        type=str,
        default="%Y/%Y-%m",
        help="Format string for grouping files by mtime (default: '%%Y-%%m')",
    )
    ap.add_argument("src", type=Path, help="Directory to tidy")

    return ap.parse_args()


def main():
    cfg = parse_args()
    pp(cfg)
    if not cfg.dst:
        cfg.dst = cfg.src
    script_fpath = os.path.realpath(__file__)
    print(f"Script file path: {script_fpath}")
    for dir_entry in cfg.src.glob("*"):
        if dir_entry.is_dir() or dir_entry.resolve() == Path(script_fpath).resolve():
            print(f"Skipping {dir_entry}")
            continue
        mtime = datetime.fromtimestamp(dir_entry.stat().st_mtime)
        dst_dir = cfg.dst / mtime.strftime(cfg.group_by_format)
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst_fpath = dst_dir / dir_entry.name
        print(f"Moving {dir_entry} to {dst_dir}")
        os.rename(dir_entry, dst_fpath)


if __name__ == "__main__":
    main()
