# CyberPanel issue #1764 hardening (operator guide)

Reference: [usmannasir/cyberpanel#1764](https://github.com/usmannasir/cyberpanel/issues/1764)

This guide covers post-upgrade verification and optional host hardening shipped in branch `v2.5.5-dev`. Scripts live under `/usr/local/CyberCP/scripts/security/`.

## Quick verification (after every upgrade)

```bash
/usr/local/CyberCP/scripts/verify_fastapi_ssh_hardening.sh
/usr/local/CyberCP/scripts/security/issue-1764-audit.sh | tee /home/cyberpanel/to-do/issue-1764-audit-$(date +%Y%m%d-%H%M%S).txt
```

Expected:

- `fastapi_ssh_server` listens on `127.0.0.1:8888` only
- No attacker IP `94.102.55.18` in auth logs
- lscpd integrity passes
- Public firewalld has **reject** on 8888, not **accept**

Upgrade hook (`upgrade_modules/10_post_tweak.sh`) runs verify + `harden-firewall-8888.sh` automatically.

## Weekly cron (optional)

```cron
0 3 * * 0 root /usr/local/CyberCP/scripts/verify_fastapi_ssh_hardening.sh >> /var/log/cyberpanel_fastapi_verify.log 2>&1
```

## Firewall: port 8888

```bash
/usr/local/CyberCP/scripts/security/harden-firewall-8888.sh
```

Removes legacy public accept rules and adds priority `-20` reject rules. Does not change the service bind (localhost only).

## Restrict panel ports (8090 / 7080 only)

**Does not touch SSH (22) or FTP.** Hosting users keep SFTP/WinSCP.

1. Create `/etc/cyberpanel/admin_ips.conf` (chmod `600`), one trusted IPv4 per line:

```
203.0.113.10
```

2. Run:

```bash
/usr/local/CyberCP/scripts/security/restrict-admin-ports.sh
```

## Block known attacker infrastructure

```bash
/usr/local/CyberCP/scripts/security/block-known-iocs.sh
/usr/local/CyberCP/scripts/security/block-known-iocs.sh --extra   # also 80.78.18.178
```

Persist iptables rules per your firewalld/iptables-save policy.

## SSH hardening (manual, per host)

**Before changing sshd:** confirm your admin IP and that your SSH key works (`ssh -i key root@host`).

Audit noted root **password** logins from `51.174.191.240`. Confirm with the operator that this is expected admin access before disabling password auth.

After confirmation, append to `/etc/ssh/sshd_config.d/cyberpanel-hardening.conf`:

```
PermitRootLogin prohibit-password
PasswordAuthentication no
PubkeyAuthentication yes
```

Then:

```bash
sshd -t && systemctl reload sshd
```

Optional: lock root authorized_keys after verifying your key:

```bash
chattr +i /root/.ssh/authorized_keys
```

To unlock later: `chattr -i /root/.ssh/authorized_keys`

## Optional auditd watches

```bash
/usr/local/CyberCP/scripts/security/install-auditd-rules.sh
```

## Upgrade from public repo

```bash
sudo bash <(curl -sL https://raw.githubusercontent.com/usmannasir/cyberpanel/v2.5.5-dev/cyberpanel_upgrade.sh) -b v2.5.5-dev
```

## Access check after hardening

From a **second session** (do not close your current SSH):

1. Root SSH with key still works
2. Site-user SFTP/WinSCP to a test account works
3. FTP login works (if enabled)
4. Panel loads from an IP in `admin_ips.conf` (if restrict script was run)
