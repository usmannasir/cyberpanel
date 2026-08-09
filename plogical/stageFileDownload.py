#!/usr/local/CyberCP/bin/python
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from plogical.fileSystemSecurity import stage_file_for_download


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--allowed-root", required=True)
    parser.add_argument("--file", required=True)
    arguments = parser.parse_args()
    sys.stdout.write(stage_file_for_download(arguments.allowed_root, arguments.file))


if __name__ == "__main__":
    main()
