import hashlib
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


# A package the PHP extension pages list: LiteSpeed PHP (lsphp83-apcu), Remi
# (php83-php-fpm) and Debian or Ubuntu (php8.3-curl) packages, with the
# architecture suffix yum prints (lsphp83-apcu.x86_64), and the two Apache
# packages `apt list` shows beside them.
PHP_PACKAGE = re.compile(
    r'(?:(?:lsphp[0-9]{2,3}|php[0-9]{2,3}|php[0-9]\.[0-9]{1,2})(?:[.-][A-Za-z0-9][A-Za-z0-9.+_-]*)?'
    r'|libapache2-mod-php[0-9]\.[0-9]{1,2}|libphp[0-9]\.[0-9]{1,2}-embed)')


def is_php_package(name):
    """True for one PHP package name; the package managers are given nothing else."""
    return isinstance(name, str) and len(name) <= 128 and PHP_PACKAGE.fullmatch(name) is not None


def php_package_prefix(selection, apache, rpm_family):
    """Return the start of the package names of a PHP selection, built from its digits.

    lsphp83 for LiteSpeed PHP; for the Apache backend php83 (Remi) or php8.3
    (Debian, Ubuntu).
    """
    major, minor = php_selection_digits(selection)
    if not apache:
        return 'lsphp%s%s' % (major, minor)
    if rpm_family:
        return 'php%s%s' % (major, minor)
    return 'php%s.%s' % (major, minor)


FPM_POOL_NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}')


def fpm_pool_name(external_app, domain):
    """Return the section name for the PHP-FPM pool of one website or child domain.

    php-fpm merges every section of the same name in the pool files of a PHP
    version into one pool, and the last file read decides its socket and
    user. The name therefore has to differ from every other pool: it is the
    website's system user followed by a digest of the domain.
    """
    digest = hashlib.sha256(domain.encode('utf-8')).hexdigest()[:12]
    name = '%s-%s' % (external_app, digest)
    if FPM_POOL_NAME.fullmatch(name) is None:
        raise ValueError('Invalid PHP-FPM pool name.')
    return name


def existing_fpm_pool_name(pool_file_text):
    """Return the section name of an existing pool file, or None if it has no usable one.

    Tuning a pool rewrites its file and keeps this name, so a pool created
    by an earlier version is not renamed. 'global' and 'www' are never kept:
    the first is php-fpm's own section, the second the distribution's pool.
    """
    for line in str(pool_file_text or '').splitlines():
        line = line.strip()
        if not line or line[0] in ';#':
            continue
        match = re.fullmatch(r'\[([^\]]*)\]', line)
        if match is None or FPM_POOL_NAME.fullmatch(match.group(1)) is None:
            return None
        if match.group(1).lower() in ('global', 'www'):
            return None
        return match.group(1)
    return None


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
