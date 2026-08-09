#!/usr/bin/env python3
"""Unit checks for CyberPanel sensitive-file denial helpers (#1859)."""
import os
import sys
import tempfile

sys.path.insert(0, '/usr/local/CyberCP')

from plogical.vhostConfs import vhostConfs
from plogical.vhost import vhost


def test_template_contains_rules():
    for name in ('olsMasterConf', 'olsChildConf', 'lswsMasterConf', 'lswsChildConf'):
        conf = getattr(vhostConfs, name)
        assert '# BEGIN CyberPanel sensitive-file denials (#1859)' in conf, name
        assert r'RewriteRule (^|/)\.env - [F,L]' in conf, name
        assert r'RewriteRule (^|/)\.git(/|$) - [F,L]' in conf, name


def test_ensure_injects_into_bare_rewrite():
    bare = (
        'docRoot /tmp\n'
        'rewrite  {\n'
        '  enable                  1\n'
        '  autoLoadHtaccess        1\n'
        '}\n'
    )
    with tempfile.NamedTemporaryFile('w+', delete=False) as fh:
        path = fh.name
        fh.write(bare)
    try:
        assert vhost.ensureSensitiveFileDenials(path) == 1
        with open(path) as fh:
            updated = fh.read()
        assert '# BEGIN CyberPanel sensitive-file denials (#1859)' in updated
        assert 'rules                   <<<END_rules' in updated
        assert vhost.ensureSensitiveFileDenials(path) == 0  # idempotent
    finally:
        os.unlink(path)


def test_ensure_prepends_existing_rules_block():
    existing = (
        'rewrite  {\n'
        '  enable                  1\n'
        '  autoLoadHtaccess        1\n'
        '  rules                   <<<END_rules\n'
        'RewriteRule ^/foo$ /bar [L]\n'
        '  END_rules\n'
        '}\n'
    )
    with tempfile.NamedTemporaryFile('w+', delete=False) as fh:
        path = fh.name
        fh.write(existing)
    try:
        assert vhost.ensureSensitiveFileDenials(path) == 1
        with open(path) as fh:
            updated = fh.read()
        begin = updated.find('# BEGIN CyberPanel sensitive-file denials (#1859)')
        foo = updated.find('RewriteRule ^/foo$ /bar [L]')
        assert begin != -1 and foo != -1 and begin < foo
    finally:
        os.unlink(path)


if __name__ == '__main__':
    test_template_contains_rules()
    test_ensure_injects_into_bare_rewrite()
    test_ensure_prepends_existing_rules_block()
    print('OK: sensitive-file denial checks passed')
