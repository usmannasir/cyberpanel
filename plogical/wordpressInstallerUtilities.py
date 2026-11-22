import os
import re
import shlex

from managePHP.phpConfig import php_selection_digits


WORDPRESS_VERSION = re.compile(r'^\d+\.\d+(?:\.\d+)?$')
WORDPRESS_ITEM_NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{0,199}')
WORDPRESS_RELEASES_URL = 'https://api.wordpress.org/core/version-check/1.7/'
WORDPRESS_TABLE_PREFIX = re.compile(r'[A-Za-z0-9_]{1,64}')


def select_wordpress_version(offers):
    """Return the first valid release advertised by the WordPress API."""
    for offer in offers or ():
        if not isinstance(offer, dict):
            continue
        version = str(offer.get('current', '')).strip()
        if WORDPRESS_VERSION.fullmatch(version):
            return version
    raise ValueError('The WordPress API did not return a valid release.')


def current_wordpress_version(fetch):
    """Ask WordPress.org which release is current ('7.0.2').

    fetch is requests.get. An answer without a valid release raises
    ValueError; a failed request raises what fetch raises.
    """
    response = fetch(WORDPRESS_RELEASES_URL, timeout=15)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise ValueError('Invalid WordPress API response.')
    return select_wordpress_version(data.get('offers', []))


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


def build_directory_listing_command(path):
    """Print the name of every entry directly inside a directory, one per line."""
    return 'find %s -mindepth 1 -maxdepth 1 -printf %s' % (shlex.quote(path), shlex.quote('%f\\n'))


def directory_entry_names(command_succeeded, output):
    """The names a listing printed, or None when the directory could not be read."""
    if not command_succeeded or not isinstance(output, str):
        return None
    return set(line for line in output.split('\n') if line)


def entries_added_since(before, after):
    """The names a job added to a directory: there now, not there when it started.

    Both are sets from directory_entry_names. Without a reading from before
    the job, or of the directory as it is now, nothing counts as added, so
    nothing is ever removed on a guess.
    """
    if before is None or after is None:
        return []
    return sorted(name for name in after - before if name not in ('.', '..') and '/' not in name)


def build_entry_removal_command(directory, name):
    """Remove one entry of a directory; its name is never read as an option or as a path."""
    if not isinstance(name, str) or not name or name in ('.', '..') or '/' in name or '\x00' in name:
        raise ValueError('Invalid directory entry.')
    return 'rm -rf -- %s' % shlex.quote(os.path.join(directory, name))


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


def wordpress_cli_command(php_binary, path, *arguments):
    """A WP-CLI command for one site that loads none of its plugins and themes.

    Run it as the site's own user. Every word is quoted, so a value read
    from a backup or from a site's files stays one argument.
    """
    words = [php_binary, '-d', 'error_reporting=0', '-d', 'memory_limit=350M', '-d', 'max_execution_time=400',
             '/usr/bin/wp']
    words.extend(arguments)
    words.extend(['--skip-plugins', '--skip-themes', '--path=' + path])
    return ' '.join(shlex.quote(str(word)) for word in words)


def wordpress_table_prefix_command(php_binary, path, prefix):
    """The WP-CLI command that sets the table prefix in a site's wp-config.php."""
    if not isinstance(prefix, str) or WORDPRESS_TABLE_PREFIX.fullmatch(prefix) is None:
        raise ValueError('Invalid WordPress table prefix.')
    return wordpress_cli_command(php_binary, path, 'config', 'set', 'table_prefix', prefix, '--type=variable')


def single_line_value(output):
    """One value printed by a command: its only line. Anything else raises ValueError.

    A value is written back into a site's configuration, so output that
    carries a warning or an error beside it is refused instead of stored.
    """
    text = str(output if output is not None else '').rstrip('\n')
    if not text or '\n' in text or '\r' in text:
        raise ValueError('The command did not print a single value.')
    return text


def brief_output(output, limit=300):
    """What a command printed, as one line of at most `limit` characters for a status message.

    The end is kept: that is where a command says why it stopped.
    """
    text = ' '.join(str(output if output is not None else '').split())
    if len(text) > limit:
        text = '... ' + text[-limit:]
    return text


def worker_failure_reason(status):
    """The reason in the last status of a worker that failed: one line, without the end marker.

    A status file ends with a line break and its marker. Put into another
    status as it is, the reason would end up on a line of its own and the
    last line, the one that is shown, would hold the marker alone.
    """
    return brief_output(str(status or '').replace('[404]', ' ')).rstrip('. ') or 'no reason was given'


def out_of_quota(output):
    """Whether a command stopped because the account's disk quota is used up."""
    return 'Disk quota exceeded' in str(output or '')


# How the database client reports a statement it could not run:
# "ERROR 1064 (42000) at line 1 in file: ...", at the start of a line.
DATABASE_CLIENT_ERROR = re.compile(r'^ERROR [0-9]+ \([0-9A-Za-z]+\).*$', re.MULTILINE)


def database_client_error(output):
    """The first error the database client reported in what an import printed, or None.

    An import through WP-CLI goes on after a statement fails, ends with
    "Success" and exits with status 0: the client's own error line is the
    only sign that the dump was not imported as it is.
    """
    found = DATABASE_CLIENT_ERROR.search(str(output if output is not None else ''))
    return brief_output(found.group(0)) if found is not None else None
