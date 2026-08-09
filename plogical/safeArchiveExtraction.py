#!/usr/local/CyberCP/bin/python
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from plogical.fileSystemSecurity import safe_extract_archive


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--allowed-root", required=True)
    parser.add_argument("--archive", required=True)
    parser.add_argument("--destination", required=True)
    parser.add_argument("--type", required=True, choices=("zip", "tar", "tar.gz", "tgz"))
    arguments = parser.parse_args()
    safe_extract_archive(
        arguments.allowed_root,
        arguments.archive,
        arguments.destination,
        arguments.type,
    )


if __name__ == "__main__":
    main()
