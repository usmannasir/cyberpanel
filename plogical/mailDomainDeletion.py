"""Checked mailbox and empty mail-domain deletion shared by the UI and CLI."""
from django.db import transaction
from mailServer.models import Domains, EUsers
from websiteFunctions.models import Websites, ChildDomains
from plogical import storageQuota


def delete_mailbox(email, authorize=None):
    """Delete one mailbox record; retain its Maildir and registered domain scope.

    Domain locking serializes last-mailbox decisions and blocks a concurrent
    foreign-key insertion while an empty domain is removed. Enrollment itself
    remains a maintenance operation, as required by the project quota service.
    """
    with transaction.atomic():
        domain_id = EUsers.objects.values_list('emailOwner_id', flat=True).get(pk=email)
        domain = Domains.objects.select_for_update().get(pk=domain_id)
        mailbox = EUsers.objects.select_for_update().get(pk=email)
        if mailbox.emailOwner_id != domain.pk:
            raise ValueError('Mail domain ownership changed; refresh and try again.')

        website_id = domain.domainOwner_id
        if domain.childOwner_id is not None:
            child = ChildDomains.objects.select_for_update().get(pk=domain.childOwner_id)
            if website_id is not None and website_id != child.master_id:
                raise ValueError('Mail domain has inconsistent website ownership.')
            website_id = child.master_id
        if website_id is None:
            raise ValueError('Mail domain has no website owner.')
        website = Websites.objects.select_for_update().get(pk=website_id)
        if authorize is not None and not authorize(website):
            raise ValueError('You do not own this website.')

        retain_domain = storageQuota.has_enrollment(website)
        mailbox.delete()
        if not retain_domain and not EUsers.objects.select_for_update().filter(emailOwner_id=domain.pk).exists():
            domain.delete()
