"""Preserve the existing OLS config if listener mapping preparation fails."""
import os
import stat
import tempfile

from plogical.domainAliasUtilities import ensure_http_vhost_mapping


def update_http_listener_mappings(path, domain):
    with open(path) as source:
        metadata = os.fstat(source.fileno())
        original = source.read()
    updated = ensure_http_vhost_mapping(original, domain)
    if updated == original:
        return
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', dir=os.path.dirname(path),
                                         prefix='.http-map-', delete=False) as target:
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
