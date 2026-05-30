#!/bin/bash
# CyberPanel install/venvsetup – modular loader. Sources venvsetup_modules/*.sh.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$SCRIPT_DIR/cyberpanel_ssh_login_banner.sh" ]]; then
  # shellcheck source=/dev/null
  source "$SCRIPT_DIR/cyberpanel_ssh_login_banner.sh"
fi
for f in 01_vars_install_required 02_memcached_main 03_main_run_pip 04_after_install 05_argument_main; do
  if [[ -f "$SCRIPT_DIR/venvsetup_modules/${f}.sh" ]]; then
    source "$SCRIPT_DIR/venvsetup_modules/${f}.sh"
  fi
done
