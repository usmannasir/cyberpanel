import os
import re
import shlex

from managePHP.phpConfig import php_selection_digits


WORDPRESS_VERSION = re.compile(r'^\d+\.\d+(?:\.\d+)?$')
WORDPRESS_ITEM_NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{0,199}')


def select_wordpress_version(offers):
    """Return the first valid release advertised by the WordPress API."""
    for offer in offers or ():
        if not isinstance(offer, dict):
            continue
        version = str(offer.get('current', '')).strip()
        if WORDPRESS_VERSION.fullmatch(version):
            return version
    raise ValueError('The WordPress API did not return a valid release.')


def wordpress_php_change_required(current_binary, required_binary):
    """Avoid restarting the web server when WordPress already uses the target PHP."""
    current = os.path.normpath(str(current_binary or ''))
    required = os.path.normpath(str(required_binary or ''))
    return not current or current != required


def php_binary_for_selection(selection):
    """Map a panel PHP selection to its exact LiteSpeed PHP CLI binary.

    The selection must be exactly 'PHP x.y' (managePHP.phpConfig holds the
    one check); the path is built from its digits.
    """
    return '/usr/local/lsws/lsphp%s%s/bin/php' % php_selection_digits(selection)


def change_php_succeeded(output):
    """Only accept the explicit success record printed by changePHP."""
    return any(line.strip() == '1,None' for line in str(output or '').splitlines())


def build_directory_probe(path):
    """Build a bounded probe that emits one byte per top-level entry."""
    return (
        'find %s -mindepth 1 -maxdepth 1 -printf x | head -c 4'
        % shlex.quote(path)
    )


def directory_allows_install(command_succeeded, output, maximum_entries=3):
    """Fail closed if a website directory cannot be inspected safely."""
    if not command_succeeded or not isinstance(output, str):
        return False
    return len(output) <= maximum_entries


def build_wordpress_core_install_command(version, destination, php_binary):
    """Download, extract, and checksum a selected WordPress release."""
    version = str(version).strip()
    if WORDPRESS_VERSION.fullmatch(version) is None:
        raise ValueError('Invalid WordPress version selected.')

    archive_url = 'https://wordpress.org/wordpress-%s.tar.gz' % version
    php_binary = shlex.quote(php_binary)
    destination = shlex.quote(destination)

    return (
        "archive=$(mktemp /tmp/cyberpanel-wordpress.XXXXXX.tar.gz) || exit 1; "
        "trap 'rm -f \"$archive\"' EXIT; "
        "curl -fsSL --retry 3 --connect-timeout 20 %s -o \"$archive\" && "
        "tar -xzf \"$archive\" --strip-components=1 --no-same-owner "
        "--no-same-permissions -C %s && "
        "%s -d error_reporting=0 /usr/bin/wp core verify-checksums "
        "--version=%s --path=%s && "
        "echo 'Success: WordPress downloaded and verified.'"
    ) % (
        shlex.quote(archive_url),
        destination,
        php_binary,
        shlex.quote(version),
        destination,
    )


def build_wordpress_config_command(php_binary, destination, database, user, password, host):
    """Preserve each configuration value as a single literal WP-CLI argument."""
    arguments = [php_binary, '-d', 'error_reporting=0', '/usr/bin/wp', 'core', 'config',
                 '--dbname=' + database, '--dbuser=' + user, '--dbpass=' + password,
                 '--dbhost=' + host, '--dbprefix=wp_', '--path=' + destination]
    return ' '.join(shlex.quote(str(argument)) for argument in arguments)


def build_wordpress_site_install_command(php_binary, destination, url, title, user, password, email):
    """Quote every site field before the existing shell execution boundary."""
    arguments = [php_binary, '-d', 'error_reporting=0', '/usr/bin/wp', 'core', 'install',
                 '--url=' + url, '--title=' + title, '--admin_user=' + user,
                 '--admin_password=' + password, '--admin_email=' + email,
                 '--path=' + destination]
    return ' '.join(shlex.quote(str(argument)) for argument in arguments)


def wrap_wordpress_site_shell_script(script):
    """Keep a complete multi-command script beneath the site's sudo boundary."""
    return 'sh -c ' + shlex.quote(script)


def build_wordpress_config_password_command(php_binary, destination, password):
    """Use config-set's PHP literal serialization after config-create's escaping."""
    arguments = [php_binary, '-d', 'error_reporting=0', '/usr/bin/wp',
                 'config', 'set', 'DB_PASSWORD', password, '--type=constant',
                 '--path=' + destination]
    return ' '.join(shlex.quote(str(argument)) for argument in arguments)


def wordpress_item_names(*values):
    """Whether every value is a plugin or theme name, or a list of such names.

    The values come from the browser and are written onto a WP-CLI command
    line, so only plain names ('akismet', 'twentytwentyfive', also the words
    'all' and 'selected') are ever passed on.
    """
    for value in values:
        names = value if isinstance(value, list) else [value]
        for name in names:
            if not isinstance(name, str) or WORDPRESS_ITEM_NAME.fullmatch(name) is None:
                return False
    return True


def wordpress_config_set_command(php_binary, path, key, value):
    """The WP-CLI command that sets one database constant in a site's wp-config.php.

    Run it as the site's own user. The value is read from a file the customer
    can edit, so it reaches the command only as one quoted argument.
    """
    if key not in ('DB_NAME', 'DB_USER', 'DB_PASSWORD'):
        raise ValueError('Unsupported WordPress configuration constant.')
    if not isinstance(value, str) or not isinstance(path, str) or not isinstance(php_binary, str):
        raise ValueError('Invalid WordPress configuration value.')
    return ('%s -d error_reporting=0 -d memory_limit=350M -d max_execution_time=400 /usr/bin/wp '
            'config set %s %s --skip-plugins --skip-themes --path=%s') % (
        shlex.quote(php_binary), key, shlex.quote(value), shlex.quote(path))
