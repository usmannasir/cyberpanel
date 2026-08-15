#!/usr/local/CyberCP/bin/python
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from plogical.systemPassword import (
    apply_system_password,
    consume_system_password_request,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--token", required=True)
    arguments = parser.parse_args()
    request = consume_system_password_request(arguments.token)
    apply_system_password(request["username"], request["password"])


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.stderr.write("Unable to change system password.\n")
        sys.exit(1)
