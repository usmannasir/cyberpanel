# pip-audit record (CyberPanel fork)

Date note: run on server used for CI or operator workstation; re-run after `requirments.txt` changes.

## 2026-05-04 run (after bumping Django, sqlparse, cryptography, pyOpenSSL)

Resolved on install set (see `requirments.txt` at same commit):

- Django raised from 4.2.14 to **4.2.30** (LTS security line).
- **sqlparse** pinned to **0.5.4**.
- **cryptography** lower bound **>=44.0.1** (installer resolved 47.x in test venv).
- **pyOpenSSL** lower bound **>=25.0.0** (installer resolved 26.x).

Remaining findings from `pip-audit -r requirments.txt` on Python 3.9 venv (transitive or ecosystem limits):

| Package       | Note |
| ------------- | ---- |
| python-dotenv | GHSA fix in 1.2.2 requires Python **>=3.10**; pin stays **1.0.0** on 3.9 installs. Upgrade dotenv when panel runtime is 3.10+. |
| requests      | Advisory suggests **2.33.0**; not published for this index at audit time; kept **>=2.32.4**. Re-audit when 2.33.x is available. |
| pyasn1        | Transitive; fix **0.6.3** may need explicit pin if tooling allows. |
| starlette     | Via **fastapi**; newer starlette may need **fastapi** bump (watch Python version support). |
| urllib3       | Pinned indirectly by **requests** 2.32.x to **1.26.x** line; moving to urllib3 2.x needs coordinated **requests** upgrade. |
| filelock      | Transitive; optional pin **>=3.20.3** if a direct dependency is added. |

## bandit (webmail, aiScanner, api)

High findings **B324** on `hashlib.md5` for file content fingerprints were addressed in `aiScanner/api.py` using `usedforsecurity=False` (Python 3.9+). Re-run:

```bash
bandit -r webmail aiScanner api --severity-level high
```

## Command reference

```bash
python3 -m venv /tmp/cp-audit-venv
/tmp/cp-audit-venv/bin/pip install -U pip pip-audit
/tmp/cp-audit-venv/bin/pip-audit -r requirments.txt
```
