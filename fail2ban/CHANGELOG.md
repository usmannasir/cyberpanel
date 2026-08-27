## 2026-08-07 - SQLite hardening

- Install/run `scripts/fail2ban-db-maintain.sh` to repair and prevent `database disk image is malformed`
- Enables WAL mode, daily integrity timer, and safer systemd CPU/stop settings
- Wired into `install.sh` for future installs

## 1.4.1 (2026-08-05)

- Security Logs: paginated viewer (default 5/page), dark mobile-friendly cards, Clear log with confirmation.
- Fix log read via allowlisted sudo helper; opaque Manage modal CSS in CPUI assets.

## 1.4.0 (2026-08-05)

- Unified UI: tabs in URL, banned/whitelist pagination and search, Manage modal, firewall sync, opaque dark-mode modal.
- Requires CyberPanel 2.5.5+ (meta min_version).

# Changelog - Fail2ban Security Manager

All notable changes to this plugin will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.3] - 2026-02-02

### Added
- PM2 Manager-style dashboard: header with Live indicator, action buttons, cleaner tab navigation
- Go To dashboard button on settings page (like PM2 Manager)
- sudo permission for journalctl so Recent Activity shows fail2ban logs when service is running

### Fixed
- Overview tab content nesting (tabs now switch correctly)
- Hash-based tab loading (#overview, #jails, etc.) on page load
- extraCSS block changed to header_scripts so styles load in CyberPanel base template
- Recent Activity always showing "No recent activity" when fail2ban is running (journalctl now runs with sudo)

### Changed
- Removed aggressive CSS reset (all: initial) that broke layout
- Tab styling: pill-style active state, PM2 Manager color scheme (#5856d6)
- Status cards styling to match PM2 Manager stat-card design

## [1.0.2] - 2026-02-01

### Changed
- **Category normalization**: Updated meta.xml `<type>` from `security` to `Security` for consistency with Plugin Store categories (Utility, Security, Backup, Performance). The "Plugin" category has been removed.

## [1.0.1] - 2026-01-26

### Fixed
- **JavaScript Function Scope Issues**: Fixed `Uncaught ReferenceError` for missing functions:
  - `showAddWhitelistModal()` - Now defined at top of script block for global scope
  - `showAddBlacklistModal()` - Now defined at top of script block for global scope
  - `refreshBannedIPs()` - Now defined at top of script block for global scope
  - `refreshLogs()` - Now defined at top of script block for global scope
  - `refreshStatistics()` - Now defined at top of script block for global scope
- **Function Availability**: Moved all utility functions (`getCookie`, `showAlert`, `closeModal`, `refreshJails`) to the top of the script block to ensure they're available immediately when the page loads, before any onclick handlers are called
- **Error Handling**: Added proper null checks and error logging in modal and refresh functions

### Changed
- **Code Organization**: Reorganized JavaScript code structure to define utility functions first, ensuring proper function hoisting and global scope availability
- **Function Definitions**: All onclick handler functions are now defined in global scope at the top of the script block

### Technical Details
- Functions were previously defined later in the script, causing `ReferenceError` when buttons were clicked before full script execution
- All functions are now hoisted to the top of the script block (lines 1052-1138) for immediate availability
- Added defensive programming with element existence checks and console error logging

## [1.0.0] - 2026-01-25

### Added
- Initial release of Fail2ban Security Manager plugin
- Real-time fail2ban monitoring and management
- IP whitelist/blacklist management
- Jail configuration and control
- Mobile-friendly responsive UI
- Security statistics and analytics
- Automated threat detection
- Email notifications
- Log analysis and reporting
- Unified settings page with tabbed interface
- Comprehensive API endpoints for all operations
- Singleton pattern for settings management
- Database models for persistent IP management
