# One-Click Backup public-key validation and repair

The One-Click Backup DeployAccount path previously forwarded the output of `cat /root/.ssh/cyberpanel.pub` directly to CreateSFTPAccount. A missing or malformed public file could therefore prevent deployment even when the intended private identity still existed.

DeployAccount now invokes the fixed-path helper through the existing privileged ProcessUtilities boundary with `/usr/local/CyberCP/bin/python`. It derives and validates the public half using bounded, non-interactive OpenSSH against an already-open private-key descriptor. It never generates, replaces, changes permissions on, or logs a private key or passphrase. Missing private keys and invalid or encrypted identities stop deployment with a clear error.

An already matching public file is preserved. An absent public file is published exclusively; a malformed public file is backed up to an owned mode-0600 `.cyberpanel.pub.before-repair-<uuid>` file before atomic replacement. A different but valid public key is refused because the intended identity is ambiguous. Cooperative calls share a bounded lock. Symlinks, FIFOs, unsafe permissions/ownership, and observed key or directory identity drift are refused. After publication, observed drift stops the API call without restoring over another owner's replacement. The public file may have been repaired at that point; no private key was changed, and the pair requires review. Root processes outside this cooperative lock can still race a later rotation, so this is not a substitute for coordinating manual key changes.

The helper accepts the platform validator's existing key types, including RSA, Ed25519 and ECDSA; it does not narrow existing deployment behavior to RSA. Some existing backup-transfer paths separately load `paramiko.RSAKey`; that preexisting transfer limitation is not changed or claimed resolved here. The standalone helper avoids post-Python-3.6 subprocess and pathlib convenience APIs. The normal installer may create an initial identity during a fresh installation; this recovery path does not do so.

## Validation

Run `python -m unittest plogical.test_backup_ssh_key -v` on Linux with OpenSSH available. Twenty tests cover real temporary RSA/Ed25519/ECDSA and encrypted-key fixtures, private-byte and metadata preservation, corrupt-public backup, mismatch refusal, nonblocking FIFO and symlink refusal, pre/postpublication drift, timeout handling, and the actual DeployAccount method extracted from release source. Four deployment contract regressions fail against the previous release implementation. Tests use temporary keys and mocked platform/ORM calls; no production keys, customer host, subscription, or SFTP account is changed.

This source fix does not confirm a customer's existing key state, paid-subscription status, successful account deployment, or end-to-end backup transfer. Customer retesting is still required after updating to the released code.
