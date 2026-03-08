#!/usr/bin/env python3

import os
import sqlite3
import argparse
import P4
from pprint import pprint as pp

SQL_CONCAT_SEP = "::"  # separator for GROUP_CONCAT in SQLite, should be something that won't appear in depot paths


def parse_args():
    ap = argparse.ArgumentParser(description="dedupe with info from Perforce")
    _ = "p4cache.db"
    ap.add_argument(
        "--db",
        default=_,
        metavar=_,
        help="path to sqlite database file (default: %(default)s)",
    )
    subparser = ap.add_subparsers(dest="command", required=True)
    cache_ap = subparser.add_parser(
        "cache", help="cache Perforce info into the database"
    )
    cache_ap.add_argument(
        "depot_paths", nargs="+", help="depot paths to cache (e.g. //depot/...)"
    )
    cache_ap.set_defaults(func=do_cache)

    dedupe_ap = subparser.add_parser(
        "dedupe", help="show duplicate files based on md5"
    )
    dedupe_ap.add_argument(
        "--dont-keep-shortest-path",
        "--dksp",
        default=False,
        action="store_true",
        help="do not keep the file with the shortest depot path",
    )
    dedupe_ap.add_argument(
        "--keep-path",
        "-k",
        dest="keep_paths",
        action="append",
        default=[],
        help="prefer keeping files that matches this (server) depot path (can be specified multiple times)",
    )
    dedupe_ap.add_argument(
        '--only-delete',
        dest='delete_paths',
        action='append',
        default=[],
        help="only delete files that matches this (server) depot path (can be specified multiple times)",
    )
    dedupe_ap.add_argument(
        "--yes",
        "-y",
        action="store_true",
        default=False,
        help="automatically delete duplicates without asking",
    )
    # dedupe_ap.add_argument(
    #     "depot_paths", nargs="*", default=[], help="depot paths to dedupe (e.g. //depot/...)"
    # )
    dedupe_ap.set_defaults(func=do_dedupe)

    return ap.parse_args()


def do_cache(cfg: argparse.Namespace):
    p4 = P4.P4()
    p4.connect()

    conn = sqlite3.connect(cfg.db)
    cux = conn.cursor()
    cux.executescript("""
        CREATE TABLE IF NOT EXISTS files (
            depot_file TEXT PRIMARY KEY,
            size INTEGER,
            md5 TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_files_md5 ON files(md5);
    """)

    for depot_path in cfg.depot_paths:
        print(f"Caching {depot_path}...")
        for f in p4.run_fstat("-Ol", depot_path):
            # pp(f)
            if f.get("headAction") in ('delete', 'move/delete'):
                continue
            cux.execute(
                """
                INSERT OR REPLACE INTO files (depot_file, size, md5) VALUES (?, ?, ?)
            """,
                (f.get("depotFile"), f.get("fileSize"), f.get("digest")),
            )
    conn.commit()
    conn.close()


def do_dedupe(cfg: argparse.Namespace):
    # if not os.path.exists(cfg.db):
    #     print(f"Caching data to {cfg.db}")
    #     do_cache(cfg)
    conn = sqlite3.connect(cfg.db)
    cux = conn.cursor()
    cux.execute(f"""
        SELECT md5, size, COUNT(*) as count, GROUP_CONCAT(depot_file, '{SQL_CONCAT_SEP}') AS files
        FROM files
        GROUP BY md5
        HAVING COUNT(*) > 1
    """)
    saved, dupes = 0, 0
    keep_map, delete_map = P4.Map(), P4.Map()
    for keep_path in cfg.keep_paths:
        keep_map.insert(keep_path, "//client/...")
    for delete_path in cfg.delete_paths:
        delete_map.insert(delete_path, "//client/...")

    for md5, size, count, files in cux.fetchall():
        if size:
            saved += (count - 1) * size
            dupes += count - 1
        files = sorted(
            files.split(SQL_CONCAT_SEP), key=lambda f: f.count("/"), reverse=False
        )  # sort by depth

        keepers = set()
        for f in files:
            if f in keepers:
                continue
            if keep_map.includes(f):
                keepers.add(f)
                continue
            if not delete_map.includes(f):
                keepers.add(f)
                continue
        if not cfg.dont_keep_shortest_path:
            keepers.add(files[0])

        trash = set(files) - keepers
        print(f"✅ {keepers} ❌ {trash}")

    conn.close()
    print(f"Total potential savings: {saved:,} bytes, removing {dupes} duplicates")


def main():
    cfg = parse_args()
    pp(cfg)
    cfg.func(cfg)


if __name__ == "__main__":
    main()
