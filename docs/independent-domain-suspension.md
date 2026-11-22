# Independent sub/addon domain suspension

The Suspend/Unsuspend page can select an owned main website or child domain.
Main website suspension still blocks its children. A child also has its own
independent state, so restoring the parent does not restore a separately
suspended child. Clearing a child's independent suspension while its parent is
suspended leaves it inaccessible; the page displays that inherited state.

The existing suspend permission and domain ownership checks apply to both
status and changes. Existing API action spellings (`Unsuspend`, `UnSuspend`,
`SUSPEND`) remain accepted; unknown actions fail instead of restoring a site.

Existing installations gain `websiteFunctions_childdomains.state` through the
verified, idempotent schema step in the normal upgrade. The default of `1`
means independently active; parent suspension remains separate. Fresh installs
create the field from the model through their existing schema setup. The
repository generates application migrations on the installed panel, so this
change follows the existing explicit upgrade-schema convention rather than
introducing a new initial migration for this already-populated application.

XML and cloud/S3 JSON backups include independent child suspension state.
Restore applies that state before a new child can serve content and reconciles
it again after restoring its vhost. Legacy backups without the field default
new children to active independent state and preserve an existing child's
current independent state. Restoring a child's state also verifies its parent
matches the website being restored.

Vhost changes use the normal privileged command service. Parent and child
operations serialize with child provisioning and lock the parent database row.
The shared helper preserves existing rewrite rules, writes vhosts atomically,
checks the server configuration and activates it. The server's configuration
test is run before and after the change, and only an error the change added
refuses it: a fresh installation already ends the test with status 1 for
warnings about its stock Example virtual host, and an error in one website
ends it with 2 while the server keeps running. Any failure before the
database commit restores original vhost files and attempts to reactivate them;
the restored files are judged against the same earlier result.

Three consequences of judging a change by what it added:

- An error that was already in the configuration before the change does not
  refuse a suspension or a restore, also when it is not confined to one
  website (a listener, the WebAdmin configuration, a disabled module). The
  server is restarted with it, as every other panel action that restarts the
  server does. If such an error would keep OpenLiteSpeed from starting, correct
  it first: `/usr/local/lsws/bin/openlitespeed -t` lists it.
- Restoring a website puts back the configuration it had before it was
  suspended. Its rewrite rules are commented out while it is suspended, so an
  error in them is not reported then and returns with them. An error line
  about a website that is being restored therefore does not refuse the
  restore, of that website or of the parent and siblings restored with it. A
  line is about a website when its context names the virtual host
  (`[config:server:vhosts:vhost:NAME...]`) or when the only website directory
  it names is `conf/vhosts/NAME/`. A new error about any other website, a
  server-wide one, a fatal one, or one that names no website still refuses the
  restore and leaves the websites suspended.
- Line numbers are ignored when comparing, but only in messages about the
  websites whose files the change edits, because suspension moves the lines
  of exactly those files.
Recovery failure is reported explicitly. Suspension applies at vhost rewrite
level, before more-specific contexts, and affects HTTP and HTTPS using the
same vhost. Existing SSL certificates are not changed.
An existing customized `websiteFunctions/suspension.html` is preserved and used;
the bundled fallback is `suspension-default.html`. Switching between Apache and
OpenLiteSpeed also reapplies effective suspension before activating the new
frontend configuration.

## Regression checks

Run without panel bootstrap:

```console
python -m unittest plogical.test_website_suspension plogical.test_website_suspension_check websiteFunctions.test_domain_suspension plogical.test_child_creation_suspension plogical.test_child_backup_suspension plogical.test_upgrade_login_schema websiteFunctions.test_addon_parent_ownership
node --test websiteFunctions/test_domain_suspension_ui.cjs
node --check websiteFunctions/static/websiteFunctions/websiteFunctions.js
```

Native integration must use an isolated panel database and OLS installation,
with main, child and sibling fixture vhosts and HTTP/HTTPS listeners. Check
ordinary paths and a more-specific static/proxy context throughout:

1. Suspend child: child blocked, parent and sibling remain active.
2. Suspend then restore parent: independently suspended child remains blocked.
3. Restore child: child serves its original content and rewrite rules again.
4. Suspend parent, clear child's independent suspension: child remains blocked.
5. Restore parent: independently active children serve again.
6. Repeat each operation; verify no duplicate blocks or extra server activation.
7. Simulate config validation/activation failure; verify original files and
   database states survive, and original content still serves.
   Repeat items 1 and 3 on a server whose configuration test does not end
   with 0 before the change (a fresh installation, and one website with an
   error of its own): both must succeed.
   Put a faulty rule into the rewrite block of a child's vhost file, suspend
   and restore its parent: parent, child and siblings must all be restored.
8. Verify cross-owner and missing-permission requests cannot mutate any vhost.
9. Create/regenerate a child under suspended parent; it must never serve content
   before inheriting the parent's effective suspension.

Do not use a customer's server or the platform's shared production database for
these checks. Passing unit tests alone does not establish native OLS behavior.

`plogical.test_website_suspension_native` retains the real ORM → privileged
worker → OLS acceptance runner. Ordinary unit discovery skips it. It requires
an explicitly disposable Docker fixture with the synthetic domain/listener
configuration above, MySQL database `jehu_qa` at
`cp-jehu-suspension-mysql`, and `/qa/ISOLATED_SUSPENSION_QA` containing
`cyberpanel-jehu-native-qa`. In that container only, run:

```console
CYBERPANEL_RUN_NATIVE_SUSPENSION_TESTS=isolated-qa python -m unittest plogical.test_website_suspension_native
```

The runner mutates fixture vhosts and schema, injects one reload failure, and
writes `/qa/native-receipt.json`. Against the real configuration test it
checks both sides of the rule above: a fault in another website from before
the change is tolerated, and a change that itself adds an error (the worker's
code, writing a block with a stray closing brace) is refused and undone. Native creation checks invoke the actual
inheritance hook before saving/activating its synthetic child; unit tests
separately execute the creation dispatcher's ordering and failure paths. They
do not establish external DNS/ACME issuance on every installation type.
