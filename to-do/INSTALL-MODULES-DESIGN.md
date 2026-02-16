# Install modularization design

## Overview
- **cyberpanel.sh**: Modular loader; sources `install_modules/00_common.sh` … `09_parse_main.sh`. When `install_modules/` is missing (e.g. one-liner), downloads modules from GitHub.
- **install.sh**: Wrapper that detects OS, checks disk; if repo has `cyberpanel.sh` + `install_modules/`, runs local loader; else downloads `cyberpanel.sh` and runs it.
- **install/venvsetup.sh**: Loader that sources `install/venvsetup_modules/01_*` … `05_*`. Original kept as `install/venvsetup_monolithic.sh`.

## install_modules/ (repo root)
| Module | Lines | Content |
|--------|-------|---------|
| 00_common.sh | ~418 | Globals, log_message, print_status, show_banner, detect_os, fix_static_file_permissions, fix_post_install_issues |
| 01_verify_deps.sh | ~129 | verify_installation, install_dependencies |
| 02_install_core.sh | ~390 | install_cyberpanel, check_cyberpanel_installed, cleanup_existing_cyberpanel, install_cyberpanel_direct (part 1) |
| 03_install_direct.sh | ~411 | install_cyberpanel_direct_cont |
| 04_fixes_status.sh | ~210 | apply_fixes, _port_listening, show_status_summary |
| 05_menus_main.sh | ~328 | show_main_menu, show_fresh_install_menu, show_commit_selection, show_version_selection, show_installation_preferences |
| 06_menus_update.sh | ~247 | show_update_menu, show_reinstall_menu, show_system_status |
| 07_menus_advanced.sh | ~273 | show_advanced_menu, show_error_help, show_fix_menu, show_clean_menu, show_logs_menu, show_diagnostics |
| 08_actions.sh | ~317 | start_upgrade, start_force_reinstall, start_preupgrade, start_reinstall, start_installation |
| 09_parse_main.sh | ~247 | parse_arguments, detect_installation_mode, create_standard_aliases, main |

All modules kept under 500 lines. Loader: `cyberpanel.sh`. Backup: `cyberpanel_install_monolithic.sh`.

## install/venvsetup_modules/
| Module | Content |
|--------|---------|
| 01_vars_install_required.sh | Vars, safe_pip_install, license_validation, special_change, system_tweak, install_required |
| 02_memcached_main.sh | memcached_installation, redis_installation, check_provider, check_*, interactive_*, main_install |
| 03_main_run_pip.sh | main_install_run, pip_virtualenv |
| 04_after_install.sh | after_install |
| 05_argument_main.sh | argument_mode, main flow (check_OS, install_required, pip_virtualenv, system_tweak, main_install) |

Loader: `install/venvsetup.sh`. Backup: `install/venvsetup_monolithic.sh`. Refactor: `main_install` calls `main_install_run()` for size split.

## install/ (Python and other files)
- **install/install.py**, **install/installCyberPanel.py**, etc. are unchanged; they are used by the shell installer and may be split in a future pass (e.g. into Python packages) if needed for the 500-line rule.
