"""Read the public TXT value without exposing command errors as DNS records."""
import re


def parse_dkim_public_key(output):
    if not isinstance(output, str) or not output.strip():
        raise ValueError('DKIM public key is missing or unreadable; check OpenDKIM key generation.')
    # opendkim-genkey writes a DNS TXT record with one or more quoted chunks.
    # Some versions wrap those chunks in parentheses, others emit one line.
    chunks = re.findall(r'"([^"\\]*)"', output)
    value = ''.join(chunks).strip()
    if not value:
        value = output.strip()
    tags = {}
    for part in value.split(';'):
        if '=' in part:
            name, content = part.split('=', 1)
            tags[name.strip().lower()] = content.strip()
    if tags.get('v') != 'DKIM1' or not re.fullmatch(r'[A-Za-z0-9+/]+={0,2}', tags.get('p', '')):
        raise ValueError('DKIM public key is missing or invalid; check OpenDKIM key generation.')
    # Keep TXT syntax safe for the DNS backend, even if a file is corrupted.
    if any(character in value for character in ('"', '\\', '\n', '\r')):
        raise ValueError('DKIM public key contains invalid TXT content.')
    return value
