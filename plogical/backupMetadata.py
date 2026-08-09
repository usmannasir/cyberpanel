def backup_includes_mail_domain(metadata, master_domain):
    expected_domain = 'mail.%s' % master_domain
    for child_domain in metadata.findall('ChildDomains/domain'):
        if child_domain.findtext('domain') == expected_domain:
            return True
    return False
