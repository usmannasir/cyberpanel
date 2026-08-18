#!/usr/bin/env python3
"""List Websites selects must use ng-value so numeric ng-model matches options."""
from __future__ import print_function

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = [
    os.path.join(ROOT, 'websiteFunctions/templates/websiteFunctions/listWebsites.html'),
    os.path.join(ROOT, 'websiteFunctions/templates/websiteFunctions/listChildDomains.html'),
]


def main():
    failures = []
    for path in PAGES:
        text = open(path, 'r', encoding='utf-8', errors='replace').read()
        name = os.path.basename(path)
        if 'ng-model="recordsToShow"' not in text:
            failures.append('%s: missing recordsToShow select' % name)
            continue
        if not re.search(r'ng-model="recordsToShow"[\s\S]{0,400}?ng-value="10"', text):
            failures.append('%s: recordsToShow options must use ng-value for 10/50/100' % name)
        if re.search(r'ng-model="recordsToShow"[\s\S]{0,400}?<option>10</option>', text):
            failures.append('%s: bare <option>10</option> causes Angular blank selection' % name)
        if 'ng-model="currentPage"' not in text:
            failures.append('%s: missing currentPage select' % name)
        elif 'ng-value="$index + 1"' not in text:
            failures.append('%s: currentPage options must use ng-value="$index + 1"' % name)
        elif re.search(r'ng-model="currentPage"[\s\S]{0,300}?value="\{\$', text):
            failures.append('%s: currentPage still uses string value="{$ ... $}"' % name)
    if failures:
        print('FAIL:')
        for f in failures:
            print(' -', f)
        return 1
    print('OK: List Websites/Child Domains selects use ng-value for numeric models')
    return 0


if __name__ == '__main__':
    sys.exit(main())
