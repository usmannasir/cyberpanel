# Preserve signed PHP limits in Basic Settings

The Basic Settings readers tokenized numeric limits without their sign. For
example, an active `memory_limit = -1` or `max_input_time = -1` was returned as
`1`. Saving that form could therefore replace the original setting. Both the
HTTP reader and legacy manager reader now preserve signs for memory, execution
and input limits. Time-limit readers also ignore commented-out assignments and
match the exact directive.

Validation on isolated CyberPanel 3.0.8 QA:

- The real HTTP endpoint and authenticated Basic Settings browser showed `1`
  for a temporary `-1` configuration before the change and `-1` afterwards.
- `manage.py test managePHP.tests managePHP.test_signed_limits`: five test
  methods passed. The new parameter matrix covers five configurations across
  both readers, including negative, positive, quoted and zero values, comments,
  and the distinct `max_memory_limit` directive.
- The legacy reader was supplied an explicit fixture path because its existing
  FPM path selector has no PHP 8.3 mapping on this LSAPI QA installation. This
  does not claim live FPM integration coverage.
- The installed reader/writer preserved both `-1` values while changing an
  unrelated upload limit in a disposable INI file; service commands were
  intercepted. Native PHP validated the preserved unlimited memory value.

Original QA code/configuration and hashes, account/session state and core
services are restored after testing. This repairs a demonstrated configuration
reader defect; it does not establish the cause of a historical reporter's
runtime values or change a customer server automatically.
