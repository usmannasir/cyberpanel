"""Download a release artifact with wget, replacing a stalled or trickling transfer.

wget has no minimum-speed option: a connection that delivers a few KB/s keeps
resetting its read timer and can hold an installation for hours. Each attempt
here is one wget process whose destination file is watched while it runs. The
first attempts must sustain a minimum rate and are dropped when they do not.
The last one may take any time and is dropped only when nothing arrives at
all, so a slow link still completes. wget's exit status decides success, and
no partial file is left behind.

Standard library only, and valid for the Python 3.6 of EL8.
"""
import collections
import os
import subprocess
import sys
import time
from urllib.parse import urlsplit


# (speed floor applies, extra wget arguments), tried in this order.
STEPS = (
    (True, ('--tries=1', '--timeout=30')),
    # A broken IPv6 route is a common reason for a transfer that crawls, and
    # the same hosts are already reached over IPv4 earlier in an installation.
    (True, ('--tries=1', '--timeout=30', '--inet4-only')),
    (False, ('--timeout=60',)),
)

# Host -> index of the step that last completed a download, so the remaining
# files of a bundle do not each rediscover the same slow route.
_proven = {}


class Policy(object):
    """Limits of one download; tests shorten them."""
    floor = 20480       # bytes per second a guarded attempt must sustain ...
    window = 60.0       # ... over this many trailing seconds
    first_byte = 45.0   # seconds a guarded attempt may deliver nothing
    stall = 300.0       # seconds the last attempt may make no progress
    poll = 1.0          # seconds between looks at the destination
    pause = 2.0         # seconds between attempts
    grace = 5.0         # seconds wget gets to exit after TERM, then after KILL

    def __init__(self, **limits):
        for name, value in limits.items():
            if not hasattr(Policy, name):
                raise TypeError('Unknown limit: %s' % name)
            setattr(self, name, value)


class _Watch(object):
    """Turns (time, size) observations of one attempt into a reason to stop it."""

    def __init__(self, guarded, policy, started):
        self.guarded = guarded
        self.policy = policy
        self.started = started
        self.samples = collections.deque()  # guarded: observations since the first byte
        self.size = 0                       # last attempt: last size seen ...
        self.changed = started              # ... and when it last changed

    def verdict(self, now, size):
        """None while the attempt may continue, else (reason, bytes per second)."""
        if size is None:
            return None
        if not self.guarded:
            # wget may restart the file on an internal retry; any change counts.
            if size != self.size:
                self.size, self.changed = size, now
            elif now - self.changed >= self.policy.stall:
                return ('stalled', 0.0)
            return None
        if not self.samples:
            if size > 0:
                self.samples.append((now, size))
            elif now - self.started >= self.policy.first_byte:
                return ('silent', 0.0)
            return None
        self.samples.append((now, size))
        # The reference is the newest observation that is a full window old.
        while len(self.samples) > 1 and now - self.samples[1][0] >= self.policy.window:
            self.samples.popleft()
        then, earlier = self.samples[0]
        if now - then >= self.policy.window:
            rate = (size - earlier) / float(now - then)
            if rate < self.policy.floor:
                return ('slow', rate)
        return None


def _size(path):
    try:
        return os.stat(path).st_size
    except FileNotFoundError:
        return 0
    except OSError:
        return None


def _remove(path):
    try:
        os.unlink(path)
    except OSError:
        pass


def _stop(process, grace):
    """Terminate wget and reap it. Returns its exit status, None if it survives."""
    for signal in (process.terminate, process.kill):
        try:
            signal()
        except OSError:
            pass
        try:
            return process.wait(timeout=grace)
        except subprocess.TimeoutExpired:
            continue
    return None


def _attempt(argv, destination, guarded, policy):
    """Run one wget. Returns None when it exited 0, otherwise (reason, detail)."""
    sys.stdout.flush()
    # Same session and terminal as the installer: wget keeps its progress bar
    # and still receives Ctrl-C.
    process = subprocess.Popen(argv)
    try:
        watch = _Watch(guarded, policy, time.monotonic())
        while True:
            try:
                status = process.wait(timeout=policy.poll)
            except subprocess.TimeoutExpired:
                status = None
            if status is not None:
                return None if status == 0 else ('exit', status)
            verdict = watch.verdict(time.monotonic(), _size(destination))
            if verdict:
                # It may have completed while this was being decided.
                return None if _stop(process, policy.grace) == 0 else verdict
    finally:
        if process.poll() is None:
            _stop(process, policy.grace)


def _explain(failure, policy, index, host):
    reason, detail = failure
    if reason == 'slow':
        what = 'Download too slow (%.1f KB/s over the last %g seconds)' % (
            detail / 1024.0, policy.window)
    elif reason == 'silent':
        what = 'No data received in %g seconds' % policy.first_byte
    elif reason == 'stalled':
        what = 'No data received for %g seconds' % policy.stall
    else:
        what = 'wget stopped with exit code %s' % detail
    if index + 1 == len(STEPS):
        return "ERROR: %s; download failed. Check this server's connection to %s." % (what, host)
    guarded, flags = STEPS[index + 1]
    if guarded:
        return 'WARNING: %s; retrying on a new connection%s.' % (
            what, ' over IPv4' if '--inet4-only' in flags else '')
    return ("WARNING: %s; continuing without a speed limit for as long as data keeps arriving. "
            "This can take a long time; check this server's connection to %s if it does "
            "not finish." % (what, host))


def _say(message):
    print(message)
    sys.stdout.flush()


def fetch(url, destination, notify=None, policy=None):
    """Download URL to DESTINATION. True only when wget exited successfully.

    NOTIFY receives one line per attempt and per replaced attempt. The caller
    still has to verify the content; this only guarantees a complete transfer.
    """
    notify = notify or _say
    policy = policy or Policy()
    host = urlsplit(url).netloc
    first = _proven.get(host, 0)
    for index in range(first, len(STEPS)):
        guarded, flags = STEPS[index]
        if index > first:
            time.sleep(policy.pause)
        _remove(destination)
        argv = ['wget', '-q', '--show-progress'] + list(flags) + ['-O', destination, '--', url]
        notify('Running: %s' % ' '.join(argv))
        failure = _attempt(argv, destination, guarded, policy)
        if failure is None:
            _proven[host] = index
            return True
        notify(_explain(failure, policy, index, host))
    _remove(destination)
    return False
