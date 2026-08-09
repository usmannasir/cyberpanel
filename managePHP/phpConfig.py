import re


def matches_directive(line, directive):
    """Return True when an INI line assigns the requested directive."""
    pattern = r'^\s*' + re.escape(directive) + r'\s*='
    return re.match(pattern, line, re.IGNORECASE) is not None
