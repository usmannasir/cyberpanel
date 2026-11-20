#!/usr/local/CyberCP/bin/python
"""Set the owner, group and mode of one directory, or the owner and group of one
plain file, without following any link.

Run with privilege by the panel for paths that sit inside a website's home,
which the website's own user can rename or replace at any moment.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from plogical.fileSystemSecurity import set_directory_owner, set_file_owner


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--allowed-root", required=True)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--directory")
    target.add_argument("--file")
    parser.add_argument("--user", required=True)
    parser.add_argument("--group", required=True)
    parser.add_argument("--mode")
    arguments = parser.parse_args()
    mode = None
    if arguments.mode is not None:
        if not arguments.mode.isdigit() or len(arguments.mode) > 4:
            sys.exit("Invalid directory mode")
        mode = int(arguments.mode, 8)
    if arguments.file is not None:
        if mode is not None:
            sys.exit("A file keeps its mode")
        set_file_owner(arguments.allowed_root, arguments.file, arguments.user, arguments.group)
        return
    set_directory_owner(arguments.allowed_root, arguments.directory, arguments.user,
                        arguments.group, mode)


if __name__ == "__main__":
    main()
