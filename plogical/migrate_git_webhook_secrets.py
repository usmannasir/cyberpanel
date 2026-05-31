#!/usr/local/CyberCP/bin/python
"""Add webhookSecret to existing git JSON configs under /home/cyberpanel/git/."""
import json
import os
import sys

sys.path.insert(0, '/usr/local/CyberCP')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CyberCP.settings')

def main():
    from plogical.webhookSecurity import generate_webhook_secret
    base = '/home/cyberpanel/git'
    updated = 0
    if not os.path.isdir(base):
        print('No git config directory.')
        return 0
    for root, _dirs, files in os.walk(base):
        for name in files:
            path = os.path.join(root, name)
            try:
                with open(path, 'r', encoding='utf-8', errors='replace') as handle:
                    data = json.loads(handle.read())
            except Exception:
                continue
            if data.get('webhookSecret'):
                continue
            data['webhookSecret'] = generate_webhook_secret()
            with open(path, 'w', encoding='utf-8') as handle:
                handle.write(json.dumps(data))
            updated += 1
            print('Updated', path)
    print('Done. Files updated:', updated)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
