# PostgreSQL stack (optional addon)

Optional **PostgreSQL 17 + pg_cron + pgAdmin 4** stack for CyberPanel on AlmaLinux/RHEL 9+.

Shipped in-repo at `/usr/local/CyberCP/postgresql-stack/` after panel install or upgrade sync.

## Install (new panel)

Interactive installer:

```bash
sh <(curl https://cyberpanel.net/install.sh || wget -O - https://cyberpanel.net/install.sh)
```

Answer **Yes** when asked about the PostgreSQL stack, or use:

```bash
sh cyberpanel.sh --postgresql-stack
```

## Install (existing server, manual)

From the live panel tree:

```bash
cd /usr/local/CyberCP/postgresql-stack
./install.sh --master-domain example.com --domain pgadmin.example.com
```

Secrets are written to `config.php` (chmod 600, not in git).

## Upgrade

On upgrade, if `config.php` already exists the upgrade script:

1. Keeps existing secrets
2. Refreshes pgAdmin patches and the CyberPanel Quick App tile
3. Restarts `pgadmin4` if the unit is installed

Fresh optional install after upgrade:

```bash
/usr/local/CyberCP/postgresql-stack/install.sh
```

## Uninstall

```bash
/usr/local/CyberCP/postgresql-stack/uninstall.sh
```

Use `--purge-data` only when you intend to remove PostgreSQL data.

## Branches

| Branch | Status |
|--------|--------|
| `v3.0.5-dev` | Integrated in `cyberpanel.sh` and `cyberpanel_upgrade.sh` |
| `v3.0.4` | Stack files included; manual or `--postgresql-stack` install |

Fork reference: [master3395/cyberpanel v3.0.4](https://github.com/master3395/cyberpanel/tree/v3.0.4)
