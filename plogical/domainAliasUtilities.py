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
