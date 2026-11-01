"""Backward-compatible independent child state in backup metadata."""


def normalize_child_state(value=None):
    # Older backups do not have independent suspension metadata.
    if value is None:
        return 1
    if type(value) is int and value == 0 or type(value) is str and value == '0':
        return 0
    if type(value) is int and value == 1 or type(value) is str and value == '1':
        return 1
    raise ValueError('Invalid independent child-domain state in backup metadata.')


def child_backup_record(child):
    return {'domain': child.domain, 'path': child.path, 'php': child.phpSelection,
            'state': normalize_child_state(child.state)}


def append_child_backup_xml(parent, child):
    from xml.etree.ElementTree import SubElement
    record = child_backup_record(child)
    element = SubElement(parent, 'domain')
    for tag, key in (('domain', 'domain'), ('phpSelection', 'php'),
                     ('path', 'path'), ('state', 'state')):
        SubElement(element, tag).text = str(record[key])
    return element
