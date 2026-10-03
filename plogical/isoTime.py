"""ISO 8601 parsing that also works on Python 3.6 panels (AlmaLinux/CloudLinux 8).

datetime.fromisoformat() only exists from Python 3.7, and Python 3.6's
strptime() %z does not accept a colon in the UTC offset.
"""
from datetime import datetime

_FORMATS = (
    '%Y-%m-%dT%H:%M:%S.%f%z', '%Y-%m-%dT%H:%M:%S%z',
    '%Y-%m-%d %H:%M:%S.%f%z', '%Y-%m-%d %H:%M:%S%z',
    '%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S',
    '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S',
    '%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M', '%Y-%m-%d',
)


def parse_iso_datetime(value, _native=True):
    """Parse the output of datetime.isoformat(); raises TypeError/ValueError like fromisoformat()."""
    if _native and hasattr(datetime, 'fromisoformat'):
        return datetime.fromisoformat(value)
    if not isinstance(value, str):
        raise TypeError('fromisoformat: argument must be str')
    text = value
    if len(text) > 6 and text[-6] in '+-' and text[-3] == ':':
        text = text[:-3] + text[-2:]
    for fmt in _FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError('Invalid isoformat string: %r' % (value,))
