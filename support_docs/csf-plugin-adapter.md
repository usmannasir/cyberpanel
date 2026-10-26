# Optional ConfigServer CSF plugin request boundary

The optional plugin's iframe view is CSRF-exempt and dispatches both GET and POST
parameters to its privileged Perl backend. Older installers inject a broad
`configservercsf` substring exception into core input validation. Do not retain
that injected exception during upgrades.

CyberPanel now adapts only `/configservercsf/iframe/` when Django resolves it to
`configservercsf.views.configservercsfiframe`. It verifies the logged-in user's
administrator ACL before adapting the request. Existing session/IP checks still
run. Every POST requires a real Django CSRF cookie/token and origin validation,
even though the installed vendor view is exempt. Only then is the generic input
character filter skipped, allowing legitimate configuration text and port ranges.

A query-free GET opens the dashboard. The inspected display-only `readme`,
`status`, `lfdstatus`, and `temp` actions can use GET with exactly one action field.
Every other query receives a core confirmation page. Opening a destructive link
therefore does not execute it; the administrator must submit its CSRF-protected
POST. Unknown actions and duplicate/extra query fields also require confirmation.

HTML forms targeting this same-origin iframe endpoint receive a CSRF token and
POST method. Other HTML, scripts and external forms are preserved. Adapted output
is private and non-cacheable, and core security headers still apply. No vendor
files, installer patches, firewall policy, service state or permissions are
modified by this adapter.

The inspected plugin is Aetherinox CSF 15.10. This boundary does not audit or
replace the vendor's privileged command implementations. Advanced vendor AJAX
GET requests outside the small display allowlist receive a confirmation document
and may require navigating to the action instead. Do not expand the GET allowlist
without inspecting the corresponding Perl dispatch and its parameters.

Tests: `CyberCP.test_csf_adapter` exercises real Django CSRF/origin validation,
exact route scope, administrator denial, destructive GET confirmation, duplicate
parameters, form transformation and full security middleware execution against a
CSRF-exempt fixture. `CyberCP.test_security_middleware` covers adjacent behavior.
Actual plugin configuration-save acceptance must also be performed on an owned
isolated CyberPanel installation before release claims.
