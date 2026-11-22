"""Preserve the existing OLS config if listener mapping preparation fails."""
import os
import stat
import tempfile

from plogical.domainAliasUtilities import ensure_http_vhost_mapping


def rewrite_config(path, transform):
    """Replace a configuration file with transform(its text) in one step.

    The file keeps its owner and mode, and is left untouched when the
    transform raises or changes nothing. Returns whether it was rewritten.
    """
    path = os.path.realpath(path)
    with open(path) as source:
        metadata = os.fstat(source.fileno())
        original = source.read()
    updated = transform(original)
    if updated == original:
        return False
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', dir=os.path.dirname(path),
                                         prefix='.config-', delete=False) as target:
            temporary = target.name
            target.write(updated)
            target.flush()
            os.fchmod(target.fileno(), stat.S_IMODE(metadata.st_mode))
            os.fchown(target.fileno(), metadata.st_uid, metadata.st_gid)
            os.fsync(target.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            os.unlink(temporary)
    return True


def update_http_listener_mappings(path, domain):
    rewrite_config(path, lambda config: ensure_http_vhost_mapping(config, domain))
