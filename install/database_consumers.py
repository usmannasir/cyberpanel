"""Configuration helpers for services that connect to the panel database."""

import os
import re
import stat
import tempfile


class DatabaseConsumerConfigError(ValueError):
    """Raised when a database consumer endpoint cannot be represented safely."""


def _database_endpoint(host, port):
    host = '' if host is None else str(host).strip()
    if not host or any(character in host for character in ('\x00', '\n', '\r')):
        raise DatabaseConsumerConfigError('Database host is invalid')

    try:
        port = int(str(port).strip())
    except (TypeError, ValueError):
        raise DatabaseConsumerConfigError('Database port must be numeric')
    if port < 1 or port > 65535:
        raise DatabaseConsumerConfigError('Database port is out of range')
    return host, port


def dovecot_connect_line(password, mysql='One', remote=False, host=None,
                         port=None):
    """Render the legacy Dovecot SQL connection without losing remote mode."""
    if remote:
        host, port = _database_endpoint(host, port)
    elif mysql == 'Two':
        host, port = '127.0.0.1', 3307
    else:
        host, port = 'localhost', 3306

    return ('connect = host=%s dbname=cyberpanel user=cyberpanel '
            'password=%s port=%s\n' % (host, password, port))


def _php_single_quoted(value):
    """Quote a value as PHP without allowing variable interpolation."""
    return "'%s'" % str(value).replace('\\', '\\\\').replace("'", "\\'")


def render_phpmyadmin_signon(content, host, port):
    """Set phpMyAdmin's sign-on host and port in an existing PHP script."""
    host, port = _database_endpoint(host, port)
    host_line = (
        "        $_SESSION['PMA_single_signon_host'] = %s;"
        % _php_single_quoted(host)
    )
    port_line = "        $_SESSION['PMA_single_signon_port'] = %s;" % port

    host_pattern = re.compile(
        r"^[ \t]*\$_SESSION\['PMA_single_signon_host'\][ \t]*=.*?;[ \t]*$",
        re.MULTILINE,
    )
    port_pattern = re.compile(
        r"^[ \t]*\$_SESSION\['PMA_single_signon_port'\][ \t]*=.*?;[ \t]*$",
        re.MULTILINE,
    )

    # A callable replacement keeps backslashes in a quoted IPv6/hostname value
    # from being interpreted as regular-expression replacement escapes.
    content, host_replacements = host_pattern.subn(
        lambda unused_match: host_line, content, count=1)
    if host_replacements != 1:
        raise DatabaseConsumerConfigError(
            'phpMyAdmin sign-on host assignment was not found')

    if port_pattern.search(content):
        content = port_pattern.sub(
            lambda unused_match: port_line, content, count=1)
    else:
        content = content.replace(host_line, host_line + '\n' + port_line, 1)
    return content


def configure_phpmyadmin_signon(path, host, port):
    """Atomically update the fixed phpMyAdmin sign-on script."""
    if os.path.islink(path):
        raise DatabaseConsumerConfigError(
            'phpMyAdmin sign-on script must not be a symbolic link')

    source_stat = os.stat(path)
    if not stat.S_ISREG(source_stat.st_mode):
        raise DatabaseConsumerConfigError(
            'phpMyAdmin sign-on script must be a regular file')

    with open(path, 'r', encoding='utf-8') as source_file:
        rendered = render_phpmyadmin_signon(source_file.read(), host, port)

    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
                mode='w', encoding='utf-8', dir=os.path.dirname(path),
                prefix='.phpmyadmin-signin-', delete=False) as temporary_file:
            temporary_path = temporary_file.name
            temporary_file.write(rendered)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.chmod(temporary_path, stat.S_IMODE(source_stat.st_mode))
        os.chown(temporary_path, source_stat.st_uid, source_stat.st_gid)
        os.replace(temporary_path, path)
        temporary_path = None
    finally:
        if temporary_path and os.path.exists(temporary_path):
            os.unlink(temporary_path)
