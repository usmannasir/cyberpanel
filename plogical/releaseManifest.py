"""The signed release file trusted by a server that updates itself.

A server that installs updates on its own must not take "whatever the release
branch points at today": anyone able to move that branch, or to change the page
naming the latest version, could then run code as root on every such server.
CyberPanel signs a small file naming one exact commit. The keys below are the
only ones accepted, and only the commit a verified file names is installed.

The file is {"release": "<JSON text>", "signatures": [{"key": id, "signature": base64}]}.
The signature covers the exact release text, so nothing is parsed before it
has been verified.
"""
import base64
import calendar
import hashlib
import json
import re
import time

URL = 'https://cyberpanel.net/release.json'
PREFIX = b'cyberpanel-release-v1\n'
LIMIT = 16 * 1024
MAXIMUM_HOURS = 336
# Raw Ed25519 public keys. The second is a spare kept apart from the first,
# so a lost or exposed key can be retired by an ordinary release.
PUBLISHERS = (
    'sSvlWEM0f9pDSf3HsPaQn1U/N5wCzujVYLvfWXPykgg=',
    '6i7RbsOTN7ZlzSNJgiIaz2vD31cb9S4ctyhMeZ+oQKk=',
)
FIELDS = ('schema', 'sequence', 'version', 'build', 'branch', 'commit', 'published',
          'soak_hours', 'spread_hours', 'hold')


class Unverified(ValueError):
    """The file is not a release signed by CyberPanel."""


class Unavailable(RuntimeError):
    """This system cannot check signatures, so nothing can be trusted."""


def key_id(public):
    return hashlib.sha256(public).hexdigest()[:16]


def _signed_by(public, signature, message):
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    except ImportError:
        raise Unavailable('The signature library is missing.')
    try:
        Ed25519PublicKey.from_public_bytes(public).verify(signature, message)
        return True
    except InvalidSignature:
        return False
    except Exception as error:
        # For example a system in FIPS mode, where Ed25519 is switched off.
        raise Unavailable('Release signatures cannot be checked here: %s' % type(error).__name__)


def _whole(value, low, high):
    return isinstance(value, int) and not isinstance(value, bool) and low <= value <= high


def published_time(release):
    """Seconds since the epoch at which the release was signed (UTC)."""
    return calendar.timegm(time.strptime(release['published'], '%Y-%m-%dT%H:%M:%SZ'))


def _checked(release):
    if not isinstance(release, dict) or sorted(release) != sorted(FIELDS):
        raise Unverified('The release has unexpected fields.')
    version, build = release['version'], release['build']
    valid = (
        _whole(release['schema'], 1, 1)
        and _whole(release['sequence'], 1, 2 ** 31)
        and isinstance(version, str) and re.fullmatch(r'[0-9]{1,4}(?:\.[0-9]{1,4}){1,3}', version)
        and _whole(build, 0, 99999)
        and release['branch'] == 'v%s.%s' % (version, build)
        and isinstance(release['commit'], str) and re.fullmatch(r'[0-9a-f]{40}', release['commit'])
        and isinstance(release['published'], str)
        and re.fullmatch(r'20[0-9]{2}-[01][0-9]-[0-3][0-9]T[0-2][0-9]:[0-5][0-9]:[0-5][0-9]Z', release['published'])
        and _whole(release['soak_hours'], 0, MAXIMUM_HOURS)
        and _whole(release['spread_hours'], 0, MAXIMUM_HOURS)
        and isinstance(release['hold'], bool)
    )
    if not valid:
        raise Unverified('The release has an unexpected value.')
    try:
        published_time(release)
    except ValueError:
        raise Unverified('The release has an impossible date.')
    return release


def verified(document, publishers=PUBLISHERS):
    """The release a published file names. Unverified unless CyberPanel signed it."""
    if not isinstance(document, bytes) or len(document) > LIMIT:
        raise Unverified('The release file is not the expected size.')
    try:
        outer = json.loads(document.decode('utf-8'))
        text, signatures = outer['release'], outer['signatures']
        if not isinstance(text, str) or not isinstance(signatures, list) or len(signatures) > 4:
            raise ValueError
        message = PREFIX + text.encode('utf-8')
        trusted = {key_id(public): public for public in (base64.b64decode(key) for key in publishers)}
        signed = False
        for entry in signatures:
            public = trusted.get(entry['key'])
            signature = base64.b64decode(entry['signature'], validate=True)
            if public is not None and len(signature) == 64 and _signed_by(public, signature, message):
                signed = True
                break
    except (ValueError, KeyError, TypeError, AttributeError):
        signed = False
    if not signed:
        raise Unverified('The release file is not signed by CyberPanel.')
    try:
        release = json.loads(text)
    except ValueError:
        raise Unverified('The signed release is not readable.')
    return _checked(release)


def order(version, build):
    """Sortable form of a version and build, for "is this newer"."""
    return tuple(int(part) for part in str(version).split('.')) + (int(build),)


def fetch(url=URL):
    from plogical.panelWorkerBuild import download
    return download(url, limit=LIMIT, timeout=30)
