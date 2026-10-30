# Legacy sender policy service

`policyCTRL.py` starts the daemon using CyberPanel's Python interpreter and the
`postfixSenderPolicy.startServer` module. Direct execution of `startServer.py`
is also supported for existing launchers.

The socket protocol is Postfix SMTPD access policy delegation: UTF-8 `name=value`
lines, a blank line terminating each request, and an ASCII `action` response
terminated by a blank line. Connections may contain multiple requests. The
handler buffers incomplete frames and rejects requests over 64 KiB. A connection
with no progress for 30 seconds is closed; an incomplete request receives a
transient defer response. An idle connection receives no unsolicited response.

Authenticated mail retains the legacy domain/account enable semantics: both
limit flags must be enabled for hourly/monthly limits to defer mail. Counters are
updated together under a process-local lock. Multi-recipient DATA requests still
count and enforce limits when Postfix omits the individual recipient. Their log
destination is empty. Unauthenticated mail and domains without configured policy
records receive DUNNO. Unexpected database/processing failures receive a transient
defer instead of silently allowing authenticated mail.

## Validation

Run `python3 -m unittest discover -s tests -p test_postfix_sender_policy.py -v`.
Tests use real socket pairs and a fresh daemon process on a temporary UNIX socket.
Django and ORM dependencies are stubbed before import; these tests do not load
installed settings, connect to a database, edit Postfix, or send mail. They cover
import/launcher behavior, bind failure, SIGTERM exit, fragmented/coalesced frames,
64-byte boundaries, limits, malformed/oversized/timed-out requests, unauthenticated
mail, missing recipients, database failures and concurrent requests.

## Operational limits

This repair does not change Postfix's configured outage fallback:
`savePolicyServerStatus` still writes `smtpd_policy_service_default_action = DUNNO`.
If the service cannot be reached or Postfix times out, mail can therefore proceed
without sender-policy enforcement. Passing these isolated tests is not evidence
that a particular server has enabled the service or is enforcing its limits.
Verify service health and a controlled SMTP submission on a dedicated test system
before depending on it. No production Postfix/SMTP validation is part of this fix.

The legacy PID-file/process-control design, cached counter persistence, and
file-based cleanup command mechanism remain. This change is not a redesign of
those mechanisms or a migration to Rspamd.

Protocol reference: https://www.postfix.org/SMTPD_POLICY_README.html
