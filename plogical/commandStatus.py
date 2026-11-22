"""Learn how a command ended when the privileged helper runs it.

The helper answers with the command's output followed by one byte, and that
byte does not tell an exit status of 0 from any other. A command whose result
matters is therefore run in a subshell, and the shell prints a trailer after
it: a newline, a marker made for this one call, and the status. Whatever the
command itself prints, it cannot know the marker, and only the very end of
the reply is read as the trailer.
"""
import re
import secrets
import shlex


# The helper takes a request of at most this many bytes: its token, the
# account and the command together. A longer one is dropped without an answer.
REQUEST_LIMIT = 1023
# The helper's token is this long; used where a request is measured before
# the token is at hand.
TOKEN_LENGTH = 32
MARKER = re.compile(r'[0-9a-f]{32}\Z')


def new_marker():
    return secrets.token_hex(16)


def with_status(command, marker):
    """The command line that runs `command` in a subshell and then prints the trailer."""
    if not isinstance(command, str) or '\x00' in command or MARKER.match(marker) is None:
        raise ValueError('not a command')
    return "(eval %s);printf '\\n%s %%d' $?" % (shlex.quote(command), marker)


def helper_request(token, user, command, marker):
    """The bytes to send to the helper, or None when they are more than it takes."""
    request = ('%s-u %s %s' % (token, user, with_status(command, marker))).encode('utf-8')
    return request if len(request) <= REQUEST_LIMIT else None


def request_fits(user, command):
    """Whether the helper would take this command for this account."""
    try:
        return helper_request('t' * TOKEN_LENGTH, user, command, '0' * 32) is not None
    except (ValueError, UnicodeError):
        return False


class StatusReader(object):
    """Pass a helper's reply on to a sink as it arrives and keep the trailer back."""

    def __init__(self, marker, sink):
        self.sink = sink
        # After the trailer comes the helper's own last byte, 0 when the shell ended by itself.
        self.trailer = re.compile(b'\n' + marker.encode('ascii') + b' ([0-9]{1,3})\x00\\Z')
        self.longest = len(marker) + 6
        self.held = b''

    def feed(self, data):
        data = self.held + data
        if len(data) > self.longest:
            self.sink.write(data[:-self.longest])
        self.held = data[-self.longest:]

    def finish(self):
        """Pass on the output held back; return the command's exit status, or None when none was reported."""
        found = self.trailer.search(self.held)
        output = self.held[:found.start()] if found else self.held[:-1]
        self.held = b''
        if output:
            self.sink.write(output)
        return int(found.group(1)) if found else None
