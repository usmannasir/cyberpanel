# CyberPanel Upgrade Script - Modular Layout for Debugging

## Goal

Split `cyberpanel_upgrade.sh` into modules under `upgrade_modules/` so each file is under 500 lines and easier to debug.

## Directory Layout

- `upgrade_modules/00_common.sh` - Debug_Log, Debug_Log2, Branch_Check, Check_Return, Regenerate_Cert, Retry_Command (DONE)
- `upgrade_modules/01_variables.sh` - Set_Default_Variables (DONE)
- `upgrade_modules/02_checks.sh` - Check_Root, Check_Server_IP, Check_OS, Check_Provider, Check_Argument
- `upgrade_modules/03_mariadb.sh` - Pre_Upgrade_CentOS7_MySQL, Maybe_Backup_MariaDB_Before_Upgrade, Backup_MariaDB_Before_Upgrade, Migrate_MariaDB_To_UTF8
- `upgrade_modules/04_git_url.sh` - Pre_Upgrade_Setup_Git_URL
- `upgrade_modules/05_repository.sh` - Pre_Upgrade_Setup_Repository (~490 lines)
- `upgrade_modules/06_components.sh` - Download_Requirement, Pre_Upgrade_Required_Components
- `upgrade_modules/07_branch_input.sh` - Pre_Upgrade_Branch_Input
- `upgrade_modules/08_main_upgrade.sh` - Main_Upgrade
- `upgrade_modules/09_sync.sh` - Sync_CyberCP_To_Latest
- `upgrade_modules/10_post_tweak.sh` - Post_Upgrade_System_Tweak
- `upgrade_modules/11_display_final.sh` - Post_Install_Display_Final_Info, _br, _bl, _b

## Line Ranges in Current Script

- 00_common: 99-106, 237-263, 264-337
- 01_variables: 27-98
- 02_checks: 107-148, 149-206, 207-236, 352-399
- 03_mariadb: 425-520
- 04_git_url: 400-424
- 05_repository: 521-1011
- 06_components: 1012-1298
- 07_branch_input: 1299-1311
- 08_main_upgrade: 1312-1649
- 09_sync: 1650-1688
- 10_post_tweak: 1691-2023
- 11_display_final: 2024-2118

## Main Script After Refactor

1. Root check, Sudo_Test
2. If upgrade_modules/ exists: source each 00-11; else (one-liner) download modules from GitHub by branch and source
3. Set_Default_Variables, Check_Root, Check_Server_IP, Check_OS, Check_Provider, Check_Argument
4. Branch and MariaDB prompts
5. Pre_Upgrade_Setup_Repository, Pre_Upgrade_Setup_Git_URL, Pre_Upgrade_Required_Components
6. Main_Upgrade, Sync_CyberCP_To_Latest, Post_Upgrade_System_Tweak, Post_Install_Display_Final_Info

## Status

Done: 00_common.sh, 01_variables.sh. Remaining: create 02-11 and refactor main script to loader.
