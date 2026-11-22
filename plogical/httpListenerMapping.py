"""Preserve the existing OLS config if listener mapping preparation fails."""
import contextlib
import fcntl
import os
import stat
import tempfile
import time

from plogical.domainAliasUtilities import ensure_http_vhost_mapping

# How long a rewrite waits for another rewrite of the same file, in seconds.
LOCK_WAIT = 30


def read_config(path):
    """A configuration file as text that encodes back to exactly the bytes read.

    Line endings are kept as they are and a byte that is not UTF-8 survives
    as an escape, so reading never fails on the content of the file.
    """
    with open(path, 'rb') as source:
        return source.read().decode('utf-8', 'surrogateescape')


@contextlib.contextmanager
def config_lock(path, wait=None):
    """Hold the lock that orders rewrites of one configuration file.

    The lock is a file beside the configuration that is never removed. It is
    waited for at most `wait` seconds (LOCK_WAIT unless given); after that
    TimeoutError is raised and the caller has changed nothing.
    """
    wait = LOCK_WAIT if wait is None else wait
    name = os.path.join(os.path.dirname(path), '.' + os.path.basename(path) + '.lock')
    descriptor = os.open(name, os.O_RDWR | os.O_CREAT | getattr(os, 'O_CLOEXEC', 0), 0o600)
    try:
        deadline = time.monotonic() + wait
        while True:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise TimeoutError('%s is being changed by another operation; gave up after %s seconds'
                                       % (path, wait))
                time.sleep(0.1)
        yield
    finally:
        os.close(descriptor)


def rewrite_config(path, transform, wait=None):
    """Replace a configuration file with transform(its text) in one step.

    Reading, transforming and replacing happen under the file's lock, so two
    rewrites of one file follow each other and neither loses the other's
    change. The transform gets the text as it is in the file at that moment.
    The file keeps its owner and mode and every byte the transform did not
    change, and is left untouched when the transform raises, changes nothing
    or the lock is not obtained in time. Returns whether it was rewritten.
    """
    path = os.path.realpath(path)
    with config_lock(path, wait):
        with open(path, 'rb') as source:
            metadata = os.fstat(source.fileno())
            original = source.read().decode('utf-8', 'surrogateescape')
        updated = transform(original)
        if updated == original:
            return False
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='wb', dir=os.path.dirname(path),
                                             prefix='.config-', delete=False) as target:
                temporary = target.name
                target.write(updated.encode('utf-8', 'surrogateescape'))
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
