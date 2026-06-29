# CyberPanel Upgrade False Failure and lscpd on OpenVZ

## Summary

Some successful CyberPanel upgrades can end with:

```text
Seems something wrong with upgrade, please check...
```

This message does not always mean the upgrade failed. Older upgrade scripts checked the panel with:

```bash
curl -I https://127.0.0.1:8090 | grep -q "200 OK"
```

That check is too strict because the panel can return a redirect, an authorization response, or an HTTP/2 status line that does not contain the literal text `200 OK`. In those cases the upgrade can finish successfully while the final message still reports failure.

## Fast Triage

Use the upgrade debug log as the source of truth:

```bash
grep -i "All components successfully installed" /var/log/cyberpanel_upgrade_debug.log
```

If the log contains `All components successfully installed!`, treat the upgrade as completed and troubleshoot panel availability separately.

Check the panel endpoint with status codes instead of grepping the status line:

```bash
curl -k -L -s -o /dev/null -w "%{http_code}\n" https://127.0.0.1:8090/
```

Expected non-failure codes include `200`, `302`, `401`, and `403`. A `000` response usually means the service is not accepting the connection.

## Distinguish the Two Issues

### False Upgrade Failure Message

Signs:

- Upgrade debug log says all components installed successfully.
- The final installer output says something went wrong.
- `curl -I` output does not contain the literal text `200 OK`, or the panel returns a redirect/auth response.

Action:

- Do not rerun the full upgrade only because of this final message.
- Verify the HTTP status with `curl -k -L -s -o /dev/null -w "%{http_code}\n"`.
- If the status is `200`, `302`, `401`, or `403`, the final message was a false alarm.

### lscpd Not Serving Port 8090

Signs:

- Upgrade log shows success, but `https://SERVER_IP:8090` is unreachable.
- Local status check returns `000` or connection refused.
- `ss -ltnp | grep ':8090'` shows nothing listening.
- Mail services still work because Postfix and Dovecot are independent of the CyberPanel web service.

This is common on some OpenVZ/Virtuozzo ploop containers where cgroup support is missing or incomplete. In that environment, `systemctl restart lscpd` can appear to run but the service may not stay running.

## Commands to Collect Evidence

```bash
cat /usr/local/lscp/conf/bind.conf
curl -k -L -s -o /dev/null -w "%{http_code}\n" https://127.0.0.1:8090/
ss -ltnp | grep ':8090'
systemctl status lscpd --no-pager
journalctl -u lscpd -n 80 --no-pager
grep -i "All components successfully installed" /var/log/cyberpanel_upgrade_debug.log
```

If `bind.conf` contains an address and port, use the port portion for the curl check.

## Support Response Template

```text
The upgrade log shows that CyberPanel completed the upgrade successfully. The final "Seems something wrong with upgrade" message can be a false alarm caused by the old final status check expecting the exact string "200 OK".

The current issue is separate: the CyberPanel service is not serving the panel port. Mail can continue working because Postfix and Dovecot do not depend on the panel web service.

Please provide working SSH access so we can restart and inspect lscpd directly. If this is an OpenVZ/Virtuozzo container, systemd/cgroup limitations can prevent lscpd from staying up after a normal restart.
```

## Permanent Script Fix

The upgrade script should check the HTTP status code directly and accept normal panel responses:

```bash
Panel_HTTP_Code=$(curl -k -L -s -o /dev/null -w "%{http_code}" "https://127.0.0.1:${Panel_Port#*:}/")
if [[ "$Panel_HTTP_Code" =~ ^(200|302|401|403)$ ]] ; then
    echo "CyberPanel Upgraded"
else
    echo "Seems something wrong with upgrade, please check..."
fi
```
