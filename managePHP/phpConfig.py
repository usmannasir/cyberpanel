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


# How earlier releases also wrote a PHP version in storage, in backups and on
# the command line: 'PHP 74', 'php 7.4', 'PHP  7.4', '7.4', '74'.
PHP_SELECTION_SPELLING = re.compile(
    r'(?:[Pp][Hh][Pp] *)?(?:([0-9])\.([0-9]{1,2})|([0-9])([0-9]{1,2}))')


def normalized_php_selection(value):
    """Return the panel's own form, 'PHP 7.4', for an older spelling of a PHP version.

    For values that come from storage, from a backup or from the command
    line; a request from a page is checked with php_selection_digits and
    nothing else. Without a dot the first digit is the major number and the
    rest the minor one ('74' is 7.4, '810' is 8.10). The result is built from
    the digits and passes php_selection_digits; anything else raises
    ValueError.
    """
    match = PHP_SELECTION_SPELLING.fullmatch(value) if isinstance(value, str) else None
    if match is None:
        raise ValueError('Invalid PHP version selected.')
    major, minor = [part for part in match.groups() if part is not None]
    selection = 'PHP %s.%s' % (major, minor)
    php_selection_digits(selection)
    return selection


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


# The nine directives of the basic PHP settings page, in the order it saves them.
PHP_FLAGS = ('allow_url_fopen', 'display_errors', 'file_uploads', 'allow_url_include')
PHP_SIZES = ('memory_limit', 'upload_max_filesize', 'post_max_size')
PHP_SECONDS = ('max_execution_time', 'max_input_time')
BASIC_PHP_SETTINGS = ('allow_url_fopen', 'display_errors', 'file_uploads', 'allow_url_include', 'memory_limit',
                      'max_execution_time', 'upload_max_filesize', 'max_input_time', 'post_max_size')
PHP_SIZE_VALUE = re.compile(r'[+-]?[0-9]{1,10}[KMGkmg]?')
PHP_SECONDS_VALUE = re.compile(r'[+-]?[0-9]{1,6}')


def php_flag(value):
    """Return '1' or '0' for a switch of the basic PHP settings page.

    The page sends true or false; the worker is handed the result.
    """
    if value is True or (type(value) in (int, str) and str(value) == '1'):
        return '1'
    if value is False or (type(value) in (int, str) and str(value) == '0'):
        return '0'
    raise ValueError('Invalid value for a PHP switch.')


def checked_basic_php_settings(values):
    """Return the nine basic PHP settings as (directive, value) pairs, or raise ValueError.

    Switches become On or Off. A size is digits with an optional sign and
    K, M or G; a time is digits with an optional sign. A value is therefore
    one word that can neither end its line nor start another directive.
    """
    settings = []
    for directive in BASIC_PHP_SETTINGS:
        value = values[directive]
        if directive in PHP_FLAGS:
            value = 'On' if php_flag(value) == '1' else 'Off'
        else:
            if type(value) is int:
                value = str(value)
            shape = PHP_SIZE_VALUE if directive in PHP_SIZES else PHP_SECONDS_VALUE
            if not isinstance(value, str) or shape.fullmatch(value) is None:
                raise ValueError('Invalid value for %s.' % directive)
        settings.append((directive, value))
    return settings


def apply_basic_php_settings(text, settings):
    """Return php.ini text with each setting assigned once per existing assignment.

    Only a line that assigns the directive is replaced; comments that merely
    mention it are kept. A directive the file does not assign is added at
    the end. Line endings of untouched lines are kept as they are.
    """
    found = set()
    lines = []
    for line in text.splitlines(True):
        for directive, value in settings:
            if matches_directive(line, directive):
                lines.append('%s = %s\n' % (directive, value))
                found.add(directive)
                break
        else:
            lines.append(line)
    missing = [(directive, value) for directive, value in settings if directive not in found]
    if missing:
        if lines and not lines[-1].endswith('\n'):
            lines.append('\n')
        lines.append('\n; Added by CyberPanel PHP Config Manager\n')
        for directive, value in missing:
            lines.append('%s = %s\n' % (directive, value))
    return ''.join(lines)


# The php.ini files the PHP settings pages manage: LiteSpeed PHP on the RPM
# family and on Debian or Ubuntu, Remi PHP-FPM, Debian or Ubuntu PHP-FPM.
MANAGED_INI = (
    re.compile(r'/usr/local/lsws/lsphp[0-9]{2,3}/etc/php\.ini'),
    re.compile(r'/usr/local/lsws/lsphp[0-9]{2,3}/etc/php/[0-9]\.[0-9]{1,2}/litespeed/php\.ini'),
    re.compile(r'/etc/opt/remi/php[0-9]{2,3}/php\.ini'),
    re.compile(r'/etc/php/[0-9]\.[0-9]{1,2}/fpm/php\.ini'),
)


def is_managed_ini(path):
    """True when the path has exactly the form of a php.ini the PHP settings pages manage."""
    return isinstance(path, str) and any(shape.fullmatch(path) is not None for shape in MANAGED_INI)


def managed_ini_path(selection, apache, rpm_family):
    """Return the php.ini of a PHP selection, built from the selection's digits.

    apache selects the PHP-FPM of the Apache backend instead of LiteSpeed PHP.
    """
    major, minor = php_selection_digits(selection)
    if not apache:
        if rpm_family:
            return '/usr/local/lsws/lsphp%s%s/etc/php.ini' % (major, minor)
        return '/usr/local/lsws/lsphp%s%s/etc/php/%s.%s/litespeed/php.ini' % (major, minor, major, minor)
    if rpm_family:
        return '/etc/opt/remi/php%s%s/php.ini' % (major, minor)
    return '/etc/php/%s.%s/fpm/php.ini' % (major, minor)


def fpm_service_for_ini(path):
    """Return the FPM service for a managed FPM ini; LSAPI needs no FPM restart."""
    remi = re.fullmatch(r'/etc/opt/remi/php([0-9]+)/php\.ini', path)
    if remi:
        return 'php%s-php-fpm' % remi.group(1)
    debian = re.fullmatch(r'/etc/php/([0-9]+\.[0-9]+)/fpm/php\.ini', path)
    if debian:
        return 'php%s-fpm' % debian.group(1)
    return None
