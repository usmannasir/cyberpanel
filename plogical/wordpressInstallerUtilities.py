import re
import shlex


WORDPRESS_VERSION = re.compile(r'^\d+\.\d+(?:\.\d+)?$')


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
