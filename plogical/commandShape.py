"""Tell whether a shell would run exactly one command from a command line.

The privileged helper hands every command line to a shell. A command that
starts by switching to a website's account is meant to run one program as
that account; if a value written into it ends that command, the shell runs
whatever follows with the helper's own privilege.
"""

STDERR_DISCARD = ' 2>/dev/null'


def runs_one_command(command):
    """True when the shell would run one simple command and nothing else.

    Quoting is followed the way the shell follows it, so separators inside
    quotes are ordinary text. Discarding error output at the end of the line
    is the one redirection accepted.
    """
    if not isinstance(command, str) or any(char in command for char in '\n\r\x00'):
        return False
    text = command.rstrip()
    if text.endswith(STDERR_DISCARD):
        text = text[:-len(STDERR_DISCARD)]

    quote = None
    index = 0
    while index < len(text):
        char = text[index]
        if quote == "'":
            if char == "'":
                quote = None
        elif char == '\\':
            index += 1
            if index >= len(text):
                return False
        elif char == '`' or text.startswith('$(', index):
            return False
        elif quote == '"':
            if char == '"':
                quote = None
        elif char in '\'"':
            quote = char
        elif char in ';&|<>()':
            return False
        index += 1
    return quote is None
