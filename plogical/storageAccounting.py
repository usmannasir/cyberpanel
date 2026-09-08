"""Read-only accounting for a website and its explicitly owned mail domains."""
import os
import stat
import subprocess


HOME_ROOT = '/home'
MAIL_ROOT = '/home/vmail'
MEBIBYTE = 1024 * 1024


class StorageAccountingError(Exception):
    pass


def _component(value):
    if (not isinstance(value, str) or not value or value in ('.', '..')
            or any(character in value for character in ('/', '\\', '\x00', '\n', '\r', '\t'))):
        raise StorageAccountingError('Invalid storage path component')
    return value


def owned_mail_domains(website):
    """Return direct and child mail domains with consistent database ownership.

    Directory names alone do not establish ownership. In particular, leftover
    directories without a Domains record are not attributed to a website.
    """
    if website.pk is None:
        raise StorageAccountingError('Website has no saved identity')
    found = {}

    def add(domain, child=None):
        name = _component(domain.domain)
        direct_id = domain.domainOwner_id
        child_id = domain.childOwner_id
        if child is None:
            if direct_id != website.pk:
                raise StorageAccountingError('Mail domain has inconsistent website ownership')
        elif child_id != child.pk:
            raise StorageAccountingError('Mail domain has inconsistent child ownership')
        if direct_id is not None and direct_id != website.pk:
            raise StorageAccountingError('Mail domain belongs to a different website')
        if child_id is not None:
            owner = domain.childOwner
            if owner.pk != child_id or owner.master_id != website.pk:
                raise StorageAccountingError('Mail domain child belongs to a different website')
        identity = (direct_id, child_id)
        if name in found and found[name][0] != identity:
            raise StorageAccountingError('Mail domain has conflicting ownership records')
        found[name] = (identity, domain)

    for domain in website.domains_set.all():
        add(domain)
    for child in website.childdomains_set.all():
        if child.master_id != website.pk:
            raise StorageAccountingError('Child domain belongs to a different website')
        for domain in child.domains_set.all():
            add(domain, child)
    return tuple(found[name][1] for name in sorted(found))


def mail_domain_path(domain, mail_root=None):
    """Build the canonical root from the actual mail-domain record."""
    return os.path.join(os.path.abspath(mail_root or MAIL_ROOT), _component(domain.domain))


def _directory(path, optional=False):
    try:
        metadata = os.lstat(path)
    except FileNotFoundError:
        if optional:
            return None
        raise StorageAccountingError('Required storage directory is missing: %s' % path)
    except OSError as error:
        raise StorageAccountingError('Cannot inspect storage directory: %s' % path) from error
    if not stat.S_ISDIR(metadata.st_mode):
        raise StorageAccountingError('Storage path is not a real directory: %s' % path)
    return metadata.st_dev, metadata.st_ino


def _checked_path(base, components, optional=False):
    """Reject symlink roots/ancestors before passing any path to du."""
    base = os.path.abspath(base)
    if _directory(base, optional=optional) is None:
        return None
    path = base
    for component in components:
        path = os.path.join(path, _component(component))
        if _directory(path, optional=optional) is None:
            return None
    return path


def _run_du(paths):
    environment = os.environ.copy()
    environment.update(LC_ALL='C', LANG='C', LANGUAGE='C')
    try:
        result = subprocess.run(
            ['du', '--summarize', '--block-size=1', '--no-dereference',
             '--total', '--null', '--'] + list(paths),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
            timeout=600, env=environment)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise StorageAccountingError('Storage measurement could not complete') from error
    if result.returncode != 0 or result.stderr:
        raise StorageAccountingError('Storage measurement failed; cached usage was retained')
    try:
        records = result.stdout.split(b'\x00')
        if records[-1] != b'' or not records[-2].endswith(b'\ttotal'):
            raise ValueError('Missing complete total')
        total = records[-2][:-len(b'\ttotal')]
        if not total.isdigit():
            raise ValueError('Invalid byte count')
        return int(total)
    except (AttributeError, IndexError, TypeError, ValueError) as error:
        raise StorageAccountingError('Storage measurement returned an invalid total') from error


def measure_paths_bytes(paths):
    """Measure one combined allocated-byte total, counting hard links once.

    GNU du does not follow links within the trees. A single invocation also
    deduplicates hard links shared between the website and its mail domains.
    """
    roots = []
    identities = {}
    for path in sorted(set(os.path.abspath(path) for path in paths), key=lambda item: (len(item), item)):
        identity = _directory(path)
        if identity in identities.values():
            continue
        if any(os.path.commonpath((path, root)) == root for root in roots):
            continue
        roots.append(path)
        identities[path] = identity
    if not roots:
        return 0
    total = _run_du(roots)
    for path, identity in identities.items():
        if _directory(path) != identity:
            raise StorageAccountingError('Storage directory changed during measurement')
    return total


def _megabytes(byte_count):
    return (byte_count + MEBIBYTE - 1) // MEBIBYTE


def measure_website_storage(website, home_root=None, mail_root=None):
    """Collect all measurements before the caller writes any cached statistics."""
    home_root = home_root or HOME_ROOT
    mail_root = mail_root or MAIL_ROOT
    domains = owned_mail_domains(website)
    home_path = _checked_path(home_root, (website.domain,))
    roots = [home_path]
    mailboxes = []
    seen_emails = set()
    for domain in domains:
        domain_path = _checked_path(mail_root, (domain.domain,), optional=True)
        if domain_path is not None:
            roots.append(domain_path)
        for email in domain.eusers_set.all():
            if email.emailOwner_id != domain.domain:
                raise StorageAccountingError('Mailbox belongs to a different mail domain')
            local_part, separator, address_domain = email.email.rpartition('@')
            if not separator or address_domain != domain.domain or email.email in seen_emails:
                raise StorageAccountingError('Mailbox has inconsistent domain ownership')
            seen_emails.add(email.email)
            local_part = _component(local_part)
            expected_mail = 'maildir:' + os.path.join(
                os.path.abspath(mail_root), domain.domain, local_part, 'Maildir')
            if not isinstance(email.mail, str) or email.mail != expected_mail:
                raise StorageAccountingError('Mailbox storage is not a canonical CyberPanel maildir')
            mailbox_path = _checked_path(mail_root, (domain.domain, local_part), optional=True)
            usage = measure_paths_bytes([mailbox_path]) if mailbox_path is not None else 0
            mailboxes.append((email, str(_megabytes(usage))))
    usage_mb = _megabytes(measure_paths_bytes(roots))
    allowance = int(website.package.diskSpace)
    if allowance < 0:
        raise StorageAccountingError('Website storage allowance is invalid')
    return {
        'disk_usage_mb': usage_mb,
        'disk_usage_percentage': usage_mb * 100 // allowance if allowance else 0,
        'mailbox_usage': mailboxes,
        'mail_domains': domains,
    }
