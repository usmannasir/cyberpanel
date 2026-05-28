#!/usr/bin/env bash
# Run inside CI Docker container (or repo root). Validates upgrade loader + modules and key files.
set -e

echo "=== Shell syntax check ==="
for f in cyberpanel_upgrade.sh preUpgrade.sh fix-phpmyadmin.sh fix-snappymail.sh cyberpanel.sh cyberpanel_utility.sh; do
  [ ! -f "$f" ] && continue
  bash -n "$f" || { echo "FAIL (syntax): $f"; exit 1; }
  echo "OK $f"
done
if [ -f scripts/utils/cyberpanel-utils.sh ]; then
  bash -n scripts/utils/cyberpanel-utils.sh || { echo "FAIL (syntax): scripts/utils/cyberpanel-utils.sh"; exit 1; }
  echo "OK scripts/utils/cyberpanel-utils.sh"
  for f in scripts/utils/*.sh; do
    [ -f "$f" ] || continue
    case "$f" in *cyberpanel-utils.sh) continue ;; esac
    bash -n "$f" || { echo "FAIL (syntax): $f"; exit 1; }
    echo "OK $f"
  done
fi
test -f preUpgrade.sh && test -f cyberpanel_upgrade.sh || { echo "Missing required scripts"; exit 1; }

echo "=== Key files ==="
for f in preUpgrade.sh cyberpanel_upgrade.sh plogical/upgrade.py install/install.py; do
  test -f "$f" || { echo "Missing: $f"; exit 1; }
done
grep -q 'BRANCH_NAME' preUpgrade.sh || exit 1

if [ -d upgrade_modules ]; then
  for n in 00_common 01_variables 02_checks 03_mariadb 04_git_url 05_repository 06_components 07_branch_input 08_main_upgrade 09_sync 10_post_tweak 11_display_final; do
    test -f "upgrade_modules/${n}.sh" || { echo "Missing: upgrade_modules/${n}.sh"; exit 1; }
  done
  grep -q 'Branch_Check\|Branch_Name' upgrade_modules/00_common.sh upgrade_modules/02_checks.sh || exit 1
  grep -q 'upgrade_modules\|Pre_Upgrade_Branch_Input\|Set_Default_Variables' cyberpanel_upgrade.sh || exit 1
  for f in upgrade_modules/*.sh; do
    [ -f "$f" ] || continue
    bash -n "$f" || { echo "FAIL (syntax): $f"; exit 1; }
  done
else
  grep -q 'Branch_Name\|download_install_phpmyadmin\|Branch_Check' cyberpanel_upgrade.sh || exit 1
fi

echo "Done."
