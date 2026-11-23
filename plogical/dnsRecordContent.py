"""Content of the DNS records whose priority is kept apart from it.

PowerDNS serves an MX or SRV record as the ``prio`` column of its ``records`` table followed by
the ``content`` column. The content of such a record is therefore what comes after the priority:
the mail host of an MX record, and weight, port and target of an SRV record. A content that
repeats the priority gives a record PowerDNS cannot serve.
"""
import re

_NUMBER = re.compile(r'[0-9]{1,5}')
_LABEL = re.compile(r'[A-Za-z0-9_-]{1,63}')
_HIGHEST = 65535

PRIORITY_EXPECTED = 'Priority must be a whole number from 0 to 65535.'
SRV_EXPECTED = ('An SRV record takes weight, port and target as its content, for example '
                '"5 5060 sip.example.com". The priority goes in the Priority field only.')
MX_EXPECTED = ('An MX record takes the mail host as its content, for example "mail.example.com". '
               'The priority goes in the Priority field only.')


def record_priority(value):
    """The priority of an MX or SRV record as a number, however the request spelled it."""
    if isinstance(value, str) and _NUMBER.fullmatch(value.strip()):
        value = int(value.strip())
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= _HIGHEST:
        raise ValueError(PRIORITY_EXPECTED)
    return value


def _words(content):
    return content.split() if isinstance(content, str) else []


def _without_repeated_priority(words, length, priority, expected):
    """Drop a leading priority from a content that states the whole record.

    A content one number longer than the record takes can only be the record written out in
    full, priority first. Where that number is the priority of the Priority field there is one
    record that can be meant, and it is stored. Where the two differ nothing says which of them
    is meant, so the record is refused.
    """
    if len(words) != length + 1 or not all(_NUMBER.fullmatch(word) for word in words[:length]):
        return words
    if int(words[0]) != priority:
        raise ValueError('The content begins with the priority %s, but the Priority field holds %s. %s'
                         % (words[0], priority, expected))
    return words[1:]


def _number(word, name):
    if not _NUMBER.fullmatch(word) or int(word) > _HIGHEST:
        raise ValueError('%s must be a whole number from 0 to 65535. %s' % (name, SRV_EXPECTED))
    return int(word)


def _target(word):
    """The target the way the panel stores host names: without the dot that ends a full name."""
    if word == '.':
        # RFC 2782: the service is not available at this domain.
        return word
    name = word[:-1] if word.endswith('.') else word
    if len(name) > 253 or not all(_LABEL.fullmatch(label) for label in name.split('.')):
        raise ValueError('Target must be a host name such as sip.example.com, or a single dot '
                         'where the service is not offered. %s' % SRV_EXPECTED)
    return name


def srv_record_content(content, priority):
    """Weight, port and target of an SRV record, as stored beside its priority."""
    words = _without_repeated_priority(_words(content), 3, priority, SRV_EXPECTED)
    if len(words) != 3:
        raise ValueError(SRV_EXPECTED)
    return '%d %d %s' % (_number(words[0], 'Weight'), _number(words[1], 'Port'), _target(words[2]))


def mx_record_content(content, priority):
    """The mail host of an MX record, as stored beside its priority."""
    words = _without_repeated_priority(_words(content), 1, priority, MX_EXPECTED)
    if len(words) != 1:
        raise ValueError(MX_EXPECTED)
    return words[0]
