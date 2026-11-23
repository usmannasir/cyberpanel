"""Unlock website homes that the File Manager locked by mistake.

From 3.0.9 to 3.0.15 every delete in the File Manager ran "chattr -R +i" on the
website's whole home: its probe ("touch -h", which never creates a file) always
failed, and a failed probe was read as a home that was already locked. Every
file and folder of the website became immutable, and uploads by FTP and by the
File Manager, and the website's own writes, failed.

The panel does not lock a home itself any more, and a customer who protects
files with chattr protects files, not the home folder itself. A home folder
that is immutable is the mark of that delete: such a home is unlocked again,
everything in it, without following links (chattr cannot change a link, and a
link may lead out of the home). A home whose folder is not immutable is left
exactly as it is.
"""
import os
import subprocess

FLAGS_COMMAND = ('lsattr', '-d')
# A home on a network file system that stopped answering must not hold the
# upgrade: it is reported instead.
FLAGS_TIMEOUT = 60
UNLOCK_TIMEOUT = 1800


def is_immutable(path, run=subprocess.run):
    """Whether the folder itself has the immutable attribute."""
    result = run(list(FLAGS_COMMAND) + ['--', path], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                 universal_newlines=True, timeout=FLAGS_TIMEOUT)
    if result.returncode != 0 or not result.stdout.strip():
        return False
    return 'i' in result.stdout.split()[0]


def unlock(path, run=subprocess.run):
    """Clear the immutable attribute of the folder and of every file and folder
    in it, links left alone. Returns whether it worked."""
    result = run(['find', '-P', path, '(', '-type', 'f', '-o', '-type', 'd', ')',
                  '-exec', 'chattr', '-i', '{}', '+'],
                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=UNLOCK_TIMEOUT)
    return result.returncode == 0


def website_homes(domains, root='/home'):
    """The home folders of these websites that exist and are real folders."""
    for domain in domains:
        if not domain or '/' in domain or domain in ('.', '..'):
            continue
        home = os.path.join(root, domain)
        if os.path.isdir(home) and not os.path.islink(home):
            yield home


def repair(domains=None, run=subprocess.run, homes=website_homes):
    """Unlock every website home whose folder is immutable. Returns the homes
    that were unlocked and those that could not be."""
    if domains is None:
        from websiteFunctions.models import Websites
        domains = list(Websites.objects.values_list('domain', flat=True))
    unlocked, failed = [], []
    for home in homes(domains):
        try:
            if not is_immutable(home, run):
                continue
            (unlocked if unlock(home, run) else failed).append(home)
        except Exception:
            # Timed out or could not be run: the other homes are still repaired.
            failed.append(home)
    return unlocked, failed
