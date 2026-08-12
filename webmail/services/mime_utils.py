"""Safe decoding helpers for untrusted MIME headers and message bodies."""

from email.header import decode_header


def decode_mime_bytes(value, charset=None):
    """Decode MIME bytes without trusting a sender-supplied charset label."""
    if not value:
        return ''

    declared_charset = str(charset or 'utf-8').strip() or 'utf-8'
    for candidate in (declared_charset, 'utf-8', 'latin-1'):
        try:
            return value.decode(candidate, errors='replace')
        except (LookupError, UnicodeError):
            continue

    return value.decode('utf-8', errors='replace')


def decode_mime_header(value):
    """Decode a MIME header while tolerating invalid encoded-word charsets."""
    if value is None:
        return ''

    try:
        decoded_parts = decode_header(value)
    except (TypeError, ValueError):
        return decode_mime_bytes(value) if isinstance(value, bytes) else str(value)

    result = []
    for part, charset in decoded_parts:
        if isinstance(part, bytes):
            result.append(decode_mime_bytes(part, charset))
        else:
            result.append(part)
    return ''.join(result)
