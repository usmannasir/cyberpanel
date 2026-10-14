"""Optional remote themes must not prevent access to local CSS settings."""
import re


def fetch_theme_catalog(get):
    response = get('https://api.github.com/repos/usmannasir/CyberPanel-Themes/commits', timeout=(3, 5))
    response.raise_for_status()
    commits = response.json()
    if not isinstance(commits, list) or not commits or not isinstance(commits[0], dict):
        raise ValueError('Invalid theme commit response.')
    sha = commits[0].get('sha')
    if not isinstance(sha, str) or not re.fullmatch(r'[a-fA-F0-9]{40}', sha):
        raise ValueError('Invalid theme commit identifier.')
    response = get('https://api.github.com/repos/usmannasir/CyberPanel-Themes/git/trees/' + sha, timeout=(3, 5))
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict) or not isinstance(payload.get('tree'), list):
        raise ValueError('Invalid theme tree response.')
    return [entry['path'] for entry in payload['tree']
            if isinstance(entry, dict) and entry.get('type') == 'tree'
            and isinstance(entry.get('path'), str)]
