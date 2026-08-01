#!/usr/bin/env python3
"""Full Settings page: content-width tile grid, log cards, unclipped selects."""
from __future__ import print_function

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(ROOT, 'websiteFunctions/templates/websiteFunctions/website.html')


def main():
    failures = []
    text = open(HTML, encoding='utf-8').read()

    if 'repeat(auto-fill, minmax(220px, 1fr))' not in text:
        failures.append('content-box-wrapper tiles need auto-fill grid (sidebar-safe)')
    if re.search(r'\.content-box-wrapper \.row \.col-md-3\s*\{[^}]*flex:\s*0 0 25%', text):
        failures.append('fixed 25% col-md-3 tiles still present (crushes with sidebar)')
    if 'log-card' not in text or 'log-list' not in text:
        failures.append('Access Logs must use card list, not only a wide table')
    if re.search(r'fetchedData[\s\S]{0,800}<table class="table cyber-table"', text):
        failures.append('Access Logs still use cyber-table inside fetchedData')
    if not re.search(r'\.cyberpanel-website-page select\.form-control\s*\{[^}]*padding:\s*0 36px 0 12px\s*!important', text):
        failures.append('page-wide select unclip padding missing')
    if "ng-value=\"'Enable'\"" not in text or 'phpSelectionMaster' not in text:
        failures.append('open_basedir / PHP master selects need ng-value')
    if re.search(r'ng-model="openBasedirValue"[\s\S]{0,200}<option>Enable</option>', text):
        failures.append('bare openBasedirValue options still present')
    if 'ld-card' not in text:
        failures.append('List Domains cards must remain')

    if failures:
        print('FAIL:')
        for item in failures:
            print(' -', item)
        return 1
    print('OK: Full Settings mobile cards / log cards / select contract holds')
    return 0


if __name__ == '__main__':
    sys.exit(main())
