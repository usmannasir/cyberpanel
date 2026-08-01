#!/usr/bin/env python3
"""List page selects: ng-value for numeric models + global select clip CSS."""
from __future__ import print_function

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = [
    ('websiteFunctions/templates/websiteFunctions/listWebsites.html', True),
    ('websiteFunctions/templates/websiteFunctions/listChildDomains.html', True),
    ('websiteFunctions/templates/websiteFunctions/ListDockersite.html', True),
    ('websiteFunctions/templates/websiteFunctions/manageGIT.html', True),
]
HARMONIZE = [
    'baseTemplate/static/baseTemplate/css/cyberpanel-harmonize.css',
    'public/static/baseTemplate/css/cyberpanel-harmonize.css',
]


def main():
    failures = []
    for rel, need_ngvalue in PAGES:
        path = os.path.join(ROOT, rel)
        text = open(path, 'r', encoding='utf-8', errors='replace').read()
        name = os.path.basename(path)
        if 'ng-model="recordsToShow"' not in text:
            failures.append('%s: missing recordsToShow' % name)
            continue
        if need_ngvalue and not re.search(r'ng-model="recordsToShow"[\s\S]{0,500}?ng-value="10"', text):
            # WPsitesList uses ng-options instead
            if 'ng-options=' not in text.split('ng-model="recordsToShow"', 1)[1][:400]:
                failures.append('%s: recordsToShow needs ng-value or ng-options' % name)
        if re.search(r'ng-model="recordsToShow"[\s\S]{0,400}?<option>10</option>', text):
            failures.append('%s: bare <option>10</option> still present' % name)
    for rel in HARMONIZE:
        path = os.path.join(ROOT, rel)
        text = open(path, 'r', encoding='utf-8', errors='replace').read()
        if 'padding: 0 28px 0 12px !important' not in text:
            failures.append('%s: missing global select clip fix' % os.path.basename(path))
        if '#main-content select.form-control' not in text:
            failures.append('%s: missing #main-content select.form-control rule' % os.path.basename(path))
    wp = open(os.path.join(ROOT, 'websiteFunctions/templates/websiteFunctions/WPsitesList.html'), encoding='utf-8').read()
    if 'search-bar input.form-control' not in wp:
        failures.append('WPsitesList.html: form-control padding still applies to selects')
    if 'end < 1' not in wp and 'end < start' not in wp:
        failures.append('WPsitesList.html: range filter not guarded for empty lists')
    if failures:
        print('FAIL:')
        for f in failures:
            print(' -', f)
        return 1
    print('OK: list-page select visibility contract holds')
    return 0


if __name__ == '__main__':
    sys.exit(main())
