#!/usr/bin/env bash
# Inject PostgreSQL/pgAdmin card into CyberPanel Quick App Installer.
# Target: websiteFunctions/templates/websiteFunctions/website.html (.app-grid).
set -euo pipefail

STACK_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../lib/common.sh
source "${STACK_ROOT}/lib/common.sh"

load_config

PGADMIN_DOMAIN="$(cfg_get pgadmin_domain)"
SSO_TOKEN="$(cfg_get pgadmin_sso_token 2>/dev/null || true)"
WEBSITE_HTML="/usr/local/CyberCP/websiteFunctions/templates/websiteFunctions/website.html"
LEGACY_HTML="/usr/local/CyberCP/websiteFunctions/templates/websiteFunctions/applicationInstaller.html"
ICON_DIR="/usr/local/CyberCP/public/static/images/icons"
ICON_FILE="${ICON_DIR}/postgresql.png"
MARKER="POSTGRESQL_STACK_TILE"
if [[ -n "${SSO_TOKEN}" && "${SSO_TOKEN}" != "missing key" ]]; then
    TILE_URL="https://${PGADMIN_DOMAIN}/sso/?key=${SSO_TOKEN}"
else
    TILE_URL="https://${PGADMIN_DOMAIN}/"
fi

install_icon() {
    mkdir -p "${ICON_DIR}"
    if [[ -f "${ICON_FILE}" ]]; then
        log_info "PostgreSQL icon already present."
    else
        log_info "Installing PostgreSQL icon for CyberPanel tile..."
        if curl -sfL "https://www.postgresql.org/media/img/about/press/elephant.png" -o "${ICON_FILE}.tmp" 2>/dev/null; then
            mv "${ICON_FILE}.tmp" "${ICON_FILE}"
            chmod 644 "${ICON_FILE}"
        else
            touch "${ICON_FILE}"
            log_warn "Could not download icon; placeholder created at ${ICON_FILE}."
        fi
    fi

    for dest in \
        "/usr/local/CyberCP/static/images/icons/postgresql.png" \
        "/usr/local/CyberCP/websiteFunctions/static/images/icons/postgresql.png"; do
        mkdir -p "$(dirname "${dest}")"
        cp -f "${ICON_FILE}" "${dest}" 2>/dev/null || true
    done
}

clean_legacy_injection() {
    if [[ -f "${LEGACY_HTML}" ]] && grep -q "${MARKER}" "${LEGACY_HTML}"; then
        log_info "Removing stale tile from legacy applicationInstaller.html..."
        TARGET="${LEGACY_HTML}" MARK="${MARKER}" python3 <<'PY'
import os, re
from pathlib import Path
path = Path(os.environ["TARGET"])
mark = os.environ["MARK"]
text = path.read_text()
text = re.sub(r"\n\s*<!-- " + re.escape(mark) + r" -->.*?</a>\n", "\n", text, flags=re.DOTALL)
path.write_text(text)
PY
    fi
}

patch_website_ui() {
    if [[ ! -f "${WEBSITE_HTML}" ]]; then
        return 0
    fi
    if grep -q "POSTGRESQL_STACK_UI_FIX" "${WEBSITE_HTML}"; then
        log_info "Website UI cloak patch already present."
        return 0
    fi

    log_info "Patching website.html domain form (hide until Angular, ng-cloak)..."
    TARGET="${WEBSITE_HTML}" python3 <<'PY'
from pathlib import Path
import os

path = Path(os.environ["TARGET"])
text = path.read_text()
marker = "<!-- POSTGRESQL_STACK_UI_FIX -->"

old_form = (
    '<form id="domainCreationForm" name="websiteCreationForm" action="/"\n'
    '                                  class="form-horizontal bordered-row">'
)
new_form = (
    marker + '\n'
    '                            <form id="domainCreationForm" name="websiteCreationForm" action="/"\n'
    '                                  class="form-horizontal bordered-row" style="display:none;" ng-cloak>'
)
if old_form in text:
    text = text.replace(old_form, new_form, 1)
elif 'POSTGRESQL_STACK_UI_FIX' not in text and 'id="domainCreationForm"' in text:
    text = text.replace(
        'id="domainCreationForm" name="websiteCreationForm" action="/"\n'
        '                                  class="form-horizontal bordered-row"',
        marker + '\n'
        '                            <form id="domainCreationForm" name="websiteCreationForm" action="/"\n'
        '                                  class="form-horizontal bordered-row" style="display:none;" ng-cloak',
        1,
    )

old_block = '''                                <div ng-hide="installationProgress" class="form-group">
                                    <label class="col-sm-2 control-label"></label>
                                    <div class="col-sm-7">

                                        <div class="alert alert-success text-center">
                                            <h2>{$ currentStatus $}</h2>
                                        </div>'''
new_block = '''                                <div ng-hide="installationProgress" class="form-group" ng-cloak>
                                    <label class="col-sm-2 control-label"></label>
                                    <div class="col-sm-7">

                                        <div class="alert alert-success text-center">
                                            <h2>{$ currentStatus $}</h2>
                                        </div>'''
if old_block in text:
    text = text.replace(old_block, new_block, 1)

for old, new in [
    ('<div ng-hide="errorMessageBox" class="alert alert-danger">', '<div ng-hide="errorMessageBox" class="alert alert-danger" ng-cloak>'),
    ('<div ng-hide="success" class="alert alert-success">\n                                            <p>{% trans "Website succesfully created." %}</p>',
     '<div ng-hide="success" class="alert alert-success" ng-cloak>\n                                            <p>{% trans "Website succesfully created." %}</p>'),
    ('<div ng-hide="couldNotConnect" class="alert alert-danger">\n                                            <p>{% trans "Could not connect to server. Please refresh this page." %}</p>',
     '<div ng-hide="couldNotConnect" class="alert alert-danger" ng-cloak>\n                                            <p>{% trans "Could not connect to server. Please refresh this page." %}</p>'),
]:
  if old in text:
    text = text.replace(old, new, 1)

go_back_old = '''                                <div ng-hide="installationProgress" class="form-group">
                                    <label class="col-sm-3 control-label"></label>
                                    <div class="col-sm-4">
                                        <button type="button" ng-disabled="goBackDisable" ng-click="goBack()"'''
go_back_new = '''                                <div ng-hide="installationProgress" class="form-group" ng-cloak>
                                    <label class="col-sm-3 control-label"></label>
                                    <div class="col-sm-4">
                                        <button type="button" ng-disabled="goBackDisable" ng-click="goBack()"'''
if go_back_old in text:
    text = text.replace(go_back_old, go_back_new, 1)

path.write_text(text)
print("ui patched")
PY
}

