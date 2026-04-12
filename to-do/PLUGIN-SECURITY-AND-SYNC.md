# Plugin security and branch sync (master3395 fork)

**Oppdatert:** 12.04.2026

## `v2.5.5-dev` vs upstream

- Lokal `v2.5.5-dev` er **synket med** `usmannasir/cyberpanel` branch `v2.5.5-dev` gjennom merge-base **778de5af** (Merge pull request #1761 from master3395/v2.5.5-dev).
- Siste commit på denne forgreningen: **c7995ecf** — «Fix missing /usr/local/CyberCP/bin/python for cron og IncBackups».

Kjør jevnlig for å holde deg à jour med upstream:

```bash
cd /home/cyberpanel-repo
git fetch origin
git fetch usmannasir
git merge usmannasir/v2.5.5-dev
git push origin v2.5.5-dev
```

## Community-plugins (sikkerhet)

Sikkerhetsforbedringer for installerte CyberPanel-plugins (Fail2ban, Discord Auth/Webhooks, Redis Manager, Memcache Manager, Google Tag Manager) vedlikeholdes i **cyberpanel-plugins**, ikke i denne kjernerepoen.

- Repo: https://github.com/master3395/cyberpanel-plugins
- Referansecommit (security hardening på `main`): **6be9796e** (12.04.2026).

Installer eller oppdater plugins via CyberPanel Plugin Manager eller ved å hente siste `main` fra det repoet.
