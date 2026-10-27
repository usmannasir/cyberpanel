# Cloudflare credential helper privilege boundary

SSL V2 remains a paid feature. Its authenticated/authorized view passes JSON through stdin to the fixed privileged helper. This policy changes neither entitlement checks nor refund handling.

Root install/upgrade provisions `/etc/sudoers.d/cyberpanel-cloudflare` after the Google Drive helper policy. Only `cyberpanel` and `lscpd` may invoke these exact root commands without a password:

```
/usr/local/CyberPanel/bin/python -I -S /usr/local/CyberCP/plogical/cloudflareCredentials.py metadata
/usr/local/CyberPanel/bin/python -I -S /usr/local/CyberCP/plogical/cloudflareCredentials.py save
```

There are no wildcard arguments, general Python/shell grants, or credentials on the command line. `NOSETENV`, `env_reset`, a fixed secure path, and isolated Python without site initialization constrain the invocation. The helper accepts bounded stdin and returns credential status only; the root-owned account file is not made readable by the web users.

`gdriveSudo.provision_fixed` shares the existing checked installation transaction. It validates lexical and resolved root-owned, non-writable interpreter/helper/dependency ancestry, requires an enabled `/etc/sudoers.d`, rejects an unmanaged or symlink policy, writes mode0440 through a private temporary file, validates the candidate with visudo, then validates the full policy. Full-policy failure restores the original file (or removes the newly created one). The existing Google Drive policy bytes and command grant are unchanged.

The provisioner requires sudo/visudo and refuses to modify the main sudoers file. Failure requires administrator review of the dependency or trust-path diagnostic; do not work around it by granting arbitrary Python or shell access.

## Acceptance

Unit checks cover exact command grants, Google Drive policy-byte preservation, both provisioning hooks, idempotence, unmanaged-file refusal, candidate/global validation rollback, unprivileged provisioning, and inactive/outside target names.

A network-disabled owned Ubuntu22/Python3.10 container was temporarily connected to install sudo, then disconnected before testing. Actual UID1000 cyberpanel and UID1001 lscpd requests saved synthetic token/global-key credentials through sudo and returned only configured/mode metadata. Direct file reads, arbitrary Python/shell, extra arguments, alternate actions, non-isolated invocation, direct unprivileged helper calls and explicit sudo environment assignments were rejected. Inherited Python environment injection did not execute. Malformed/oversized/invalid-secret saves preserved the prior file. Root-only mode0600, writable-helper refusal, unmanaged-policy refusal, policy idempotence and complete visudo validation passed.

No host sudoers, customer credentials, or production services were changed. This tests the privilege boundary; Cloudflare API/ACME behavior is covered separately.
