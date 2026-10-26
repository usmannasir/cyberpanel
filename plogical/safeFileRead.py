#!/usr/local/CyberCP/bin/python
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from plogical.fileSystemSecurity import read_text_file_under


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--allowed-root", required=True)
    parser.add_argument("--file", required=True)
    arguments = parser.parse_args()
    try:
        content = read_text_file_under(arguments.allowed_root, arguments.file,
                                       max_bytes=4 * 1024 * 1024)
    except ValueError as error:
        if str(error) != 'File is too large to edit':
            raise
        print('CYBERPANEL_FILE_TOO_LARGE')
        raise SystemExit(1)
    sys.stdout.write(content)


if __name__ == "__main__":
    main()
