#!/usr/local/CyberCP/bin/python
"""Convert a top-level CyberPanel website into a child domain under an apex site."""

import os
import shlex
import shutil
import time
from random import randint

from loginSystem.models import Administrator
from plogical.acl import ACLManager
from plogical.processUtilities import ProcessUtilities
from plogical import CyberCPLogFileWriter as logging
from plogical import virtualHostUtilities
from websiteFunctions.models import ChildDomains, Websites


def find_master_candidate(domain):
    """Return the longest matching apex domain managed as a top-level website."""
    labels = (domain or '').split('.')
    if len(labels) < 3:
        return None

    for index in range(1, len(labels) - 1):
        candidate = '.'.join(labels[index:])
        if Websites.objects.filter(domain=candidate).exists():
            return candidate
    return None


def convert_website_to_child_domain(user_id, website_name, master_domain=None):
    """
    Remove a duplicate top-level website entry and attach it under a master domain.

  When a child domain row already exists, only the top-level website shell is removed.
  Otherwise the docroot is moved under the master home and a child domain is created.
    """
    website_name = (website_name or '').strip().lower()
    if not website_name:
        return 0, 'Website name is required.'

    current_acl = ACLManager.loadedACL(user_id)
    if ACLManager.currentContextPermission(current_acl, 'modifyWebsite') == 0:
        return 0, 'You are not authorized to modify websites.'

    admin = Administrator.objects.get(pk=user_id)

    try:
        website = Websites.objects.get(domain=website_name)
    except Websites.DoesNotExist:
        return 0, 'Website not found.'

    if ACLManager.checkOwnership(website_name, admin, current_acl) != 1:
        return 0, 'You do not own this website.'

    if not master_domain:
        master_domain = find_master_candidate(website_name)
    master_domain = (master_domain or '').strip().lower()

    if not master_domain:
        return 0, 'No matching master domain was found for this website.'

    if master_domain == website_name:
        return 0, 'A website cannot be converted under itself.'

    if not website_name.endswith('.' + master_domain):
        return 0, '%s is not a subdomain of %s.' % (website_name, master_domain)

    try:
        master = Websites.objects.get(domain=master_domain)
    except Websites.DoesNotExist:
        return 0, 'Master domain %s was not found.' % master_domain

    if ACLManager.checkOwnership(master_domain, admin, current_acl) != 1:
        return 0, 'You do not own the master domain %s.' % master_domain

    existing_child = ChildDomains.objects.filter(domain=website_name).first()
    if existing_child and existing_child.master_id != master.pk:
        return 0, '%s is already a child domain of %s.' % (
            website_name, existing_child.master.domain)

    php_selection = website.phpSelection or master.phpSelection
    old_home = '/home/%s' % website_name
    child_path = '/home/%s/%s' % (master_domain, website_name)
    temp_status_path = '/home/cyberpanel/%s' % randint(1000, 9999)

    try:
        if existing_child:
            logging.writeToFile(
                'convert_to_child: removing duplicate top-level website %s; child already exists under %s'
                % (website_name, master_domain))
        else:
            master_home = '/home/%s' % master_domain
            if not os.path.isdir(master_home):
                return 0, 'Master home directory %s does not exist.' % master_home

            if os.path.exists(child_path):
                return 0, 'Target path %s already exists.' % child_path

            if os.path.isdir(old_home):
                shutil.move(old_home, child_path)
                logging.writeToFile(
                    'convert_to_child: moved %s to %s' % (old_home, child_path))
            else:
                os.makedirs(child_path, mode=0o755, exist_ok=True)

        exec_path = (
            '/usr/local/CyberCP/bin/python '
            + shlex.quote(virtualHostUtilities.cyberPanel)
            + '/plogical/virtualHostUtilities.py deleteVirtualHostConfigurations --virtualHostName '
            + shlex.quote(website_name)
        )
        ProcessUtilities.executioner(exec_path)

        if existing_child:
            return 1, '%s is now managed only as a subdomain of %s.' % (
                website_name, master_domain)

        apache_backend = '0'
        apache_path = '/usr/local/lsws/conf/vhosts/%s.conf' % master_domain
        if os.path.exists(apache_path):
            apache_backend = '1'

        exec_path = (
            '/usr/local/CyberCP/bin/python '
            + shlex.quote(virtualHostUtilities.cyberPanel)
            + '/plogical/virtualHostUtilities.py createDomain'
            + ' --masterDomain ' + shlex.quote(master_domain)
            + ' --virtualHostName ' + shlex.quote(website_name)
            + ' --phpVersion ' + shlex.quote(php_selection)
            + ' --ssl 1 --dkimCheck 1 --openBasedir 1'
            + ' --path ' + shlex.quote(child_path)
            + ' --websiteOwner ' + shlex.quote(admin.userName)
            + ' --tempStatusPath ' + shlex.quote(temp_status_path)
            + ' --apache ' + apache_backend
            + ' --aliasDomain 0'
        )
        ProcessUtilities.popenExecutioner(exec_path)
        time.sleep(2)

        return 1, 'Conversion started for %s under %s.' % (website_name, master_domain)

    except BaseException as exc:
        logging.writeToFile('convert_to_child failed for %s: %s' % (website_name, exc))
        return 0, str(exc)
