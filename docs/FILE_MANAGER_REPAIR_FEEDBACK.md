# File Manager repair feedback and editor bounds

Permission repair now checks command outcomes, preserves document-root mode 0750
throughout its recursive changes, and keeps child roots restricted even when
they are outside the parent's public_html. Recursive chmod uses find's batched
exec form so a failed chmod produces a failure status. The view propagates an
explicit refusal rather than reporting success. Both shipped legacy controllers
and the modern controller suppress duplicate clicks while a request is pending
and display HTTP errors; this is a per-page guard, not a cross-worker job lock.

The editor's CLI reader now allows at most 4 MiB and returns a specific message for
larger files. Download remains available. The generic safe reader's 16 MiB default
is unchanged. Website-user execution, regular-file/no-symlink checks, allowed-root
containment, administrator-only repair and premium root-file-manager entitlement
checks remain in place. WordPress Manager and all paid features remain paid.

Verification includes nine focused Python cases (including a real find child
failure), six JavaScript cases, Chromium/Angular request/error/retry checks, and
nine native filesystem/LSPHP CLI checks on an owned QA host. The old repair made
an outside-public_html child readable to another fixture Unix user; the update
denied that read while preserving the owner and configured web-server group's
access. Small-file editing succeeded; a 5 MiB log was rejected with the size message.
No customer files or installed panel/services were changed; fixture Unix users
and homes were removed.

This is not a full container isolation guarantee or a fix for every CPU, theme,
or resource-display symptom in issue 1588. Applications sharing a Unix user or
permitted group share the corresponding filesystem access. A failure may follow
earlier completed permission changes; it now stops and is reported for review.
