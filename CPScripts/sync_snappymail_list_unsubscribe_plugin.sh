#!/usr/bin/env bash
# Sync list-unsubscribe-header from a local snappymail-plugins (or upstream clone)
# checkout into install/snappymail/plugins/ for CyberPanel packaging.
#
# Usage (from CyberPanel repo root):
#   export SNAPPYMAIL_PLUGINS_ROOT=/path/to/snappymail-plugins
#   ./CPScripts/sync_snappymail_list_unsubscribe_plugin.sh
#
# Optional: CYBERPANEL_REPO_ROOT overrides repo root (parent of CPScripts).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${CYBERPANEL_REPO_ROOT:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
SRC_ROOT="${SNAPPYMAIL_PLUGINS_ROOT:-}"

if [[ -z "${SRC_ROOT}" ]]; then
	echo "ERROR: Set SNAPPYMAIL_PLUGINS_ROOT to the directory containing list-unsubscribe-header/ (e.g. snappymail-plugins checkout)." >&2
	exit 1
fi

SRC_FILE="${SRC_ROOT%/}/list-unsubscribe-header/index.php"
DEST_DIR="${REPO_ROOT}/install/snappymail/plugins/list-unsubscribe-header"
DEST_FILE="${DEST_DIR}/index.php"

if [[ ! -f "${SRC_FILE}" ]]; then
	echo "ERROR: Source not found: ${SRC_FILE}" >&2
	exit 1
fi

mkdir -p "${DEST_DIR}"

python3 - "${SRC_FILE}" "${DEST_FILE}" <<'PY'
import sys
from pathlib import Path

src = Path(sys.argv[1])
dst = Path(sys.argv[2])
raw = src.read_text(encoding="utf-8", errors="strict")

if "Bundled with CyberPanel" in raw:
    out = raw
else:
    if not raw.startswith("<?php"):
        raise SystemExit("ERROR: expected plugin to start with <?php")
    body = raw[len("<?php") :].lstrip("\n")
    if body.startswith("/**"):
        end = body.find("*/")
        if end == -1:
            raise SystemExit("ERROR: unterminated docblock in source")
        rest = body[end + 2 :].lstrip("\n")
    else:
        rest = body

    bundled = (
        "<?php\n\n"
        "/**\n"
        " * Bundled with CyberPanel (see plogical/snappymail_plugin_utilities.py).\n"
        " * Upstream: https://github.com/master3395/snappymail-list-unsubscribe-header\n"
        " *\n"
        " * Adds List-Unsubscribe and List-Unsubscribe-Post on outbound mail (RFC 2369 / RFC 8058).\n"
        " */\n"
    )
    out = bundled + rest

dst.write_text(out.replace("\r\n", "\n"), encoding="utf-8")
PY

php -l "${DEST_FILE}" >/dev/null
echo "OK: wrote ${DEST_FILE}"
