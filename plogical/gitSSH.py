#!/usr/local/CyberCP/bin/python
"""Helpers for CyberPanel Git remotes (custom hosts and non-default SSH ports)."""

from __future__ import print_function


def parse_git_host(git_host):
    """
    Parse host or host:port.

    Returns (domain, port_or_None) or (None, error_message).
    """
    if git_host is None:
        return None, 'Git host is required.'
    host = str(git_host).strip()
    if not host:
        return None, 'Git host is required.'
    if host.find('://') > -1:
        return None, 'Use host or host:port (no URL scheme).'
    if host.find('/') > -1:
        return None, 'Invalid characters in Git host.'

    port = None
    domain = host
    if host.find(':') > -1:
        parts = host.rsplit(':', 1)
        domain = parts[0].strip()
        try:
            port = int(parts[1].strip())
        except (TypeError, ValueError):
            return None, 'Invalid port in Git host.'
        if port < 1 or port > 65535:
            return None, 'Invalid port in Git host.'

    if not domain or domain.find(' ') > -1:
        return None, 'Invalid Git host.'
    return domain, port


def build_ssh_remote_url(git_host, username, reponame):
    """
    Build a clone/remote URL.

    Default port 22: git@host:user/repo.git
    Custom port: ssh://git@host:port/user/repo.git
    """
    domain, port = parse_git_host(git_host)
    if domain is None:
        raise ValueError(port)
    user = str(username).strip().strip('/')
    repo = str(reponame).strip().strip('/')
    if repo.endswith('.git'):
        repo = repo[:-4]
    if port is None:
        return 'git@%s:%s/%s.git' % (domain, user, repo)
    return 'ssh://git@%s:%s/%s/%s.git' % (domain, port, user, repo)


def resolve_provider_host(default_provider, custom_host=None):
    """
    Map setupGit provider id to a host string.

    github / gitlab -> github.com / gitlab.com
    custom / private -> custom_host (required)
    """
    provider = (default_provider or 'github').strip().lower()
    if provider in ('custom', 'private'):
        host = (custom_host or '').strip()
        if not host:
            return None, 'Custom Git host is required.'
        domain, port_or_err = parse_git_host(host)
        if domain is None:
            return None, port_or_err
        return host, None
    if provider == 'gitlab':
        return 'gitlab.com', None
    if provider == 'github':
        return 'github.com', None
    if provider.find('.') > -1:
        return provider, None
    return '%s.com' % provider, None


def build_ssh_config(identity_file, hosts):
    """
    Build ~/.ssh/config content for one or more hosts.

    hosts: iterable of host strings (domain or domain:port).
    """
    blocks = []
    seen = set()
    for raw in hosts:
        domain, port = parse_git_host(raw)
        if domain is None:
            continue
        key = '%s:%s' % (domain, port or 22)
        if key in seen:
            continue
        seen.add(key)
        lines = [
            'Host %s' % domain,
            '  HostName %s' % domain,
            '  IdentityFile %s' % identity_file,
            '  IdentitiesOnly yes',
            '  StrictHostKeyChecking no',
        ]
        if port is not None:
            lines.append('  Port %s' % port)
        blocks.append('\n'.join(lines))
    return '\n\n'.join(blocks) + ('\n' if blocks else '')
