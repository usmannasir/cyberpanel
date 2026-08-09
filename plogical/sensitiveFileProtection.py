import os
import re
import tempfile


BEGIN_MARKER = '# BEGIN CyberPanel sensitive-file denials'
END_MARKER = '# END CyberPanel sensitive-file denials'

OLS_DENY_RULES = """# BEGIN CyberPanel sensitive-file denials
RewriteRule (^|/)\\.env - [F,L]
RewriteRule (^|/)\\.git(/|$) - [F,L]
RewriteRule (^|/)\\.htpasswd$ - [F,L]
RewriteRule (^|/)\\.user\\.ini$ - [F,L]
RewriteRule (^|/)\\.htaccess$ - [F,L]
# END CyberPanel sensitive-file denials"""


def _protected_content(content):
    if BEGIN_MARKER in content:
        return content

    candidates = []
    for match in re.finditer(
        r'(?ms)^(?P<indent>[ \t]*)rewrite[ \t]*\{(?P<body>.*?)(?P<close>^(?P=indent)\})',
        content,
    ):
        if re.search(r'(?m)^[ \t]*autoLoadHtaccess[ \t]+[01][ \t]*$', match.group('body')):
            candidates.append(match)

    rewrite = min(candidates, key=lambda match: (len(match.group('indent')), match.start())) if candidates else None
    if rewrite:
        indent = rewrite.group('indent')
        rules = re.search(
            r'(?m)^[ \t]*rules[ \t]+<<<[A-Za-z0-9_]+[ \t]*$',
            rewrite.group(0),
        )
        if rules:
            insertion_at = rewrite.start() + rules.end()
            return content[:insertion_at] + '\n' + OLS_DENY_RULES + content[insertion_at:]

        insertion_at = rewrite.start('close')
        block = (
            '%s  rules                   <<<END_rules\n'
            '%s\n'
            '%s  END_rules\n'
        ) % (indent, OLS_DENY_RULES, indent)
        return content[:insertion_at] + block + content[insertion_at:]

    block = (
        '\nrewrite  {\n'
        '  enable                  1\n'
        '  autoLoadHtaccess        1\n'
        '  rules                   <<<END_rules\n'
        + OLS_DENY_RULES + '\n'
        '  END_rules\n'
        '}\n'
    )
    return content.rstrip() + block


def protect_vhost_file(vhost_file):
    if not vhost_file or not os.path.isfile(vhost_file):
        return 0

    try:
        with open(vhost_file, 'r') as handle:
            original = handle.read()
        protected = _protected_content(original)
        if protected == original:
            return 0

        file_stat = os.stat(vhost_file)
        directory = os.path.dirname(vhost_file) or '.'
        descriptor, temporary_path = tempfile.mkstemp(prefix='.vhost.', dir=directory, text=True)
        try:
            with os.fdopen(descriptor, 'w') as handle:
                handle.write(protected)
                handle.flush()
                os.fsync(handle.fileno())
                os.fchmod(handle.fileno(), file_stat.st_mode)
                try:
                    os.fchown(handle.fileno(), file_stat.st_uid, file_stat.st_gid)
                except PermissionError:
                    pass
            os.replace(temporary_path, vhost_file)
        finally:
            if os.path.exists(temporary_path):
                os.unlink(temporary_path)
        return 1
    except (OSError, IOError):
        return -1


def protect_vhost_tree(vhost_root='/usr/local/lsws/conf/vhosts'):
    results = {'examined': 0, 'updated': 0, 'skipped': 0, 'errors': 0}
    if not os.path.isdir(vhost_root):
        results['errors'] = 1
        return results

    for name in sorted(os.listdir(vhost_root)):
        if name in ('Example', 'cyberpanel'):
            continue
        vhost_file = os.path.join(vhost_root, name, 'vhost.conf')
        if not os.path.isfile(vhost_file):
            continue
        results['examined'] += 1
        status = protect_vhost_file(vhost_file)
        if status == 1:
            results['updated'] += 1
        elif status == 0:
            results['skipped'] += 1
        else:
            results['errors'] += 1
    return results
