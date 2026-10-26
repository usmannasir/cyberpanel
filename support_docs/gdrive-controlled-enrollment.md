# Controlled Google Drive enrollment

New enrollment is disabled unless both sides have valid private configuration.
Existing destinations and scheduled backups do not use this enrollment switch.
These instructions are for an operator provisioning a verified installation;
there is no public callback-registration or hostname-discovery endpoint.

## Configuration contract

Platform settings read only `/etc/cyberhosting/gdrive-handoff.json`:

```json
{
  "version": 1,
  "enabled": true,
  "platform_origin": "https://platform.cyberpersons.com",
  "database": "/var/lib/cyberhosting/gdrive-handoff/handoffs.sqlite3",
  "installations": [
    {"origin": "https://verified-panel.example:8090", "key": "GENERATE_A_UNIQUE_RANDOM_KEY_FOR_THIS_INSTALLATION"}
  ]
}
```

CyberPanel settings read only `/etc/cyberpanel/gdrive-handoff.json`:

```json
{
  "version": 1,
  "enabled": true,
  "platform_origin": "https://platform.cyberpersons.com",
  "installation_key": "THE_SAME_GENERATED_INSTALLATION_KEY"
}
```

Example key strings above are placeholders, not usable credentials. Each platform
installation expands to exactly `/backup/gDriveSetup` and
`/IncrementalBackups/ConfigureV2BackupSetup` on that origin, using its key. Include
the actual browser port. Origins must be canonical HTTPS origins without paths,
trailing slashes, user information, wildcards, queries or fragments. Duplicate
origins and keys reused across installations are rejected.

Configuration files must be regular, single-link, root-owned files, mode 0600
(or 0640 for a service read-group; read-only equivalents are accepted). Every
ancestor must be root-owned, not group/other writable, and not a symlink. Config
is limited to 64 KiB. Unknown or duplicate fields and invalid types are rejected.
Missing, unreadable or invalid config leaves enrollment disabled and never logs
its contents. Environment variables do not override the fixed paths or switch.

The handoff database belongs in a dedicated 0700 directory owned by the platform
service user, outside the web root. All workers must use the same file and stable
Django secret. Current platform service runs as root; if its user changes, adjust
database ownership and the config's read-group deliberately. Do not copy handoff
databases between environments.

## Prepare a paired enrollment without enabling it

First verify ownership/authorization for the customer server, its exact browser
origin and a valid HTTPS certificate. Upgrade it to a release containing the
loader. The customer's Google OAuth application must authorize exactly
`https://platform.cyberpersons.com/gDrive/v2/callback` as the Google redirect.
Normal backup setup requires backup permission; V2 additionally requires website
ownership and the existing premium entitlement. These checks remain enforced.

Run the following on the platform as root from the deployed project directory.
Replace the example origin and choose a new private staging directory. This
writes paired candidate files only; it does not replace production configuration
or print the generated installation key. Existing registry entries are retained,
and an existing origin is rejected rather than silently rotating its key.

```bash
cd /home/platform.cyberpersons.com/public_html
python3 - https://verified-panel.example:8090 /root/gdrive-enrollment-NEW <<'PY'
import json, os, secrets, sys
from pathlib import Path
from CommonUtils.gdriveSettings import _read_private_json, _validate, _origin
origin = _origin(sys.argv[1])
stage = Path(sys.argv[2])
if os.geteuid() != 0:
    raise SystemExit('Run as root')
stage.mkdir(mode=0o700, parents=False, exist_ok=False)
try:
    registry = _read_private_json('/etc/cyberhosting/gdrive-handoff.json')
    _validate(registry, 'platform')
except FileNotFoundError:
    registry = {'version': 1, 'enabled': False}
registry.setdefault('platform_origin', 'https://platform.cyberpersons.com')
registry.setdefault('database', '/var/lib/cyberhosting/gdrive-handoff/handoffs.sqlite3')
registry.setdefault('installations', [])
key = secrets.token_urlsafe(32)
registry['installations'].append({'origin': origin, 'key': key})
registry['enabled'] = True
panel = {'version': 1, 'enabled': True,
         'platform_origin': registry['platform_origin'], 'installation_key': key}
_validate(registry, 'platform')
_validate(panel, 'panel')
for name, document in (('platform.json', registry), ('panel.json', panel)):
    fd = os.open(stage / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as output:
        json.dump(document, output, indent=2)
        output.write('\n')
print('Paired candidate files prepared; production configuration unchanged.')
PY
```

Review the origin, installation count and database path without printing keys.
Transfer only `panel.json` to that verified server using the authorized SSH
connection; never send the whole platform registry to a customer. Keep both files
out of Git, tickets, chat, access logs and shell environment dumps.

## Activate the reviewed pair

After testing the deployed OAuth dependency set, install the platform candidate
as root-owned 0600 at its fixed path, using a temporary sibling and atomic rename.
Keep a private rollback copy of any existing registry first. Create the dedicated
database directory owned by the actual platform service user, mode 0700.
For the current root service, for example:

```bash
install -d -o root -g root -m 0700 /var/lib/cyberhosting/gdrive-handoff
install -o root -g root -m 0600 /root/gdrive-enrollment-NEW/platform.json /etc/cyberhosting/.gdrive-handoff.new
mv -T /etc/cyberhosting/.gdrive-handoff.new /etc/cyberhosting/gdrive-handoff.json
```

On the verified CyberPanel server, create `/etc/cyberpanel` if absent with root
ownership, group `cyberpanel`, mode 0750; preserve unrelated existing directory
contents. Install its transferred `panel.json` as root:cyberpanel 0640 at
`/etc/cyberpanel/gdrive-handoff.json`, again via a temporary sibling and atomic
rename. Verify the actual panel worker group has read access. The file lives
outside the source replacement tree and remains operator-managed across upgrades.

Reload platform workers and restart `lscpd` on that customer panel to load the
new settings. The loader reads once at settings import. Test both authenticated
setup availability endpoints and complete the intended consent/Save flow. Global
`/gDrive/capabilities` indicates service readiness, not proof that a particular
customer key is admitted; successful authenticated registration proves that pair.
Do not claim global customer enablement from one configured canary.

Existing OAuth dependencies must be reconciled against the whole application's
requirements before activation. This loader does not install packages or change
service configuration. Do not downgrade a shared dependency solely for this flow.

## Disable, revoke or rotate

To stop all new enrollment, atomically set `enabled` to the JSON boolean `false`
and reload workers; keep the registry/key data for a later controlled re-enable.
To revoke one installation, remove its registry entry and reload platform workers.
Other installations remain admitted. For rotation, provision a new unique key on
both sides; do not reuse another customer's key. Restart the affected workers and
start a fresh setup. Pending setup expires after five minutes. Existing saved
Drive destinations are not disconnected by changing the enrollment switch.
