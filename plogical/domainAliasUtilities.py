import re


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
    mapped = False

    def update_listener(match):
        nonlocal mapped
        block = match.group(0)
        if re.search(r'^\s*secure\s+1(?:\s|$)', block, re.MULTILINE):
            return block
        lines = block.splitlines(keepends=True)
        for index, line in enumerate(lines):
            directive, marker, comment = line.partition('#')
            parts = directive.split(None, 2)
            if len(parts) != 3 or parts[0] != 'map' or parts[1] != master_domain:
                continue
            mapped = True
            domains = [item for item in re.split(r'[,\s]+', parts[2].strip()) if item]
            if alias_domain in domains:
                continue
            ending = '\n' if line.endswith('\n') else ''
            suffix = ('  #' + comment.rstrip('\r\n')) if marker else ''
            lines[index] = '  map                     ' + master_domain + ' ' + ', '.join(domains + [alias_domain]) + suffix + ending
        return ''.join(lines)

    updated = re.sub(
        r'^\s*listener\s+[^\n{]+\{[^{}]*^\s*}',
        update_listener, config, flags=re.MULTILINE,
    )
    if not mapped:
        raise ValueError('Parent domain has no HTTP listener mapping; alias was not created.')
    return updated
