import re


_LISTENER_PATTERN = r'^\s*listener\s+[^\n{]+\{[^{}]*^\s*}'


def _is_secure_listener(block):
    return bool(re.search(r'^\s*secure\s+1(?:\s|$)', block, re.MULTILINE))


def has_https_listener(config, ipv6=False):
    for match in re.finditer(_LISTENER_PATTERN, config, flags=re.MULTILINE):
        block = match.group(0)
        if _is_secure_listener(block) and (
                not ipv6 or re.search(r'^\s*address\s+\[', block, re.MULTILINE)):
            return True
    return False


def ensure_https_vhost_mapping(config, master_domain):
    """Ensure every existing secure listener routes the parent vhost."""
    return _add_alias_mapping(config, master_domain, master_domain, secure=True, create_missing=True)


def merge_alias_names(current_aliases, legacy_aliases):
    aliases = []
    seen = set()
    for alias in list(current_aliases) + list(legacy_aliases):
        if alias and alias not in seen:
            aliases.append(alias)
            seen.add(alias)
    return aliases


def remove_alias_from_map_line(line, master_domain, alias_domain):
    stripped = line.lstrip()
    parts = stripped.split(None, 2)
    if len(parts) != 3 or parts[0] != 'map' or parts[1] != master_domain:
        return line

    domains = [domain.strip() for domain in parts[2].strip().split(',') if domain.strip()]
    filtered = [domain for domain in domains if domain != alias_domain]
    if filtered == domains:
        return line

    indentation = line[:len(line) - len(stripped)]
    newline = '\n' if line.endswith('\n') else ''
    return '%smap                     %s %s%s' % (
        indentation,
        master_domain,
        ', '.join(filtered),
        newline,
    )


def add_http_alias_mapping(config, master_domain, alias_domain):
    """Add an alias to every non-TLS listener serving the exact parent vhost."""
    return _add_alias_mapping(config, master_domain, alias_domain, secure=False)


def add_https_alias_mapping(config, master_domain, alias_domain):
    """Add an alias to every TLS listener serving the exact parent vhost."""
    return _add_alias_mapping(config, master_domain, alias_domain, secure=True)


def _add_alias_mapping(config, master_domain, alias_domain, secure, create_missing=False):
    mapped = False

    def update_listener(match):
        nonlocal mapped
        block = match.group(0)
        is_secure = _is_secure_listener(block)
        if is_secure != secure:
            return block
        lines = block.splitlines(keepends=True)
        parent_found = False
        for index, line in enumerate(lines):
            directive, marker, comment = line.partition('#')
            parts = directive.split(None, 2)
            if len(parts) != 3 or parts[0] != 'map' or parts[1] != master_domain:
                continue
            mapped = True
            parent_found = True
            domains = [item for item in re.split(r'[,\s]+', parts[2].strip()) if item]
            if alias_domain in domains:
                continue
            ending = '\n' if line.endswith('\n') else ''
            suffix = ('  #' + comment.rstrip('\r\n')) if marker else ''
            lines[index] = '  map                     ' + master_domain + ' ' + ', '.join(domains + [alias_domain]) + suffix + ending
        if create_missing and not parent_found:
            lines.insert(len(lines) - 1, '  map                     %s %s\n' % (master_domain, master_domain))
            mapped = True
        return ''.join(lines)

    updated = re.sub(
        _LISTENER_PATTERN,
        update_listener, config, flags=re.MULTILINE,
    )
    if not mapped:
        protocol = 'HTTPS' if secure else 'HTTP'
        raise ValueError('Parent domain has no %s listener mapping; alias was not created.' % protocol)
    return updated
