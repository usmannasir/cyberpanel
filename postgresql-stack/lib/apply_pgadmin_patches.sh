#!/usr/bin/env bash
# Apply postgresql-stack patches to the installed pgAdmin bundle.
# Idempotent: safe to re-run after pgAdmin package upgrades.
set -euo pipefail

STACK_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=common.sh
source "${STACK_ROOT}/lib/common.sh"

APP_BUNDLE="/usr/pgadmin4/web/pgadmin/static/js/generated/app.bundle.js"
MARKER="pgstack-adhoc-lazy-api"
SRC_JSX="/usr/pgadmin4/web/pgadmin/misc/workspaces/static/js/AdHocConnection.jsx"

patch_app_bundle() {
    if [[ ! -f "${APP_BUNDLE}" ]]; then
        log_error "pgAdmin bundle not found: ${APP_BUNDLE}"
        return 1
    fi
    if grep -q "${MARKER}" "${APP_BUNDLE}"; then
        log_info "pgAdmin Query Tool patch already applied (${MARKER})."
        return 0
    fi

    local tmp
    tmp="$(mktemp)"
    python3 - "${APP_BUNDLE}" "${tmp}" "${MARKER}" <<'PY'
import sys

src_path, dst_path, marker = sys.argv[1:4]
data = open(src_path, encoding="utf-8").read()
old_ctor = "this.dbs=[],this.api=(0,g.default)(),this.connectExistingServer"
new_ctor = f"this.dbs=[],/*{marker}*/this.connectExistingServer"
if old_ctor not in data:
    raise SystemExit("ERROR: AdHocConnection constructor pattern not found in app.bundle.js")
data = data.replace(old_ctor, new_ctor, 1)
old_get = 'this.api.get((0,o.default)("sqleditor.get_new_connection_servers"))'
new_get = '(0,g.default)().get((0,o.default)("sqleditor.get_new_connection_servers"))'
if old_get not in data:
    raise SystemExit("ERROR: get_new_connection_servers API call pattern not found")
data = data.replace(old_get, new_get, 1)
old_other = "this.api.get((0,o.default)(`sqleditor.${t}`,{sid:e,sgid:0}))"
new_other = "(0,g.default)().get((0,o.default)(`sqleditor.${t}`,{sid:e,sgid:0}))"
if old_other not in data:
    raise SystemExit("ERROR: getOtherOptions API call pattern not found")
data = data.replace(old_other, new_other, 1)
open(dst_path, "w", encoding="utf-8").write(data)
print("patched")
PY
    cp -a "${APP_BUNDLE}" "${APP_BUNDLE}.bak.pgstack"
    mv "${tmp}" "${APP_BUNDLE}"
    chmod 644 "${APP_BUNDLE}"
    chown root:root "${APP_BUNDLE}" 2>/dev/null || true
    log_info "Patched ${APP_BUNDLE} (backup: ${APP_BUNDLE}.bak.pgstack)."
}

patch_source_jsx() {
    if [[ ! -f "${SRC_JSX}" ]]; then
        log_warn "AdHocConnection.jsx not found; bundle patch only."
        return 0
    fi
    if grep -q "${MARKER}" "${SRC_JSX}"; then
        return 0
    fi
    python3 - "${SRC_JSX}" "${MARKER}" <<'PY'
import pathlib, sys
path = pathlib.Path(sys.argv[1])
marker = sys.argv[2]
text = path.read_text(encoding="utf-8")
text = text.replace(
    "    this.api = getApiInstance();\n",
    f"    /* {marker}: lazy API client in getServerList/getOtherOptions */\n",
    1,
)
text = text.replace("this.api.get(", "getApiInstance().get(", 2)
if marker not in text:
    raise SystemExit("jsx patch failed")
path.write_text(text, encoding="utf-8")
print("jsx patched")
PY
    log_info "Patched ${SRC_JSX}."
}

patch_app_bundle
patch_source_jsx
log_info "pgAdmin patches applied."
