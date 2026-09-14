import re


def matches_directive(line, directive):
    """Return True when an INI line assigns the requested directive."""
    pattern = r'^\s*' + re.escape(directive) + r'\s*='
    return re.match(pattern, line, re.IGNORECASE) is not None


def fpm_service_for_ini(path):
    """Return the FPM service for a managed FPM ini; LSAPI needs no FPM restart."""
    remi = re.fullmatch(r'/etc/opt/remi/php([0-9]+)/php\.ini', path)
    if remi:
        return 'php%s-php-fpm' % remi.group(1)
    debian = re.fullmatch(r'/etc/php/([0-9]+\.[0-9]+)/fpm/php\.ini', path)
    if debian:
        return 'php%s-fpm' % debian.group(1)
    return None
