#!/usr/bin/env python3

'''
This shouldn't be needed but `p4 rec` would actually allow you to add files that already exist in Perforce.

    $  poc p4 sync ...#0
    ...#0 - file(s) up-to-date.
    $  poc p4 add 10
    //depot/10 - can't add existing file
    $  poc p4 rec -an
    //depot/10#1 - opened for add
    $  poc p4 rec -a
    //depot/10#1 - opened for add
    /home/hacks/ws/poc/10 - empty, assuming binary.

Even though `p4 add` would say no:

    $  poc p4 add 10
    //depot/10 - can't add existing file

This will revert any files that are added but already exist in Perforce, so you can safely run `p4 rec` after it.

    $  poc /path/to/p4_revert_added.py
    Reverting /home/hacks/ws/poc/.p4ignore as it already exists in Perforce with the same content.
    [{'action': 'abandoned',
    'clientFile': '/home/hacks/ws/poc/.p4ignore',
    'depotFile': '//depot/.p4ignore',
    'haveRev': 'none',
    'oldAction': 'add'}]
    [{'action': 'added',
    'change': '1',
    'clientFile': '/home/hacks/ws/poc/.p4ignore',
    'depotFile': '//depot/.p4ignore',
    'fileSize': '10',
    'rev': '1',
    'totalFileCount': '1',
    'totalFileSize': '10'}]


'''

import P4
import argparse
from pprint import pprint as pp  # pprint.pp() only available from Python 3.8+

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Revert files that exists in Perforce, safely.")
    parser.add_argument("-c", "--client", help="Perforce client name")
    parser.add_argument("-u", "--user", help="Perforce user name")
    parser.add_argument("-p", "--port", help="Perforce server port")
    parser.add_argument("--change", help="Specific change number to revert")
    return parser.parse_args()

import hashlib

def md5_file(fpath: str) -> str:
    '''
    Docstring for md5_file
    
    :param fpath: file to checksum
    :type fpath: str
    :return: hexdigest of file content, upper cased
    :rtype: str
    '''
    with open(fpath, 'rb') as infile:
        return hashlib.file_digest(infile, 'md5').hexdigest().upper()




def main() -> None:
    cfg = parse_args()
    p4 = P4.P4()
    if cfg.client:
        p4.client = cfg.client
    if cfg.user:
        p4.user = cfg.user
    if cfg.port:
        p4.port = cfg.port
    p4.connect()

    opened_files = p4.run_opened(f'-c {chg}'.split() if cfg.change else '-c default'.split())
    for of in opened_files:
        if of['action'] != 'add':
            continue
    
        fstats = p4.run_fstat(['-Ol', of['depotFile']])
        if not fstats:
            continue  # shouldn't happen since we are getting the list from `p4 opened`, but just in case
        assert(len(fstats) == 1)
        fstat = fstats[0]
        # pp(fstat)
        if not fstat.get('headRev'):
            continue  # not on server

        if md5_file(fstat['clientFile']) == fstat['digest']:
            print(f"Reverting {fstat['clientFile']} as it already exists in Perforce with the same content.")
            pp(p4.run_revert(fstat['clientFile']))
            pp(p4.run_sync(fstat.get('depotFile')))
    

if __name__ == "__main__":
    main()