inject_card() {
    if [[ ! -f "${WEBSITE_HTML}" ]]; then
        log_error "CyberPanel website.html not found: ${WEBSITE_HTML}"
        exit 1
    fi
    if grep -q "${MARKER}" "${WEBSITE_HTML}"; then
        log_info "PostgreSQL card already present in Quick App Installer."
        return 0
    fi

    log_info "Injecting PostgreSQL/pgAdmin card into Quick App Installer (website.html)..."
    cp -a "${WEBSITE_HTML}" "${WEBSITE_HTML}.bak.postgresql-stack.$(date +%Y%m%d%H%M%S)"

    TARGET="${WEBSITE_HTML}" MARK="${MARKER}" TILEURL="${TILE_URL}" python3 <<'PY'
import os
from pathlib import Path

path = Path(os.environ["TARGET"])
mark = os.environ["MARK"]
url = os.environ["TILEURL"]
text = path.read_text()

card = (
    "                <!-- " + mark + " -->\n"
    "                <a href=\"" + url + "\" target=\"_blank\" rel=\"noopener noreferrer\" class=\"app-card postgresql\">\n"
    "                    <div class=\"quick-badge\">Database</div>\n"
    "                    <div class=\"app-icon-wrapper\">\n"
    "                        <img src=\"{% static 'images/icons/postgresql.png' %}\" alt=\"PostgreSQL\" class=\"app-icon\">\n"
    "                    </div>\n"
    "                    <h3 class=\"app-name\">PostgreSQL / pgAdmin</h3>\n"
    "                    <p class=\"app-description\">{% trans \"PostgreSQL database administration via pgAdmin 4\" %}</p>\n"
    "                    <div class=\"app-features\">\n"
    "                        <span class=\"feature-tag\">pgAdmin</span>\n"
    "                        <span class=\"feature-tag\">pg_cron</span>\n"
    "                        <span class=\"feature-tag\">SQL</span>\n"
    "                    </div>\n"
    "                    <div class=\"install-btn\">\n"
    "                        <i class=\"fas fa-database\"></i>\n"
    "                        {% trans \"Open pgAdmin\" %}\n"
    "                    </div>\n"
    "                </a>\n"
)

# Insert after the Mautic card (the last card in the Quick App Installer grid).
# fa-chart-line is unique to the Mautic install button, so this anchors the
# correct grid rather than the management-tools grid above it.
anchor = (
    "                        <i class=\"fas fa-chart-line\"></i>\n"
    "                        {% trans \"Install Now\" %}\n"
    "                    </div>\n"
    "                </a>\n"
)
if anchor not in text:
    raise SystemExit("Mautic card anchor not found in website.html; aborting injection")

text = text.replace(anchor, anchor + card, 1)
path.write_text(text)
print("card injected")
PY

    log_info "Card injected. Re-apply after CyberPanel upgrades: ${STACK_ROOT}/reapply-tile.sh"
}

update_tile_href() {
    if [[ ! -f "${WEBSITE_HTML}" ]] || ! grep -q "${MARKER}" "${WEBSITE_HTML}"; then
        return 0
    fi
    TARGET="${WEBSITE_HTML}" MARK="${MARKER}" TILEURL="${TILE_URL}" python3 <<'PY'
import os, re
from pathlib import Path

path = Path(os.environ["TARGET"])
mark = os.environ["MARK"]
url = os.environ["TILEURL"]
text = path.read_text()

# Update the href on the tile anchor immediately following our marker comment.
pattern = re.compile(
    r'(<!-- ' + re.escape(mark) + r' -->\s*\n\s*<a href=")[^"]*(")'
)
new_text, n = pattern.subn(r'\g<1>' + url.replace('\\', r'\\') + r'\g<2>', text, count=1)
if n and new_text != text:
    path.write_text(new_text)
    print("tile href updated")
else:
    print("tile href unchanged")
PY
}

install_icon
clean_legacy_injection
patch_website_ui
inject_card
update_tile_href
