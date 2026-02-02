# Security Guidelines for Premium Plugin

## ⚠️ IMPORTANT: Never Expose Secrets

This plugin is designed to be **publicly shareable**. It contains **NO secrets** and is safe to publish.

## What's Safe to Share

✅ **Safe to commit:**
- Plugin code (views.py, urls.py, etc.)
- Templates (HTML files)
- meta.xml (no secrets, only tier name and URL)
- README.md
- Documentation

❌ **Never commit:**
- Patreon Client Secret
- Patreon Access Tokens
- Patreon Refresh Tokens
- Any hardcoded credentials

## Configuration

All Patreon credentials are configured on the **server side** via:
- Environment variables
- Django settings (from environment)
- Secure config files (not in repository)

## For Your Own Setup

When setting up this plugin on your server:

1. **Do NOT** modify plugin files with your secrets
2. **Do** configure environment variables on the server
3. **Do** use Django settings.py (with environment variable fallbacks)
4. **Do** add any secret config files to .gitignore

## Example Secure Configuration

```python
# In settings.py (safe to commit)
PATREON_CLIENT_ID = os.environ.get('PATREON_CLIENT_ID', '')
PATREON_CLIENT_SECRET = os.environ.get('PATREON_CLIENT_SECRET', '')

# On server (NOT in repo)
export PATREON_CLIENT_ID="your_actual_secret"
export PATREON_CLIENT_SECRET="your_actual_secret"
```

## Verification

Before publishing, verify:
- [ ] No secrets in plugin files
- [ ] No secrets in meta.xml
- [ ] No secrets in README
- [ ] All credentials use environment variables
- [ ] .gitignore excludes secret files
