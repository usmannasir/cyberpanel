# Cookie hardening during source upgrades

The source upgrader retains explicit `True` assignments for
`SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, and `SESSION_COOKIE_HTTPONLY`
from the private backup of the previous `CyberCP/settings.py`. It merges those
three values into the new release settings before source activation, alongside
the existing database credential merge. New application lists and other release
defaults remain in place. Local `False` values never weaken release defaults.

The supported form is one top-level literal boolean assignment per setting
(including an annotated assignment). Duplicate, conditional, computed, chained,
or otherwise ambiguous direct assignments stop the source upgrade before the
installation is replaced and identify the setting requiring review. The old
settings source is parsed, never imported or executed by this preservation step.
Arbitrary settings imports or indirect runtime mutations are not a supported
local override mechanism and must be reviewed separately.

This is targeted preservation, not a general local-settings override system.
It does not enable secure-only cookies on installations that have not explicitly
configured them, change the default panel HTTP/HTTPS access policy, or repair
customizations already lost in earlier upgrades. A failed collectstatic step
restores the previous installation and its original settings through the existing
source activation rollback.

Validation: `python3 -W ignore -m unittest plogical.test_upgrade_source` covers
successful staging with all three flags, unchanged new applications/database
credentials, rejection before activation, rollback with the original settings,
non-execution of old source, stronger defaults, and repeated preservation without
duplicate assignments. These are isolated filesystem tests, not a production
customer upgrade or full install certification.
