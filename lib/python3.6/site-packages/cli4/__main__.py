#!/usr/bin/env python
"""Cloudflare API via command line"""
from __future__ import absolute_import

import sys

from .cli4 import cli4

def main(args=None):
    """Cloudflare API via command line"""
    if args is None:
        args = sys.argv[1:]
    cli4(args)

if __name__ == '__main__':
    main()
