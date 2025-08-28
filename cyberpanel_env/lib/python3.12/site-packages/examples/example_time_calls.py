#!/usr/bin/env python
"""Cloudflare API code - example"""

import os
import sys
import time

sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('..'))
import CloudFlare

def main():
    """Cloudflare API code - example"""

    # Simple timing of calls

    print('Create')
    tic = time.process_time_ns()
    try:
        cf = CloudFlare.CloudFlare()
    except Exception as e:
        print('\tError: %s' % (e))
        cf = None
    toc = time.process_time_ns()
    print('\t%7.3f ms' % ((toc-tic)/1000000.0))
    print('')

    if not cf:
        return

    print('Call')
    for ii in range(0,10):
        tic = time.process_time_ns()
        try:
            r = cf.ips()
        except Exception as e:
            print('\tError: %s' % (e))
            break
        toc = time.process_time_ns()
        print('\t%7.3f ms' % ((toc-tic)/1000000.0))
    print('')

    print('Close')
    tic = time.process_time_ns()
    del cf
    toc = time.process_time_ns()
    print('\t%7.3f ms' % ((toc-tic)/1000000.0))
    print('')

if __name__ == '__main__':
    main()
