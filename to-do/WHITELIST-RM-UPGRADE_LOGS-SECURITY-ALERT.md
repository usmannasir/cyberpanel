# Security alert: `rm -rf /home/cyberpanel/upgrade_logs`

## Is this an issue?

**No.** This is **expected behavior** from the CyberPanel upgrade process, not a sign of compromise.

## What’s going on

- Your security product (e.g. OSSEC, Wazuh, or similar) flagged:
  - **Command:** `sudo ... /bin/rm -rf /home/cyberpanel/upgrade_logs`
  - **Context:** `PWD=/tmp/lscpd`, `USER=root`
- The CyberPanel daemon (**lscpd**) runs upgrade-related tasks. The upgrade logic uses `/home/cyberpanel/upgrade_logs` as the path for upgrade logs (see `plogical/upgrade.py`: `LogPathNew = '/home/cyberpanel/upgrade_logs'`). Cleaning that path (file or directory) before or after an upgrade is normal so the next run starts from a clean state.
- So this command is the **panel cleaning its own upgrade logs**, not an attacker.

## Why does it look “suspicious”?

- Security tools often treat **any** `rm -rf` as “dangerous” because it can delete a lot if misused.
- They also flag “system file access” or “writes/deletes under /home” to catch abuse.
- Here, the path is a **known, fixed** CyberPanel path and the process is **root from lscpd** (expected for the panel). So the alert is a **false positive** for “suspicious command” in this context.

## Why “my own local files” look suspicious

- “Local files” in the alert usually means “commands or file operations on this machine.” The product isn’t saying your personal files are malicious; it’s saying the **behavior** (e.g. `rm -rf` on a path under `/home`) matches a **rule** that can indicate compromise.
- In this case the “local” actor is **CyberPanel itself** (lscpd/upgrade), so the behavior is legitimate.

## What you can do

1. **Treat as expected:** No need to change passwords or hunt for backdoors solely because of this alert.
2. **Whitelist/tune the rule:** In your security product, add an exception or rule so that this specific command (or pattern) when run by root from the lscpd context is not reported, e.g.:
   - Command pattern: `rm -rf /home/cyberpanel/upgrade_logs`
   - Or: allow `rm -rf` for paths under `/home/cyberpanel/` when the process is lscpd/upgrade-related.
3. **Keep monitoring:** Continue to review real suspicious activity (e.g. unknown scripts, unexpected `rm -rf /` or `rm -rf /home/*`).

## Summary

- **Not a compromise** – normal CyberPanel upgrade cleanup.
- **“Suspicious”** only in the generic sense (rm -rf + /home); in context it’s the panel’s own operation.
- **Action:** Whitelist or tune the alert for this known-good case; no need to panic or “fix” the panel for this.

---

## Whitelist / rule examples (stop this specific case being reported)

Use the example that matches your product. After editing config, restart the agent/manager as indicated.

### OSSEC

Allow this command so it is not reported as suspicious.

**1. Local rule to ignore this command**

Create or edit a local rule file (e.g. `/var/ossec/etc/rules/local_rules.xml`) and add:

```xml
<!-- Allow CyberPanel upgrade cleanup: rm -rf /home/cyberpanel/upgrade_logs -->
<rule id="100001" level="0">
  <if_sid>100002</if_sid>
  <match>rm -rf /home/cyberpanel/upgrade_logs</match>
  <description>Whitelist: CyberPanel upgrade log cleanup (expected)</description>
</rule>
```

If your “suspicious command” rule has a different `<rule id>`, replace `100002` with that rule’s ID (so this rule only applies when that one fires). If you’re not sure, you can use a broader override that matches the command and sets level 0:

```xml
<rule id="100001" level="0">
  <match>rm -rf /home/cyberpanel/upgrade_logs</match>
  <description>Whitelist: CyberPanel upgrade log cleanup</description>
</rule>
```

Restart OSSEC:

```bash
systemctl restart ossec
# or
/var/ossec/bin/ossec-control restart
```

**2. (Optional) Decoder to tag sudo rm**

In `/var/ossec/etc/decoders/local_decoder.xml` you can add a decoder so the command is clearly identified; the rule above is enough to stop the alert.

### Wazuh

**1. Local rule to not alert on this command**

Append to `/var/ossec/etc/rules/local_rules.xml` (Wazuh keeps OSSEC-style paths):

```xml
<!-- Whitelist CyberPanel upgrade cleanup -->
<group name="local,syscheck,">
  <rule id="100001" level="0">
    <match>rm -rf /home/cyberpanel/upgrade_logs</match>
    <description>Whitelist: CyberPanel upgrade_logs cleanup (lscpd/upgrade)</description>
  </rule>
</group>
```

If the alert is from a different rule (e.g. “suspicious command” or “syscheck”), you may need to set `<if_sid>` to that rule’s ID so this rule only overrides that case.

Restart Wazuh:

```bash
systemctl restart wazuh-agent
# On manager:
systemctl restart wazuh-manager
```

**2. (Optional) Broader CyberPanel cleanup**

To allow any `rm -rf` under `/home/cyberpanel/` when the process is from lscpd/upgrade, you’d need a rule that matches both the command pattern and (if available) the process or PWD. That’s product-specific; the rule above is the minimal, safe whitelist for the exact command you saw.

### Other products (generic)

- **Fail2ban / custom script:** If the alert is generated by a script that parses `auth.log` or `secure`, add an exception when the log line contains both `rm -rf` and `/home/cyberpanel/upgrade_logs`.
- **SIEM / cloud:** Add an exception or filter so that events with command `rm -rf /home/cyberpanel/upgrade_logs` and user `root` (and optionally process/source indicating lscpd) are not escalated.

Once the whitelist is in place, future runs of that CyberPanel cleanup will no longer trigger this specific alert.
