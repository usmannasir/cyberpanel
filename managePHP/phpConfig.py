import re


# The panel's own name for a PHP version: 'PHP 8.3'. One digit for the major
# number; the minor number may have two ('PHP 8.10' is lsphp810).
PHP_SELECTION = re.compile(r'PHP ([0-9])\.([0-9]|[1-9][0-9])')


def php_selection_digits(selection):
    """Return the two numbers of a PHP selection: ('8', '3') for 'PHP 8.3'.

    This is the one check of a PHP selection. The text must be exactly the
    panel's own form; anything else raises ValueError. Every name derived
    from a selection (lsphp directory, FPM service, ini path) is built from
    the returned digits, never from the text that was received.
    """
    match = PHP_SELECTION.fullmatch(selection) if isinstance(selection, str) else None
    if match is None:
        raise ValueError('Invalid PHP version selected.')
    return match.groups()


def fpm_service_for_selection(selection, rpm_family):
    """Return the PHP-FPM service of a selection.

    php83-php-fpm on the RPM family (Remi packages), php8.3-fpm on Debian
    and Ubuntu.
    """
    major, minor = php_selection_digits(selection)
    if rpm_family:
        return 'php%s%s-php-fpm' % (major, minor)
    return 'php%s.%s-fpm' % (major, minor)


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
