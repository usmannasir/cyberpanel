#!/usr/bin/env python3
"""List Domains (Full Settings): child JSON + card layout with full path text."""
from __future__ import print_function

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    failures = []

    child_py = open(os.path.join(ROOT, 'plogical/childDomain.py'), encoding='utf-8').read()
    if 'childBaseDir' not in child_py or 'phpSelection' not in child_py:
        failures.append('childDomain.py: fetch JSON must include childBaseDir and phpSelection')
    if 'openBasedirLabel' not in child_py:
        failures.append('childDomain.py: missing openBasedirLabel helper')

    website_html = open(
        os.path.join(ROOT, 'websiteFunctions/templates/websiteFunctions/website.html'),
        encoding='utf-8'
    ).read()
    list_block = website_html.split('id="listDomains"', 1)[1][:12000] if 'id="listDomains"' in website_html else ''

    if "ng-value=\"'Enable'\"" not in list_block:
        failures.append('website.html List Domains: open_basedir needs ng-value Enable')
    if re.search(r'ng-model="record\.childBaseDir"[\s\S]{0,300}?<option>Enable</option>', list_block):
        failures.append('website.html: bare <option>Enable</option> still present')
    if 'ld-card' not in list_block or 'ld-path' not in list_block:
        failures.append('website.html List Domains: must use card layout with ld-path')
    if 'class="table cyber-table"' in list_block:
        failures.append('website.html List Domains: wide cyber-table must be replaced by cards')
    if 'overflow-wrap: anywhere' not in website_html or '#listDomains .ld-path' not in website_html:
        failures.append('website.html: missing List Domains full-path CSS')
    if 'min-width: 600px' in website_html and '#listDomains' in website_html:
        # Global 600px table min-width regresses narrow viewports
        if re.search(r'\.table\s*\{[^}]*min-width:\s*600px', website_html):
            failures.append('website.html: global table min-width 600px still present')

    acl_py = open(os.path.join(ROOT, 'plogical/acl.py'), encoding='utf-8').read()
    if 'def CachedAddonPermission' not in acl_py:
        failures.append('acl.py: missing CachedAddonPermission')

    website_py = open(os.path.join(ROOT, 'websiteFunctions/website.py'), encoding='utf-8').read()
    if 'CachedAddonPermission' not in website_py:
        failures.append('website.py loadDomainHome: should use CachedAddonPermission')
    if "'phpSelection': phpSelection" not in website_py:
        failures.append('website.py findChildsListJson: missing phpSelection')

    list_child = open(
        os.path.join(ROOT, 'websiteFunctions/templates/websiteFunctions/listChildDomains.html'),
        encoding='utf-8'
    ).read()
    if 'web.path' not in list_child or 'web.phpSelection' not in list_child:
        failures.append('listChildDomains.html: cards should show path and PHP')

    try:
        sys.path.insert(0, ROOT)
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CyberCP.settings')
        import django
        django.setup()
        from websiteFunctions.models import Websites
        from plogical.childDomain import ChildDomainManager
        if Websites.objects.filter(domain='newstargeted.com').exists():
            raw = ChildDomainManager('newstargeted.com').findChildDomainsJson(0)
            data = json.loads(raw)
            if not isinstance(data, list):
                failures.append('findChildDomainsJson: not a list')
            elif data:
                sample = data[0]
                for key in ('childDomain', 'path', 'phpSelection', 'childBaseDir'):
                    if key not in sample:
                        failures.append('findChildDomainsJson sample missing %s' % key)
                if sample.get('childBaseDir') not in ('Enable', 'Disable'):
                    failures.append('childBaseDir must be Enable or Disable, got %r' % sample.get('childBaseDir'))
    except Exception as exc:
        failures.append('runtime check skipped/failed: %s' % exc)

    if failures:
        print('FAIL:')
        for item in failures:
            print(' -', item)
        return 1
    print('OK: List Domains card layout / full path / childBaseDir contract holds')
    return 0


if __name__ == '__main__':
    sys.exit(main())
