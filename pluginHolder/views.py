# -*- coding: utf-8 -*-
from django.shortcuts import render, redirect
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from plogical.mailUtilities import mailUtilities
import os
import shutil
import subprocess
import shlex
import json
import re
from datetime import datetime, timedelta
from xml.etree import ElementTree
from plogical.httpProc import httpProc
from plogical.plugin_acl import user_can_manage_plugins, deny_plugin_manage_json_response
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
import sys
import urllib.request
import urllib.error
import time
import threading
import inspect
sys.path.append('/usr/local/CyberCP')
from pluginInstaller.pluginInstaller import pluginInstaller
from .patreon_verifier import PatreonVerifier

# Plugin state file location
PLUGIN_STATE_DIR = '/home/cyberpanel/plugin_states'

# Plugin store cache configuration
PLUGIN_STORE_CACHE_DIR = '/home/cyberpanel/plugin_store_cache'
PLUGIN_STORE_CACHE_FILE = os.path.join(PLUGIN_STORE_CACHE_DIR, 'plugins_cache.json')
PLUGIN_STORE_CACHE_DURATION = 3600  # Base cache duration: 1 hour (3600 seconds)
PLUGIN_STORE_CACHE_RANDOM_OFFSET = 600  # Random offset: ±10 minutes (600 seconds) to prevent simultaneous requests
PLUGIN_STORE_REFRESH_LOCK_FILE = os.path.join(PLUGIN_STORE_CACHE_DIR, 'plugins_cache_refresh.lock')
PLUGIN_STORE_REFRESH_LOCK_STALE_SECONDS = 900  # 15 minutes; remove leftover lock if stuck
GITHUB_REPO_API = 'https://api.github.com/repos/master3395/cyberpanel-plugins/contents'
GITHUB_RAW_BASE = 'https://raw.githubusercontent.com/master3395/cyberpanel-plugins/main'
GITHUB_COMMITS_API = 'https://api.github.com/repos/master3395/cyberpanel-plugins/commits'

# Plugin backup configuration
PLUGIN_BACKUP_DIR = '/home/cyberpanel/plugin_backups'

# Plugin source paths (checked in order; first match wins for install)
PLUGIN_SOURCE_PATHS = ['/home/cyberpanel/plugins', '/home/cyberpanel-plugins']

# Builtin/core plugins that are part of CyberPanel (not user-installable plugins)
# These plugins show "Built-in" badge and only Settings button (no Deactivate/Uninstall)
BUILTIN_PLUGINS = frozenset(['emailMarketing', 'emailPremium'])


def _resolve_logged_in_plugin_identity(request):
    """
    CyberPanel often authenticates via session userID (not Django auth user).
    Use Administrator email when available, otherwise username.
    """
    candidates = []
    try:
        if getattr(request, 'user', None) and request.user.is_authenticated:
            u = request.user
            email = getattr(u, 'email', None) or ''
            if email:
                candidates.append(email)
            uname = getattr(u, 'username', None) or ''
            if uname:
                candidates.append(uname)
    except Exception:
        pass
    try:
        uid = request.session.get('userID') if hasattr(request, 'session') else None
        if uid:
            from loginSystem.models import Administrator
            admin = Administrator.objects.filter(pk=uid).only('email', 'userName').first()
            if admin:
                if getattr(admin, 'email', '') and str(admin.email).lower() != 'none':
                    candidates.append(str(admin.email))
                if getattr(admin, 'userName', ''):
                    candidates.append(str(admin.userName))
    except Exception:
        pass
    for item in candidates:
        item = (item or '').strip()
        if item:
            return item.lower()
    return ''


def _install_plugin_compat(plugin_name, zip_path_abs):
    """
    Call pluginInstaller.installPlugin with zip_path when supported (newer CyberPanel).
    Older installs only accept installPlugin(pluginName) and expect pluginName.zip in CWD.
    """
    zip_path_abs = os.path.abspath(zip_path_abs)
    work_dir = os.path.dirname(zip_path_abs)
    use_zip_kw = False
    try:
        sig = inspect.signature(pluginInstaller.installPlugin)
        use_zip_kw = 'zip_path' in sig.parameters
    except (TypeError, ValueError):
        use_zip_kw = False
    if use_zip_kw:
        pluginInstaller.installPlugin(plugin_name, zip_path=zip_path_abs)
        return
    prev_cwd = os.getcwd()
    try:
        os.chdir(work_dir)
        expected_zip = os.path.join(work_dir, plugin_name + '.zip')
        if zip_path_abs != expected_zip:
            shutil.copy2(zip_path_abs, expected_zip)
        pluginInstaller.installPlugin(plugin_name)
    finally:
        try:
            os.chdir(prev_cwd)
        except Exception:
            pass

# Core CyberPanel app dirs under /usr/local/CyberCP that must not be counted as "installed plugins"
# (matches pluginHolder.urls so Installed count = store/plugin dirs only, not core apps)
RESERVED_PLUGIN_DIRS = frozenset([
    'api', 'backup', 'baseTemplate', 'cloudAPI', 'CLManager', 'containerization', 'CyberCP',
    'databases', 'dns', 'dockerManager', 'emailMarketing', 'emailPremium', 'filemanager',
    'firewall', 'ftp', 'highAvailability', 'IncBackups', 'loginSystem', 'mailServer',
    'managePHP', 'manageSSL', 'manageServices', 'packages', 'pluginHolder', 'plogical',
    'pluginInstaller', 'serverLogs', 'serverStatus', 's3Backups', 'tuning', 'userManagment',
    'websiteFunctions', 'aiScanner', 'dns', 'help', 'installed',
])


def _is_safe_plugin_store_name(plugin_name):
    """Reject path traversal and reserved/core names for plugin directory identifiers."""
    if not plugin_name or not isinstance(plugin_name, str):
        return False
    if len(plugin_name) > 128:
        return False
    if plugin_name in BUILTIN_PLUGINS or plugin_name in RESERVED_PLUGIN_DIRS:
        return False
    if '..' in plugin_name or '/' in plugin_name or '\\' in plugin_name:
        return False
    return bool(re.match(r'^[A-Za-z][A-Za-z0-9_]*$', plugin_name))


def _find_plugin_prefix_in_archive(namelist, plugin_name):
    """
    Find the path prefix for a plugin inside a GitHub archive (e.g. repo-main/pluginName/ or repo-main/Category/pluginName/).
    Returns (top_level, plugin_prefix) or (None, None) if not found.
    """
    top_level = None
    for name in namelist:
        if '/' in name:
            top_level = name.split('/')[0]
            break
    if not top_level:
        return None, None
    plugin_name_lower = plugin_name.lower()
    # Check every path: find one that has a segment equal to plugin_name (e.g. .../pm2Manager/ or .../snappymailAdmin/)
    for name in namelist:
        if '/' not in name:
            continue
        parts = name.split('/')
        # parts[0] = top_level, then we need a segment that matches plugin_name
        for i in range(1, len(parts)):
            if parts[i].lower() == plugin_name_lower:
                # Plugin folder is at top_level/parts[1]/.../parts[i]/
                prefix_parts = [top_level] + parts[1:i + 1]
                plugin_prefix = '/'.join(prefix_parts) + '/'
                return top_level, plugin_prefix
    return top_level, None


def _get_plugin_source_path(plugin_name):
    """Return the full path to a plugin's source directory, or None if not found."""
    for base in PLUGIN_SOURCE_PATHS:
        path = os.path.join(base, plugin_name)
        meta_path = os.path.join(path, 'meta.xml')
        if os.path.isdir(path) and os.path.exists(meta_path):
            return path
    return None

def _get_local_plugin_meta_modify_pair(plugin_name):
    """
    Return (modify_date string server-local, unix seconds) from first found meta.xml.
    Unix seconds represent the same instant everywhere; UI formats in browser timezone.
    """
    candidate_paths = []

    installed_meta = os.path.join('/usr/local/CyberCP', plugin_name, 'meta.xml')
    candidate_paths.append(installed_meta)

    for base in PLUGIN_SOURCE_PATHS:
        candidate_paths.append(os.path.join(base, plugin_name, 'meta.xml'))

    for meta_path in candidate_paths:
        try:
            if os.path.exists(meta_path) and os.path.isfile(meta_path):
                modify_time = os.path.getmtime(meta_path)
                return (
                    datetime.fromtimestamp(modify_time).strftime('%Y-%m-%d %H:%M:%S'),
                    int(modify_time),
                )
        except Exception:
            continue

    return ('N/A', None)


def _get_local_plugin_meta_modify_date(plugin_name):
    """
    Compute plugin modify date from local meta.xml file timestamps.
    This avoids per-plugin GitHub commits API calls while still providing
    a useful "Modify date" column in the plugin store UI.
    """
    return _get_local_plugin_meta_modify_pair(plugin_name)[0]


def _apply_modify_date_from_meta_path(data_dict, meta_xml_path):
    """Set modify_date, modify_timestamp, freshness_badge on plugin data dict."""
    modify_date = 'N/A'
    modify_timestamp = None
    try:
        if meta_xml_path and os.path.exists(meta_xml_path):
            modify_time = os.path.getmtime(meta_xml_path)
            modify_date = datetime.fromtimestamp(modify_time).strftime('%Y-%m-%d %H:%M:%S')
            modify_timestamp = int(modify_time)
    except Exception:
        pass
    data_dict['modify_date'] = modify_date
    data_dict['modify_timestamp'] = modify_timestamp
    data_dict['freshness_badge'] = _get_freshness_badge(modify_date)

def _ensure_plugin_meta_xml(plugin_name):
    """
    If plugin is installed (directory exists) but meta.xml is missing,
    restore it from source or from GitHub so the grid and version checks work.
    """
    installed_dir = os.path.join('/usr/local/CyberCP', plugin_name)
    installed_meta = os.path.join(installed_dir, 'meta.xml')
    if not os.path.isdir(installed_dir) or os.path.exists(installed_meta):
        return
    source_path = _get_plugin_source_path(plugin_name)
    if source_path:
        source_meta = os.path.join(source_path, 'meta.xml')
        if os.path.exists(source_meta):
            try:
                shutil.copy2(source_meta, installed_meta)
                logging.writeToFile(f"Restored meta.xml for {plugin_name} from source")
            except Exception as e:
                logging.writeToFile(f"Could not restore meta.xml for {plugin_name}: {e}")
            return

    # Performance: do not call GitHub during /plugins/installed render path.
    # If meta.xml is still missing, we just skip enrichment for this plugin.
    logging.writeToFile(
        f"meta.xml still missing for {plugin_name}; GitHub sync skipped for performance"
    )
    return

def _get_plugin_state_file(plugin_name):
    """Get the path to the plugin state file"""
    if not os.path.exists(PLUGIN_STATE_DIR):
        os.makedirs(PLUGIN_STATE_DIR, mode=0o755)
    return os.path.join(PLUGIN_STATE_DIR, plugin_name + '.state')

def _is_plugin_enabled(plugin_name):
    """Check if a plugin is enabled"""
    state_file = _get_plugin_state_file(plugin_name)
    if os.path.exists(state_file):
        try:
            with open(state_file, 'r') as f:
                state = f.read().strip()
                return state == 'enabled'
        except:
            return True  # Default to enabled if file read fails
    return True  # Default to enabled if state file doesn't exist


def _get_freshness_badge(modify_date):
    """
    Return freshness badge (NEW/Stable/STALE) based on modify_date.
    modify_date format: 'YYYY-MM-DD HH:MM:SS' or 'N/A'
    - 0-90 days: NEW (yellow)
    - 90-365 days: Stable (green)
    - 730+ days: STALE (red)
    - 365-730 days: no badge
    """
    if not modify_date or modify_date == 'N/A' or not isinstance(modify_date, str):
        return None
    try:
        dt = datetime.strptime(modify_date[:19], '%Y-%m-%d %H:%M:%S')
        days_ago = (datetime.now() - dt).days
        if days_ago <= 90:
            return {'badge': 'NEW', 'class': 'freshness-badge-new', 'title': 'This plugin was released/updated within the last 3 months'}
        elif days_ago <= 365:
            return {'badge': 'Stable', 'class': 'freshness-badge-stable', 'title': 'This plugin was updated within the last year'}
        elif days_ago < 730:
            return {'badge': 'Unstable', 'class': 'freshness-badge-unstable', 'title': 'This plugin has not been updated in over 1 year'}
        else:
            return {'badge': 'STALE', 'class': 'freshness-badge-stale', 'title': 'This plugin has not been updated in over 2 years'}
    except (ValueError, TypeError):
        pass
    return None

def _set_plugin_state(plugin_name, enabled):
    """Set plugin enabled/disabled state"""
    state_file = _get_plugin_state_file(plugin_name)
    try:
        with open(state_file, 'w') as f:
            f.write('enabled' if enabled else 'disabled')
        os.chmod(state_file, 0o644)
        return True
    except Exception as e:
        logging.writeToFile(f"Error writing plugin state for {plugin_name}: {str(e)}")
        return False

def help_page(request):
    """Display plugin development help page"""
    mailUtilities.checkHome()
    proc = httpProc(request, 'pluginHolder/help.html', {}, 'managePlugins')
    return proc.render()

def installed(request):
    mailUtilities.checkHome()
    installedPath = '/usr/local/CyberCP'
    pluginList = []
    errorPlugins = []
    processed_plugins = set()  # Track which plugins we've already processed

    # Timing instrumentation for /plugins/installed slowness
    t_total_start = time.perf_counter()
    t_repair_start = t_total_start
    t_repair = 0.0
    repair_attempts = 0
    t_source_loop_start = None
    t_source_loop = 0.0
    t_installed_fallback_start = None
    t_installed_fallback = 0.0
    t_filesystem_count_start = None

    # Repair pass: ensure every installed plugin dir has meta.xml (from source or GitHub) so counts and grid are correct
    if os.path.exists(installedPath):
        for plugin in os.listdir(installedPath):
            if plugin.startswith('.') or plugin in RESERVED_PLUGIN_DIRS:
                continue
            plugin_dir = os.path.join(installedPath, plugin)
            if os.path.isdir(plugin_dir):
                repair_attempts += 1
                _ensure_plugin_meta_xml(plugin)
        t_repair = time.perf_counter() - t_repair_start

    # First, process plugins from source directories (multiple paths: /home/cyberpanel/plugins, /home/cyberpanel-plugins)
    # BUT: Skip plugins that are already installed - we'll process those from the installed location instead
    t_source_loop_start = time.perf_counter()
    for pluginPath in PLUGIN_SOURCE_PATHS:
        if not os.path.exists(pluginPath):
            continue
        try:
            dirs_in_path = [p for p in os.listdir(pluginPath) if os.path.isdir(os.path.join(pluginPath, p))]
            logging.writeToFile(f"Plugin source path {pluginPath}: directories {sorted(dirs_in_path)}")
        except Exception as e:
            logging.writeToFile(f"Plugin source path {pluginPath}: listdir error {e}")
        for plugin in os.listdir(pluginPath):
            if plugin in processed_plugins:
                continue
            # Skip files (like .zip files) - only process directories
            pluginDir = os.path.join(pluginPath, plugin)
            if not os.path.isdir(pluginDir):
                continue
            
            # Use same "installed" criterion as install endpoint: plugin directory in /usr/local/CyberCP/
            installed_dir = os.path.join(installedPath, plugin)
            completePath = os.path.join(installedPath, plugin, 'meta.xml')
            if os.path.exists(completePath):
                # Plugin is fully installed (dir + meta.xml), skip - second loop will add it
                continue
            
            data = {}
            # Try installed location first, then fallback to source location
            sourcePath = os.path.join(pluginDir, 'meta.xml')
            
            # Determine which meta.xml to use
            metaXmlPath = None
            if os.path.exists(completePath):
                metaXmlPath = completePath
            elif os.path.exists(sourcePath):
                # Plugin not installed but has source meta.xml - use it
                metaXmlPath = sourcePath
            
            # Add error handling to prevent 500 errors
            try:
                if metaXmlPath is None:
                    # No meta.xml found in either location - skip (log for diagnostics)
                    logging.writeToFile(f"Plugin {plugin}: skipped (no meta.xml in source or installed)")
                    continue
                
                pluginMetaData = ElementTree.parse(metaXmlPath)
                root = pluginMetaData.getroot()
                
                # Validate required fields exist (handle both <plugin> and <cyberpanelPluginConfig> formats)
                name_elem = root.find('name')
                type_elem = root.find('type')
                desc_elem = root.find('description')
                version_elem = root.find('version')
                
                # All fields required including type (category) - no default
                if name_elem is None or type_elem is None or desc_elem is None or version_elem is None:
                    errorPlugins.append({'name': plugin, 'error': 'Missing required metadata fields (name, type/category, description, or version)'})
                    logging.writeToFile(f"Plugin {plugin}: Missing required metadata fields in meta.xml")
                    continue
                
                # Check if text is None or empty (all required)
                type_text = type_elem.text.strip() if type_elem.text else ''
                if name_elem.text is None or desc_elem.text is None or version_elem.text is None or not type_text:
                    errorPlugins.append({'name': plugin, 'error': 'Empty metadata fields (name, type/category, description, or version required)'})
                    logging.writeToFile(f"Plugin {plugin}: Empty metadata fields in meta.xml")
                    continue
                
                # Valid categories only: Utility, Security, Backup, Performance (Plugin category removed)
                if type_text.lower() not in ('utility', 'security', 'backup', 'performance', 'monitoring', 'integration', 'email', 'development', 'analytics'):
                    errorPlugins.append({'name': plugin, 'error': f'Invalid category "{type_text}". Use: Utility, Security, Backup, or Performance.'})
                    logging.writeToFile(f"Plugin {plugin}: Invalid category '{type_text}'")
                    continue
                
                data['name'] = name_elem.text
                data['type'] = type_text
                data['desc'] = desc_elem.text
                data['version'] = version_elem.text
                data['plugin_dir'] = plugin  # Plugin directory name
                # Set builtin flag (core CyberPanel plugins vs user-installable plugins)
                data['builtin'] = plugin in BUILTIN_PLUGINS
                # Installed = plugin directory exists (must match install endpoint which uses directory existence)
                # Fixes grid showing "Not Installed" when directory exists but meta.xml is missing
                data['installed'] = os.path.isdir(installed_dir)
                
                # Get plugin enabled state (only for installed plugins)
                if data['installed']:
                    data['enabled'] = _is_plugin_enabled(plugin)
                else:
                    data['enabled'] = False
                
                # Initialize is_paid to False by default (will be set later if paid)
                data['is_paid'] = False
                data['patreon_tier'] = None
                data['patreon_url'] = None
                
                # Get modify date from local file (fast, no API calls)
                # GitHub commit dates are fetched in the plugin store, not here to avoid timeouts
                _apply_modify_date_from_meta_path(data, metaXmlPath)
                
                # Extract settings URL or main URL for "Manage" button
                settings_url_elem = root.find('settings_url')
                url_elem = root.find('url')
                
                # Priority: settings_url > url > default pattern
                # Special handling for core plugins that don't use /plugins/ prefix
                if plugin == 'emailMarketing':
                    # emailMarketing is a core CyberPanel plugin, uses /emailMarketing/ not /plugins/emailMarketing/
                    data['manage_url'] = '/emailMarketing/'
                elif settings_url_elem is not None and settings_url_elem.text:
                    data['manage_url'] = settings_url_elem.text
                elif url_elem is not None and url_elem.text:
                    data['manage_url'] = url_elem.text
                else:
                    # Default: try /plugins/{plugin_dir}/settings/ or /plugins/{plugin_dir}/
                    # Only set if plugin is installed (we can't know if the URL exists otherwise)
                    # Special handling for emailMarketing
                    if plugin == 'emailMarketing':
                        data['manage_url'] = '/emailMarketing/'
                    elif data['installed']:
                        # Plugin directory exists; use main plugin URL
                        main_route = f'/plugins/{plugin}/'
                        data['manage_url'] = main_route
                    else:
                        data['manage_url'] = None
                
                # Extract author information
                author_elem = root.find('author')
                if author_elem is not None and author_elem.text:
                    data['author'] = author_elem.text
                else:
                    data['author'] = 'Unknown'
                
                # Extract paid plugin information
                paid_elem = root.find('paid')
                patreon_tier_elem = root.find('patreon_tier')
                
                if paid_elem is not None and paid_elem.text and paid_elem.text.lower() == 'true':
                    data['is_paid'] = True
                    data['patreon_tier'] = patreon_tier_elem.text if patreon_tier_elem is not None and patreon_tier_elem.text else 'CyberPanel Paid Plugin'
                    data['patreon_url'] = root.find('patreon_url').text if root.find('patreon_url') is not None else 'https://www.patreon.com/c/newstargeted/membership'
                else:
                    data['is_paid'] = False
                    data['patreon_tier'] = None
                    data['patreon_url'] = None

                pluginList.append(data)
                processed_plugins.add(plugin)  # Mark as processed
            except ElementTree.ParseError as e:
                errorPlugins.append({'name': plugin, 'error': f'XML parse error: {str(e)}'})
                logging.writeToFile(f"Plugin {plugin}: XML parse error - {str(e)}")
                # Don't mark as processed if it failed - let installed check handle it
                if not os.path.isdir(installed_dir):
                    continue
                continue
            except Exception as e:
                errorPlugins.append({'name': plugin, 'error': f'Error loading plugin: {str(e)}'})
                logging.writeToFile(f"Plugin {plugin}: Error loading - {str(e)}")
                if not os.path.isdir(installed_dir):
                    continue
                continue
    
    # Also check for installed plugins that don't have source directories
    # This handles plugins installed from the store that may not be in /home/cyberpanel/plugins/
    if os.path.exists(installedPath):
        t_source_loop = time.perf_counter() - t_source_loop_start
        t_installed_fallback_start = time.perf_counter()
        for plugin in os.listdir(installedPath):
            # Skip if already processed
            if plugin in processed_plugins:
                continue
            
            # Only check directories that look like plugins (have meta.xml)
            pluginInstalledDir = os.path.join(installedPath, plugin)
            if not os.path.isdir(pluginInstalledDir):
                continue
            
            _ensure_plugin_meta_xml(plugin)
            metaXmlPath = os.path.join(pluginInstalledDir, 'meta.xml')
            if not os.path.exists(metaXmlPath):
                continue
            
            # This is an installed plugin without a source directory - process it
            try:
                data = {}
                pluginMetaData = ElementTree.parse(metaXmlPath)
                root = pluginMetaData.getroot()
                
                # Validate required fields (including type/category - no default)
                name_elem = root.find('name')
                type_elem = root.find('type')
                desc_elem = root.find('description')
                version_elem = root.find('version')
                
                if name_elem is None or type_elem is None or desc_elem is None or version_elem is None:
                    errorPlugins.append({'name': plugin, 'error': 'Missing required metadata (name, type/category, description, or version)'})
                    continue
                
                type_text = type_elem.text.strip() if type_elem.text else ''
                if name_elem.text is None or desc_elem.text is None or version_elem.text is None or not type_text:
                    errorPlugins.append({'name': plugin, 'error': 'Empty metadata (type/category required)'})
                    continue
                
                # Valid categories only: Utility, Security, Backup, Performance (Plugin category removed)
                if type_text.lower() not in ('utility', 'security', 'backup', 'performance', 'monitoring', 'integration', 'email', 'development', 'analytics'):
                    errorPlugins.append({'name': plugin, 'error': f'Invalid category "{type_text}". Use: Utility, Security, Backup, or Performance.'})
                    continue
                
                data['name'] = name_elem.text
                data['type'] = type_text
                data['desc'] = desc_elem.text
                data['version'] = version_elem.text
                data['plugin_dir'] = plugin
                # Set builtin flag (core CyberPanel plugins vs user-installable plugins)
                data['builtin'] = plugin in BUILTIN_PLUGINS
                data['installed'] = True  # This is an installed plugin
                data['enabled'] = _is_plugin_enabled(plugin)
                
                # Initialize is_paid to False by default (will be set later if paid)
                data['is_paid'] = False
                data['patreon_tier'] = None
                data['patreon_url'] = None
                
                # Get modify date from installed location
                _apply_modify_date_from_meta_path(data, metaXmlPath)
                
                # Extract settings URL or main URL
                settings_url_elem = root.find('settings_url')
                url_elem = root.find('url')
                
                # Priority: settings_url > url > default pattern
                # Special handling for core plugins that don't use /plugins/ prefix
                if plugin == 'emailMarketing':
                    # emailMarketing is a core CyberPanel plugin, uses /emailMarketing/ not /plugins/emailMarketing/
                    data['manage_url'] = '/emailMarketing/'
                elif settings_url_elem is not None and settings_url_elem.text:
                    data['manage_url'] = settings_url_elem.text
                elif url_elem is not None and url_elem.text:
                    data['manage_url'] = url_elem.text
                else:
                    # Default to /plugins/{plugin}/ for regular plugins
                    # Special handling for emailMarketing
                    if plugin == 'emailMarketing':
                        data['manage_url'] = '/emailMarketing/'
                    else:
                        # Default to main plugin route (most plugins work from main route)
                        data['manage_url'] = f'/plugins/{plugin}/'
                
                # Extract author information
                author_elem = root.find('author')
                if author_elem is not None and author_elem.text:
                    data['author'] = author_elem.text
                else:
                    data['author'] = 'Unknown'
                
                # Extract paid plugin information (is_paid already initialized to False above)
                paid_elem = root.find('paid')
                patreon_tier_elem = root.find('patreon_tier')
                
                if paid_elem is not None and paid_elem.text and paid_elem.text.lower() == 'true':
                    data['is_paid'] = True
                    data['patreon_tier'] = patreon_tier_elem.text if patreon_tier_elem is not None and patreon_tier_elem.text else 'CyberPanel Paid Plugin'
                    patreon_url_elem = root.find('patreon_url')
                    data['patreon_url'] = patreon_url_elem.text if patreon_url_elem is not None and patreon_url_elem.text else 'https://www.patreon.com/membership/27789984'
                # else: is_paid already False from initialization above

                pluginList.append(data)
                processed_plugins.add(plugin)  # Mark as processed to prevent duplicates
                
            except ElementTree.ParseError as e:
                errorPlugins.append({'name': plugin, 'error': f'XML parse error: {str(e)}'})
                logging.writeToFile(f"Installed plugin {plugin}: XML parse error - {str(e)}")
                continue
            except Exception as e:
                errorPlugins.append({'name': plugin, 'error': f'Error loading installed plugin: {str(e)}'})
                logging.writeToFile(f"Installed plugin {plugin}: Error loading - {str(e)}")
                continue
        t_installed_fallback = time.perf_counter() - t_installed_fallback_start

    # Ensure redisManager and memcacheManager load when present (fallback if missed by listdir)
    for plugin_name in ('redisManager', 'memcacheManager'):
        if plugin_name in processed_plugins:
            continue
        source_path = _get_plugin_source_path(plugin_name)
        installed_meta = os.path.join(installedPath, plugin_name, 'meta.xml')
        meta_xml_path = installed_meta if os.path.exists(installed_meta) else (os.path.join(source_path, 'meta.xml') if source_path else None)
        if not meta_xml_path or not os.path.exists(meta_xml_path):
            continue
        try:
            root = ElementTree.parse(meta_xml_path).getroot()
            name_elem = root.find('name')
            type_elem = root.find('type')
            desc_elem = root.find('description')
            version_elem = root.find('version')
            if name_elem is None or type_elem is None or desc_elem is None or version_elem is None:
                continue
            type_text = (type_elem.text or '').strip()
            if not type_text or name_elem.text is None or desc_elem.text is None or version_elem.text is None:
                continue
            if type_text.lower() not in ('utility', 'security', 'backup', 'performance', 'monitoring', 'integration', 'email', 'development', 'analytics'):
                continue
            complete_path = os.path.join(installedPath, plugin_name, 'meta.xml')
            data = {
                'name': name_elem.text,
                'type': type_text,
                'desc': desc_elem.text,
                'version': version_elem.text,
                'plugin_dir': plugin_name,
                'builtin': plugin_name in BUILTIN_PLUGINS,  # Set builtin flag
                'installed': os.path.exists(complete_path),
                'enabled': _is_plugin_enabled(plugin_name) if os.path.exists(complete_path) else False,
                'is_paid': False,
                'patreon_tier': None,
                'patreon_url': None,
                'manage_url': f'/plugins/{plugin_name}/',
                'author': root.find('author').text if root.find('author') is not None and root.find('author').text else 'Unknown',
            }
            _apply_modify_date_from_meta_path(data, meta_xml_path)
            paid_elem = root.find('paid')
            if paid_elem is not None and paid_elem.text and paid_elem.text.lower() == 'true':
                data['is_paid'] = True
                data['patreon_tier'] = 'CyberPanel Paid Plugin'
                data['patreon_url'] = root.find('patreon_url').text if root.find('patreon_url') is not None else 'https://www.patreon.com/membership/27789984'
            pluginList.append(data)
            processed_plugins.add(plugin_name)
            logging.writeToFile(f"Plugin {plugin_name}: added via fallback (source or installed)")
        except Exception as e:
            logging.writeToFile(f"Plugin {plugin_name} fallback load error: {str(e)}")

    # Calculate installed and active counts: only count real plugins (have meta.xml, not core apps)
    t_filesystem_count_start = time.perf_counter()
    installed_plugins_in_filesystem = set()
    if os.path.exists(installedPath):
        for plugin in os.listdir(installedPath):
            if plugin.startswith('.') or plugin in RESERVED_PLUGIN_DIRS:
                continue
            pluginInstalledDir = os.path.join(installedPath, plugin)
            if not os.path.isdir(pluginInstalledDir):
                continue
            if not os.path.exists(os.path.join(pluginInstalledDir, 'meta.xml')):
                continue
            installed_plugins_in_filesystem.add(plugin)
    
    installed_count = len([p for p in pluginList if p.get('installed', False)])
    active_count = len([p for p in pluginList if p.get('installed', False) and p.get('enabled', False)])
    
    # Use the larger of list count and filesystem count so header never shows less than grid
    filesystem_installed_count = len(installed_plugins_in_filesystem)
    list_installed_count = len([p for p in pluginList if p.get('installed', False)])
    if filesystem_installed_count != list_installed_count:
        logging.writeToFile(f"Plugin count: list installed={list_installed_count}, filesystem with meta.xml={filesystem_installed_count}")
    installed_count = max(list_installed_count, filesystem_installed_count)
    if active_count > installed_count:
        active_count = installed_count
    
    # Debug logging to help identify discrepancies
    logging.writeToFile(f"Plugin count: Total={len(pluginList)}, Installed={installed_count}, Active={active_count}")
    for p in pluginList:
        logging.writeToFile(f"  - {p.get('plugin_dir')}: installed={p.get('installed')}, enabled={p.get('enabled')}")

    # Get cache expiry timestamp for display (browser formats this as nb-NO)
    cache_expiry_timestamp, _ = _get_cache_expiry_time()
    cache_expired = _is_cache_expired(cache_expiry_timestamp)
    refresh_started = False
    if cache_expired:
        # If cache is stale while on Installed page, trigger best-effort background refresh.
        refresh_started = _try_start_plugin_store_refresh_background()
    
    # Local source copy under PLUGIN_SOURCE_PATHS (for "delete local copy" after uninstall)
    for p in pluginList:
        pd = p.get('plugin_dir')
        if pd:
            p['has_local_source'] = _get_plugin_source_path(pd) is not None
        else:
            p['has_local_source'] = False

    # Sort plugins A-Å by name (case-insensitive) for Grid and Table view
    pluginList.sort(key=lambda p: (p.get('name') or '').lower())
    
    # Summary timing log (keep it single-line to avoid huge logs)
    try:
        t_total = time.perf_counter() - t_total_start
        # The individual phase durations were captured immediately after their loops.
        t_filesystem_count = (time.perf_counter() - t_filesystem_count_start) if t_filesystem_count_start else 0.0
        logging.writeToFile(
            f"/plugins/installed timing: total={t_total:.3f}s repair_attempts={repair_attempts} "
            f"repair={t_repair:.3f}s source_loop={t_source_loop:.3f}s installed_fallback={t_installed_fallback:.3f}s "
            f"filesystem_count={t_filesystem_count:.3f}s pluginList={len(pluginList)} installed_count={installed_count} active_count={active_count}"
        )
    except Exception:
        # Never break page render due to logging failure.
        pass

    proc = httpProc(request, 'pluginHolder/plugins.html',
                    {'plugins': pluginList, 'error_plugins': errorPlugins,
                     'installed_count': installed_count, 'active_count': active_count,
                     'cache_expiry_timestamp': cache_expiry_timestamp,
                     'cache_expired': cache_expired,
                     'cache_refresh_started': refresh_started}, 'managePlugins')
    return proc.render()

@csrf_exempt
@require_http_methods(["POST"])
def install_plugin(request, plugin_name):
    """Install a plugin"""
    try:
        if not user_can_manage_plugins(request):
            return deny_plugin_manage_json_response(request)
        # Check if plugin source exists (in any configured source path)
        pluginSource = _get_plugin_source_path(plugin_name)
        if not pluginSource:
            return JsonResponse({
                'success': False,
                'error': f'Plugin source not found: {plugin_name} (checked: {", ".join(PLUGIN_SOURCE_PATHS)})'
            }, status=404)
        
        # Check if already installed
        pluginInstalled = '/usr/local/CyberCP/' + plugin_name
        if os.path.exists(pluginInstalled):
            return JsonResponse({
                'success': False,
                'error': f'Plugin already installed: {plugin_name}'
            }, status=400)
        
        # Create zip file for installation (pluginInstaller expects a zip)
        import tempfile
        import shutil
        import zipfile
        temp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(temp_dir, plugin_name + '.zip')
        
        # Create zip from source directory with correct structure
        # The ZIP must contain plugin_name/ directory structure for proper extraction
        plugin_zip = zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED)
        
        # Walk through source directory and add files with plugin_name prefix
        for root, dirs, files in os.walk(pluginSource):
            for file in files:
                file_path = os.path.join(root, file)
                # Calculate relative path from plugin source
                arcname = os.path.relpath(file_path, pluginSource)
                # Add plugin_name prefix to maintain directory structure
                arcname = os.path.join(plugin_name, arcname)
                plugin_zip.write(file_path, arcname)
        
        plugin_zip.close()
        
        # Verify zip file was created
        if not os.path.exists(zip_path):
            shutil.rmtree(temp_dir, ignore_errors=True)
            return JsonResponse({
                'success': False,
                'error': f'Failed to create zip file for {plugin_name}'
            }, status=500)
        
        zip_path_abs = os.path.abspath(zip_path)
        if not os.path.exists(zip_path_abs):
            raise Exception(f'Zip file not found: {zip_path_abs}')
        
        try:
            # Install using pluginInstaller (zip_path kw when supported; else legacy CWD + pluginName.zip)
            try:
                _install_plugin_compat(plugin_name, zip_path_abs)
            except Exception as install_error:
                # Log the full error for debugging
                error_msg = str(install_error)
                logging.writeToFile(f"pluginInstaller.installPlugin raised exception: {error_msg}")
                # Check if plugin directory exists despite the error
                pluginInstalled = '/usr/local/CyberCP/' + plugin_name
                if os.path.exists(pluginInstalled):
                    logging.writeToFile(f"Plugin directory exists despite error, continuing...")
                else:
                    raise Exception(f'Plugin installation failed: {error_msg}')
            
            # Wait a moment for file system to sync
            import time
            time.sleep(2)
            
            # Verify plugin was actually installed
            pluginInstalled = '/usr/local/CyberCP/' + plugin_name
            if not os.path.exists(pluginInstalled):
                # Check if plugin files were extracted to root (exclude README.md - main repo has it at root)
                root_files = ['apps.py', 'meta.xml', 'urls.py', 'views.py']
                found_root_files = [f for f in root_files if os.path.exists(os.path.join('/usr/local/CyberCP', f))]
                if found_root_files:
                    raise Exception(f'Plugin installation failed: Files extracted to wrong location. Found {found_root_files} in /usr/local/CyberCP/ root instead of {pluginInstalled}/')
                raise Exception(f'Plugin installation failed: {pluginInstalled} does not exist after installation')
            
            # Set plugin to enabled by default after installation
            _set_plugin_state(plugin_name, True)
            
            _ensure_plugin_meta_xml(plugin_name)
            logging.writeToFile(f"Plugin {plugin_name} installed successfully (upload)")
            return JsonResponse({
                'success': True,
                'message': f'Plugin {plugin_name} installed successfully'
            })
        finally:
            # Cleanup
            shutil.rmtree(temp_dir, ignore_errors=True)
            
    except Exception as e:
        logging.writeToFile(f"Error installing plugin {plugin_name}: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def uninstall_plugin(request, plugin_name):
    """Uninstall a plugin - but keep source files and settings"""
    try:
        if not user_can_manage_plugins(request):
            return deny_plugin_manage_json_response(request)
        # Check if plugin is installed
        pluginInstalled = '/usr/local/CyberCP/' + plugin_name
        if not os.path.exists(pluginInstalled):
            return JsonResponse({
                'success': False,
                'error': f'Plugin not installed: {plugin_name}'
            }, status=404)
        
        # Custom uninstall that keeps source files
        # We need to remove from settings.py, urls.py, and remove installed directory
        # but NOT remove from /home/cyberpanel/plugins/
        
        # Remove from settings.py
        pluginInstaller.removeFromSettings(plugin_name)
        
        # Remove from URLs
        pluginInstaller.removeFromURLs(plugin_name)
        
        # Remove interface link
        pluginInstaller.removeInterfaceLink(plugin_name)
        
        # Remove migrations if enabled
        if pluginInstaller.migrationsEnabled(plugin_name):
            pluginInstaller.removeMigrations(plugin_name)
        
        # Remove installed directory (but keep source in /home/cyberpanel/plugins/)
        pluginInstaller.removeFiles(plugin_name)
        
        # DON'T call informCyberPanelRemoval - we want to keep the source directory
        # so users can reinstall the plugin later
        
        # Restart service
        pluginInstaller.restartGunicorn()
        
        # Keep state file - we want to remember if it was enabled/disabled
        # So user can reinstall and have same state
        
        return JsonResponse({
            'success': True,
            'message': f'Plugin {plugin_name} uninstalled successfully (source files and settings preserved)'
        })
            
    except Exception as e:
        logging.writeToFile(f"Error uninstalling plugin {plugin_name}: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def delete_plugin_source(request, plugin_name):
    """
    Remove local plugin source under PLUGIN_SOURCE_PATHS after uninstall, so the Plugin Store
    can reinstall cleanly. Does not touch /usr/local/CyberCP (must uninstall first).
    """
    try:
        if not user_can_manage_plugins(request):
            return deny_plugin_manage_json_response(request)
        if not _is_safe_plugin_store_name(plugin_name):
            return JsonResponse({
                'success': False,
                'error': 'Invalid or reserved plugin name.',
            }, status=400)

        plugin_installed = '/usr/local/CyberCP/' + plugin_name
        if os.path.exists(plugin_installed):
            return JsonResponse({
                'success': False,
                'error': (
                    'This plugin is still installed. Uninstall it first, then delete the local copy '
                    'if you want a clean reinstall from the Plugin Store.'
                ),
            }, status=400)

        removed_paths = []
        for base in PLUGIN_SOURCE_PATHS:
            if not base or not os.path.isdir(base):
                continue
            candidate = os.path.join(base, plugin_name)
            try:
                candidate_real = os.path.realpath(candidate)
                base_real = os.path.realpath(base)
                if not candidate_real.startswith(base_real + os.sep) and candidate_real != base_real:
                    logging.writeToFile(
                        'delete_plugin_source: skipped path outside base (symlink?): %s' % candidate
                    )
                    continue
            except Exception:
                continue
            if not os.path.isdir(candidate):
                continue
            meta = os.path.join(candidate, 'meta.xml')
            if not os.path.isfile(meta):
                continue
            try:
                shutil.rmtree(candidate)
                removed_paths.append(candidate)
            except Exception as rm_exc:
                logging.writeToFile(
                    'delete_plugin_source: failed to remove %s: %s' % (candidate, str(rm_exc))
                )
                return JsonResponse({
                    'success': False,
                    'error': 'Could not remove local folder: %s' % candidate,
                }, status=500)

        if not removed_paths:
            return JsonResponse({
                'success': False,
                'error': (
                    'No local plugin copy found under %s. Nothing to delete.'
                    % ', '.join(PLUGIN_SOURCE_PATHS)
                ),
            }, status=404)

        try:
            pluginInstaller.informCyberPanelRemoval(plugin_name)
        except Exception:
            pass

        try:
            state_file = _get_plugin_state_file(plugin_name)
            if os.path.isfile(state_file):
                os.remove(state_file)
        except Exception:
            pass

        try:
            _invalidate_plugin_store_cache()
        except Exception:
            pass

        logging.writeToFile(
            'delete_plugin_source: removed %s paths for %s: %s'
            % (len(removed_paths), plugin_name, removed_paths)
        )
        return JsonResponse({
            'success': True,
            'message': 'Local plugin files removed. You can install again from the Plugin Store.',
        })
    except Exception as e:
        logging.writeToFile('Error delete_plugin_source %s: %s' % (plugin_name, str(e)))
        return JsonResponse({
            'success': False,
            'error': str(e),
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def enable_plugin(request, plugin_name):
    """Enable a plugin"""
    try:
        if not user_can_manage_plugins(request):
            return deny_plugin_manage_json_response(request)
        # Check if plugin is installed
        pluginInstalled = '/usr/local/CyberCP/' + plugin_name
        if not os.path.exists(pluginInstalled):
            return JsonResponse({
                'success': False,
                'error': f'Plugin not installed: {plugin_name}'
            }, status=404)
        
        # Set plugin state to enabled
        if _set_plugin_state(plugin_name, True):
            return JsonResponse({
                'success': True,
                'message': f'Plugin {plugin_name} enabled successfully'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Failed to update plugin state'
            }, status=500)
            
    except Exception as e:
        logging.writeToFile(f"Error enabling plugin {plugin_name}: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def disable_plugin(request, plugin_name):
    """Disable a plugin"""
    try:
        if not user_can_manage_plugins(request):
            return deny_plugin_manage_json_response(request)
        # Check if plugin is installed
        pluginInstalled = '/usr/local/CyberCP/' + plugin_name
        if not os.path.exists(pluginInstalled):
            return JsonResponse({
                'success': False,
                'error': f'Plugin not installed: {plugin_name}'
            }, status=404)
        
        # Set plugin state to disabled
        if _set_plugin_state(plugin_name, False):
            return JsonResponse({
                'success': True,
                'message': f'Plugin {plugin_name} disabled successfully'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Failed to update plugin state'
            }, status=500)
            
    except Exception as e:
        logging.writeToFile(f"Error disabling plugin {plugin_name}: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
            }, status=500)

def _ensure_cache_dir():
    """Ensure cache directory exists"""
    try:
        if not os.path.exists(PLUGIN_STORE_CACHE_DIR):
            os.makedirs(PLUGIN_STORE_CACHE_DIR, mode=0o755)
    except Exception as e:
        logging.writeToFile(f"Error creating cache directory: {str(e)}")

def _get_cache_expiry_time():
    """Get the cache expiry time (when cache will be updated next)
    
    Returns:
        tuple: (expiry_timestamp, expiry_datetime_string) or (None, None) if no cache
        expiry_timestamp is Unix timestamp for JavaScript conversion to local time
    """
    try:
        if not os.path.exists(PLUGIN_STORE_CACHE_FILE):
            return None, None
        
        # Try to read stored expiry time from cache metadata
        try:
            with open(PLUGIN_STORE_CACHE_FILE, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                stored_expiry = cache_data.get('expiry_timestamp')
                if stored_expiry:
                    # Return timestamp for JavaScript to convert to local time
                    return stored_expiry, None
        except:
            pass  # Fall back to calculation if metadata not found
        
        # Fallback: calculate from file modification time (for old cache files)
        cache_mtime = os.path.getmtime(PLUGIN_STORE_CACHE_FILE)
        expiry_timestamp = cache_mtime + PLUGIN_STORE_CACHE_DURATION
        
        return expiry_timestamp, None
    except Exception as e:
        logging.writeToFile(f"Error getting cache expiry time: {str(e)}")
        return None, None


def _is_cache_expired(expiry_timestamp):
    """Return True if provided cache expiry timestamp is in the past."""
    try:
        if not expiry_timestamp:
            return False
        return float(expiry_timestamp) <= time.time()
    except Exception:
        return False

def _get_cached_plugins(allow_expired=False):
    """Get plugins from cache if available and not expired
    
    Args:
        allow_expired: If True, return cache even if expired (for fallback)
    """
    try:
        if not os.path.exists(PLUGIN_STORE_CACHE_FILE):
            return None
        
        # Read cache file to get stored expiry time
        with open(PLUGIN_STORE_CACHE_FILE, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        
        # Check expiry using stored timestamp if available, otherwise fall back to file mtime
        current_time = time.time()
        stored_expiry = cache_data.get('expiry_timestamp')
        
        if stored_expiry:
            # Use stored expiry time (with randomization)
            cache_age = current_time - (stored_expiry - cache_data.get('cache_duration', PLUGIN_STORE_CACHE_DURATION))
            is_expired = current_time >= stored_expiry
        else:
            # Fallback for old cache files without expiry metadata
            cache_mtime = os.path.getmtime(PLUGIN_STORE_CACHE_FILE)
            cache_age = current_time - cache_mtime
            is_expired = cache_age > PLUGIN_STORE_CACHE_DURATION
        
        if is_expired:
            if not allow_expired:
                logging.writeToFile(f"Plugin store cache expired (age: {cache_age:.0f}s)")
                return None
            else:
                logging.writeToFile(f"Using expired cache as fallback (age: {cache_age:.0f}s)")
        
        if not allow_expired or not is_expired:
            logging.writeToFile(f"Using cached plugin store data (age: {cache_age:.0f}s)")
        return cache_data.get('plugins', [])
    except Exception as e:
        logging.writeToFile(f"Error reading plugin store cache: {str(e)}")
        return None

def _save_plugins_cache(plugins):
    """Save plugins to cache with randomized expiry time"""
    try:
        _ensure_cache_dir()
        
        # Generate random cache duration to prevent simultaneous requests from all CyberPanel instances
        # Base duration ± random offset (e.g., 1 hour ± 10 minutes)
        import random
        random_offset = random.randint(-PLUGIN_STORE_CACHE_RANDOM_OFFSET, PLUGIN_STORE_CACHE_RANDOM_OFFSET)
        actual_cache_duration = PLUGIN_STORE_CACHE_DURATION + random_offset
        
        # Calculate expiry timestamp
        current_time = time.time()
        expiry_timestamp = current_time + actual_cache_duration
        
        cache_data = {
            'plugins': plugins,
            'cached_at': datetime.now().isoformat(),
            'expiry_timestamp': expiry_timestamp,
            'cache_duration': actual_cache_duration,
            'base_duration': PLUGIN_STORE_CACHE_DURATION,
            'random_offset': random_offset
        }
        
        with open(PLUGIN_STORE_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)
        
        expiry_datetime = datetime.fromtimestamp(expiry_timestamp)
        logging.writeToFile(f"Plugin store cache saved successfully. Expires at: {expiry_datetime.strftime('%Y-%m-%d %H:%M:%S')} (duration: {actual_cache_duration}s, offset: {random_offset:+d}s)")
    except Exception as e:
        logging.writeToFile(f"Error saving plugin store cache: {str(e)}")

def _try_start_plugin_store_refresh_background():
    """
    Best-effort background refresh of the plugin store cache.
    Returns True if a refresh thread was started, False otherwise.
    """
    lock_path = PLUGIN_STORE_REFRESH_LOCK_FILE
    try:
        _ensure_cache_dir()

        # If a previous refresh crashed and left the lock behind, remove it
        # so background refresh can resume. This is critical for hourly updates.
        try:
            if os.path.exists(lock_path):
                age_s = time.time() - os.path.getmtime(lock_path)
                if age_s > PLUGIN_STORE_REFRESH_LOCK_STALE_SECONDS:
                    try:
                        os.remove(lock_path)
                        logging.writeToFile(
                            f"Removed stale plugin store refresh lock (age: {age_s:.0f}s)"
                        )
                    except Exception:
                        pass
        except Exception:
            pass

        # Try to acquire a file lock so multiple workers don't stampede GitHub.
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
            with os.fdopen(fd, 'w') as f:
                f.write(str(os.getpid()))
        except FileExistsError:
            return False
        except Exception as e:
            logging.writeToFile(f"Plugin store refresh lock acquire failed: {str(e)}")
            return False

        def _worker():
            try:
                t0 = time.perf_counter()
                plugins = _fetch_plugins_from_github()
                if plugins:
                    _save_plugins_cache(plugins)
                    dt = time.perf_counter() - t0
                    logging.writeToFile(
                        f"Background plugin store refresh complete: plugins={len(plugins)} duration={dt:.3f}s"
                    )
                else:
                    logging.writeToFile("Background plugin store refresh: fetched 0 plugins")
            except Exception as e:
                # Avoid leaking secrets; just record the error summary.
                logging.writeToFile(f"Background plugin store refresh failed: {str(e)}")
            finally:
                try:
                    if os.path.exists(lock_path):
                        os.remove(lock_path)
                except Exception:
                    pass

        threading.Thread(target=_worker, daemon=True).start()
        return True
    except Exception as e:
        logging.writeToFile(f"Error starting plugin store background refresh: {str(e)}")
        return False

def _compare_versions(version1, version2):
    """
    Compare two version strings (semantic versioning)
    Returns: 1 if version1 > version2, -1 if version1 < version2, 0 if equal
    """
    try:
        # Split versions into parts
        v1_parts = [int(x) for x in version1.split('.')]
        v2_parts = [int(x) for x in version2.split('.')]
        
        # Pad shorter version with zeros
        max_len = max(len(v1_parts), len(v2_parts))
        v1_parts.extend([0] * (max_len - len(v1_parts)))
        v2_parts.extend([0] * (max_len - len(v2_parts)))
        
        # Compare each part
        for v1, v2 in zip(v1_parts, v2_parts):
            if v1 > v2:
                return 1
            elif v1 < v2:
                return -1
        return 0
    except:
        # Fallback to string comparison if parsing fails
        if version1 > version2:
            return 1
        elif version1 < version2:
            return -1
        return 0

def _get_installed_version(plugin_dir, plugin_install_dir):
    """Get installed version of a plugin from meta.xml.
    Supports both <plugin> and <cyberpanelPluginConfig> root elements."""
    installed_path = os.path.join(plugin_install_dir, plugin_dir)
    meta_path = os.path.join(installed_path, 'meta.xml')
    
    if os.path.exists(meta_path):
        try:
            pluginMetaData = ElementTree.parse(meta_path)
            root = pluginMetaData.getroot()
            version_elem = root.find('version')
            if version_elem is not None and version_elem.text:
                return version_elem.text.strip()
        except Exception as e:
            logging.writeToFile(f"Error reading version from {meta_path}: {str(e)}")
    
    return None


def _parse_version_from_meta_xml_bytes(content):
    """Return <version> text from meta.xml bytes, or None."""
    if not content:
        return None
    try:
        if isinstance(content, bytes):
            content = content.decode('utf-8', errors='replace')
        root = ElementTree.fromstring(content)
        ve = root.find('version')
        if ve is not None and ve.text:
            return ve.text.strip()
    except Exception as e:
        logging.writeToFile('Parse meta.xml version: %s' % str(e))
    return None


def _read_version_from_plugin_zip(zip_path, plugin_name):
    """Read version from plugin_name/meta.xml inside the plugin ZIP (upgrade archive)."""
    import zipfile
    inner = '%s/meta.xml' % plugin_name
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            names = zf.namelist()
            target = inner if inner in names else None
            if target is None:
                in_lower = inner.lower()
                for n in names:
                    if n.lower() == in_lower:
                        target = n
                        break
            if not target:
                return None
            return _parse_version_from_meta_xml_bytes(zf.read(target))
    except Exception as e:
        logging.writeToFile('read_version_from_plugin_zip: %s' % str(e))
        return None


def _write_meta_xml_from_plugin_zip(zip_path, plugin_name, plugin_install_dir='/usr/local/CyberCP'):
    """Restore meta.xml on disk from the upgrade ZIP (fallback if sync/CDN overwrote with stale data)."""
    import zipfile
    inner = '%s/meta.xml' % plugin_name
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            names = zf.namelist()
            target = inner if inner in names else None
            if target is None:
                in_lower = inner.lower()
                for n in names:
                    if n.lower() == in_lower:
                        target = n
                        break
            if not target:
                return False
            data = zf.read(target)
        meta_path = os.path.join(plugin_install_dir, plugin_name, 'meta.xml')
        d = os.path.dirname(meta_path)
        if d and not os.path.exists(d):
            os.makedirs(d, mode=0o755, exist_ok=True)
        with open(meta_path, 'wb') as f:
            f.write(data)
            f.flush()
            if hasattr(os, 'fsync'):
                try:
                    os.fsync(f.fileno())
                except Exception:
                    pass
        logging.writeToFile('Restored %s/meta.xml from upgrade ZIP' % plugin_name)
        return True
    except Exception as e:
        logging.writeToFile('_write_meta_xml_from_plugin_zip: %s' % str(e))
        return False


def _invalidate_plugin_store_cache():
    """Remove store cache so grid / upgrades-available refreshes installed vs store versions."""
    try:
        _ensure_cache_dir()
        if os.path.isfile(PLUGIN_STORE_CACHE_FILE):
            os.remove(PLUGIN_STORE_CACHE_FILE)
            logging.writeToFile('Plugin store cache invalidated after upgrade')
    except Exception as e:
        logging.writeToFile('Could not invalidate plugin store cache: %s' % str(e))


def _sync_meta_xml_from_github(plugin_name, plugin_install_dir='/usr/local/CyberCP'):
    """
    Fetch meta.xml from GitHub raw (main) and overwrite installed meta.xml.
    Never overwrites with an *older* <version> than already on disk (stale raw.githubusercontent CDN).
    """
    meta_url = '%s/%s/meta.xml?t=%s' % (GITHUB_RAW_BASE, plugin_name, int(time.time()))
    meta_path = os.path.join(plugin_install_dir, plugin_name, 'meta.xml')
    for attempt in (1, 2):
        try:
            req = urllib.request.Request(
                meta_url,
                headers={'User-Agent': 'CyberPanel-Plugin-Store/1.0', 'Cache-Control': 'no-cache'},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                content = resp.read()
            if not content:
                if attempt == 2:
                    logging.writeToFile(f"Sync meta.xml for {plugin_name}: empty response from GitHub")
                continue
            remote_ver = _parse_version_from_meta_xml_bytes(content)
            current_ver = _get_installed_version(plugin_name, plugin_install_dir)
            if current_ver and remote_ver and _compare_versions(remote_ver, current_ver) < 0:
                logging.writeToFile(
                    "Skip meta.xml sync for %s: remote %s older than installed %s (CDN/stale raw)"
                    % (plugin_name, remote_ver, current_ver)
                )
                return False
            with open(meta_path, 'wb') as f:
                f.write(content)
                f.flush()
                if hasattr(os, 'fsync'):
                    try:
                        os.fsync(f.fileno())
                    except Exception:
                        pass
            ver = _get_installed_version(plugin_name, plugin_install_dir)
            if ver:
                logging.writeToFile(f"Synced meta.xml for {plugin_name} from GitHub raw (version {ver})")
                return True
            if attempt == 2:
                logging.writeToFile(f"Sync meta.xml for {plugin_name}: wrote file but could not parse version")
        except Exception as e:
            logging.writeToFile(f"Could not sync meta.xml for {plugin_name} from GitHub (attempt {attempt}): {str(e)}")
    return False

def _create_plugin_backup(plugin_name, plugin_install_dir='/usr/local/CyberCP'):
    """
    Create a backup of a plugin before upgrade
    Returns: (backup_path, backup_info) or (None, None) on failure
    """
    try:
        # Ensure backup directory exists
        if not os.path.exists(PLUGIN_BACKUP_DIR):
            os.makedirs(PLUGIN_BACKUP_DIR, mode=0o755)
        
        plugin_path = os.path.join(plugin_install_dir, plugin_name)
        if not os.path.exists(plugin_path):
            return None, None
        
        # Get current version
        installed_version = _get_installed_version(plugin_name, plugin_install_dir) or 'unknown'
        
        # Create backup directory with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"{plugin_name}_v{installed_version}_{timestamp}"
        backup_path = os.path.join(PLUGIN_BACKUP_DIR, backup_name)
        
        # Copy plugin directory
        import shutil
        shutil.copytree(plugin_path, backup_path)
        
        # Create backup metadata
        backup_info = {
            'plugin_name': plugin_name,
            'version': installed_version,
            'timestamp': timestamp,
            'backup_path': backup_path,
            'created_at': datetime.now().isoformat()
        }
        
        # Save metadata as JSON
        metadata_file = os.path.join(backup_path, '.backup_metadata.json')
        with open(metadata_file, 'w') as f:
            json.dump(backup_info, f, indent=2)
        
        logging.writeToFile(f"Created backup for {plugin_name} version {installed_version} at {backup_path}")
        
        return backup_path, backup_info
        
    except Exception as e:
        logging.writeToFile(f"Error creating backup for {plugin_name}: {str(e)}")
        return None, None

def _get_plugin_backups(plugin_name):
    """Get list of available backups for a plugin"""
    backups = []
    
    if not os.path.exists(PLUGIN_BACKUP_DIR):
        return backups
    
    try:
        for item in os.listdir(PLUGIN_BACKUP_DIR):
            if item.startswith(plugin_name + '_'):
                backup_path = os.path.join(PLUGIN_BACKUP_DIR, item)
                if os.path.isdir(backup_path):
                    metadata_file = os.path.join(backup_path, '.backup_metadata.json')
                    if os.path.exists(metadata_file):
                        try:
                            with open(metadata_file, 'r') as f:
                                backup_info = json.load(f)
                                backups.append(backup_info)
                        except:
                            # Fallback: parse from directory name
                            parts = item.split('_')
                            if len(parts) >= 3:
                                version = parts[1].replace('v', '')
                                timestamp = '_'.join(parts[2:])
                                backups.append({
                                    'plugin_name': plugin_name,
                                    'version': version,
                                    'timestamp': timestamp,
                                    'backup_path': backup_path,
                                    'created_at': timestamp
                                })
                    else:
                        # No metadata, try to parse from directory name
                        parts = item.split('_')
                        if len(parts) >= 3:
                            version = parts[1].replace('v', '')
                            timestamp = '_'.join(parts[2:])
                            backups.append({
                                'plugin_name': plugin_name,
                                'version': version,
                                'timestamp': timestamp,
                                'backup_path': backup_path,
                                'created_at': timestamp
                            })
        
        # Sort by timestamp (newest first)
        backups.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
    except Exception as e:
        logging.writeToFile(f"Error listing backups for {plugin_name}: {str(e)}")
    
    return backups

def _restore_plugin_from_backup(plugin_name, backup_path):
    """Restore a plugin from a backup"""
    try:
        plugin_install_dir = '/usr/local/CyberCP'
        plugin_path = os.path.join(plugin_install_dir, plugin_name)
        
        # Remove current plugin installation
        if os.path.exists(plugin_path):
            import shutil
            shutil.rmtree(plugin_path)
        
        # Restore from backup
        import shutil
        shutil.copytree(backup_path, plugin_path)
        
        # Remove backup metadata file from restored plugin
        metadata_file = os.path.join(plugin_path, '.backup_metadata.json')
        if os.path.exists(metadata_file):
            os.remove(metadata_file)
        
        logging.writeToFile(f"Restored {plugin_name} from backup {backup_path}")
        
        return True
        
    except Exception as e:
        logging.writeToFile(f"Error restoring {plugin_name} from backup: {str(e)}")
        return False

def _enrich_store_plugins(plugins):
    """Enrich store plugins with installed/enabled status from local system"""
    enriched = []
    plugin_source_dir = '/home/cyberpanel/plugins'
    plugin_install_dir = '/usr/local/CyberCP'
    
    for plugin in plugins:
        plugin_dir = plugin.get('plugin_dir', '')
        if not plugin_dir:
            continue
        
        # Check if plugin is installed locally
        # Plugin is only considered "installed" if it exists in /usr/local/CyberCP/
        # Source directory presence doesn't mean installed - it just means the source files are available
        installed_path = os.path.join(plugin_install_dir, plugin_dir)
        
        plugin['installed'] = os.path.exists(installed_path)
        
        # Check if plugin is enabled (only if installed)
        if plugin['installed']:
            plugin['enabled'] = _is_plugin_enabled(plugin_dir)
            
            # Check for updates by comparing versions
            installed_version = _get_installed_version(plugin_dir, plugin_install_dir)
            store_version = plugin.get('version', '0.0.0')
            
            if installed_version and store_version:
                # Update available if store version is newer
                plugin['update_available'] = _compare_versions(store_version, installed_version) > 0
                plugin['installed_version'] = installed_version
            else:
                plugin['update_available'] = False
                plugin['installed_version'] = installed_version or 'Unknown'
        else:
            plugin['enabled'] = False
            plugin['update_available'] = False
            plugin['installed_version'] = None

        plugin['has_local_source'] = _get_plugin_source_path(plugin_dir) is not None
        plugin['builtin'] = plugin_dir in BUILTIN_PLUGINS
        
        # Ensure is_paid field exists and is properly set (default to False if not set or invalid)
        # Handle all possible cases: missing, None, empty string, string values, boolean
        is_paid_value = plugin.get('is_paid', False)
        
        # Normalize is_paid to boolean
        if is_paid_value is None or is_paid_value == '' or is_paid_value == 'false' or is_paid_value == 'False' or is_paid_value == '0':
            plugin['is_paid'] = False
        elif is_paid_value is True or is_paid_value == 'true' or is_paid_value == 'True' or is_paid_value == '1' or str(is_paid_value).lower() == 'true':
            plugin['is_paid'] = True
        elif 'is_paid' not in plugin or plugin.get('is_paid') is None:
            # Try to check from local meta.xml if available
            meta_path = None
            source_path = os.path.join(plugin_source_dir, plugin_dir)
            if os.path.exists(installed_path):
                meta_path = os.path.join(installed_path, 'meta.xml')
            elif os.path.exists(source_path):
                meta_path = os.path.join(source_path, 'meta.xml')
            
            if meta_path and os.path.exists(meta_path):
                try:
                    pluginMetaData = ElementTree.parse(meta_path)
                    root = pluginMetaData.getroot()
                    paid_elem = root.find('paid')
                    if paid_elem is not None and paid_elem.text and paid_elem.text.lower() == 'true':
                        plugin['is_paid'] = True
                    else:
                        plugin['is_paid'] = False
                except:
                    plugin['is_paid'] = False
            else:
                plugin['is_paid'] = False  # Default to free if we can't determine
        else:
            # Already set, but ensure it's boolean
            plugin['is_paid'] = bool(plugin['is_paid']) if plugin['is_paid'] not in [True, False] else plugin['is_paid']
        
        enriched.append(plugin)
    
    return enriched

def _fetch_plugins_from_github():
    """Fetch plugins from GitHub repository"""
    plugins = []
    
    try:
        # Fetch repository contents
        req = urllib.request.Request(
            GITHUB_REPO_API,
            headers={
                'User-Agent': 'CyberPanel-Plugin-Store/1.0',
                'Accept': 'application/vnd.github.v3+json'
            }
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            contents = json.loads(response.read().decode('utf-8'))
        
        # Filter for directories (plugins)
        plugin_dirs = [item for item in contents if item.get('type') == 'dir' and not item.get('name', '').startswith('.')]
        
        for plugin_dir in plugin_dirs:
            plugin_name = plugin_dir.get('name', '')
            if not plugin_name:
                continue
            
            try:
                # Fetch meta.xml from raw GitHub
                meta_xml_url = f"{GITHUB_RAW_BASE}/{plugin_name}/meta.xml"
                meta_req = urllib.request.Request(
                    meta_xml_url,
                    headers={'User-Agent': 'CyberPanel-Plugin-Store/1.0'}
                )
                
                with urllib.request.urlopen(meta_req, timeout=10) as meta_response:
                    meta_xml_content = meta_response.read().decode('utf-8')
                
                # Parse meta.xml
                root = ElementTree.fromstring(meta_xml_content)
                
                # Performance: avoid per-plugin GitHub commits API calls.
                # Instead, compute modify_date from local meta.xml timestamps
                # (installed meta.xml if present, otherwise plugin source meta.xml).
                modify_date, modify_timestamp = _get_local_plugin_meta_modify_pair(plugin_name)
                freshness = _get_freshness_badge(modify_date)
                
                # Extract paid plugin information
                paid_elem = root.find('paid')
                patreon_tier_elem = root.find('patreon_tier')
                
                is_paid = False
                patreon_tier = None
                patreon_url = None
                
                if paid_elem is not None and paid_elem.text and paid_elem.text.lower() == 'true':
                    is_paid = True
                    patreon_tier = patreon_tier_elem.text if patreon_tier_elem is not None and patreon_tier_elem.text else 'CyberPanel Paid Plugin'
                    patreon_url_elem = root.find('patreon_url')
                    patreon_url = patreon_url_elem.text if patreon_url_elem is not None else 'https://www.patreon.com/c/newstargeted/membership'
                
                # Category (type) is required - valid: Utility, Security, Backup, Performance (Plugin removed)
                type_elem = root.find('type')
                if type_elem is None or not type_elem.text or not type_elem.text.strip():
                    logging.writeToFile(f"Plugin {plugin_name}: Missing required type/category in meta.xml, skipping")
                    continue
                type_text = type_elem.text.strip().lower()
                if type_text not in ('utility', 'security', 'backup', 'performance', 'monitoring', 'integration', 'email', 'development', 'analytics'):
                    logging.writeToFile(f"Plugin {plugin_name}: Invalid category '{type_elem.text}', skipping (use Utility, Security, Backup, or Performance)")
                    continue
                
                plugin_data = {
                    'plugin_dir': plugin_name,
                    'name': root.find('name').text if root.find('name') is not None else plugin_name,
                    'type': type_elem.text.strip(),
                    'description': root.find('description').text if root.find('description') is not None else '',
                    'version': root.find('version').text if root.find('version') is not None else '1.0.0',
                    'url': root.find('url').text if root.find('url') is not None else f'/plugins/{plugin_name}/',
                    'settings_url': root.find('settings_url').text if root.find('settings_url') is not None else f'/plugins/{plugin_name}/settings/',
                    'author': root.find('author').text if root.find('author') is not None else 'Unknown',
                    'github_url': f'https://github.com/master3395/cyberpanel-plugins/tree/main/{plugin_name}',
                    'about_url': f'https://github.com/master3395/cyberpanel-plugins/tree/main/{plugin_name}',
                    'modify_date': modify_date,
                    'modify_timestamp': modify_timestamp,
                    'freshness_badge': freshness,
                    'is_paid': is_paid,
                    'patreon_tier': patreon_tier,
                    'patreon_url': patreon_url
                }
                
                plugins.append(plugin_data)
                logging.writeToFile(f"Fetched plugin: {plugin_name} (last modified: {modify_date})")
                
            except urllib.error.HTTPError as e:
                if e.code == 403:
                    # Rate limit hit - log and break
                    logging.writeToFile(f"GitHub API rate limit exceeded (403) for plugin {plugin_name}")
                    raise  # Re-raise to be caught by outer handler
                elif e.code == 404:
                    # meta.xml not found, skip this plugin
                    logging.writeToFile(f"meta.xml not found for plugin {plugin_name}, skipping")
                    continue
                else:
                    logging.writeToFile(f"HTTP error {e.code} fetching {plugin_name}: {str(e)}")
                    continue
            except Exception as e:
                logging.writeToFile(f"Error processing plugin {plugin_name}: {str(e)}")
                continue
        
        return plugins
        
    except urllib.error.HTTPError as e:
        if e.code == 403:
            error_msg = "GitHub API rate limit exceeded. Using cached data if available."
            logging.writeToFile(f"GitHub API 403 error: {error_msg}")
            raise Exception(error_msg)
        else:
            error_msg = f"GitHub API error {e.code}: {str(e)}"
            logging.writeToFile(error_msg)
            raise Exception(error_msg)
    except urllib.error.URLError as e:
        error_msg = f"Network error fetching plugins: {str(e)}"
        logging.writeToFile(error_msg)
        raise Exception(error_msg)
    except Exception as e:
        error_msg = f"Error fetching plugins from GitHub: {str(e)}"
        logging.writeToFile(error_msg)
        raise Exception(error_msg)

@csrf_exempt
@require_http_methods(["GET"])
def fetch_plugin_store(request):
    """Fetch plugins from the plugin store with caching"""
    try:
        if not user_can_manage_plugins(request):
            return deny_plugin_manage_json_response(request)
        mailUtilities.checkHome()
    except Exception as e:
        logging.writeToFile(f"fetch_plugin_store: checkHome failed: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Authentication required. Please log in again.',
            'plugins': []
        }, status=401)
    
    try:
        t_total_start = time.perf_counter()

        # 1) Fast path: non-expired cache hit
        cached_plugins = _get_cached_plugins(allow_expired=False)
        if cached_plugins is not None:
            t_enrich_start = time.perf_counter()
            enriched_plugins = _enrich_store_plugins(cached_plugins)
            dt_total = time.perf_counter() - t_total_start
            logging.writeToFile(
                f"fetch_plugin_store: cache_hit plugins={len(cached_plugins)} duration={dt_total:.3f}s enrich={time.perf_counter() - t_enrich_start:.3f}s"
            )
            return JsonResponse({
                'success': True,
                'plugins': enriched_plugins,
                'cached': True
            })

        # 2) Cache miss OR expired cache: return stale-but-available cache immediately (if present)
        stale_plugins = _get_cached_plugins(allow_expired=True)
        if stale_plugins is not None:
            started_refresh = _try_start_plugin_store_refresh_background()
            t_enrich_start = time.perf_counter()
            enriched_plugins = _enrich_store_plugins(stale_plugins)
            dt_total = time.perf_counter() - t_total_start
            warning = 'Using stale plugin store cache (refreshing in background).' if started_refresh else 'Using stale plugin store cache.'
            logging.writeToFile(
                f"fetch_plugin_store: cache_stale_fallback plugins={len(stale_plugins)} refresh_started={started_refresh} duration={dt_total:.3f}s enrich={time.perf_counter() - t_enrich_start:.3f}s"
            )
            return JsonResponse({
                'success': True,
                'plugins': enriched_plugins,
                'cached': True,
                'warning': warning
            })
        
        # 3) No cache available: fetch from GitHub (slow path)
        t_fetch_start = time.perf_counter()
        plugins = _fetch_plugins_from_github()
        dt_fetch = time.perf_counter() - t_fetch_start

        # Enrich plugins with installed/enabled status
        enriched_plugins = _enrich_store_plugins(plugins)
        
        # Save to cache (save original, not enriched, to keep cache clean)
        if plugins:
            _save_plugins_cache(plugins)
        
        dt_total = time.perf_counter() - t_total_start
        logging.writeToFile(
            f"fetch_plugin_store: cache_miss_fetched plugins={len(plugins)} fetch_duration={dt_fetch:.3f}s total_duration={dt_total:.3f}s"
        )
        return JsonResponse({
            'success': True,
            'plugins': enriched_plugins,
            'cached': False
        })
        
    except Exception as e:
        error_message = str(e)
        
        # If rate limited, try to use stale cache as fallback
        if '403' in error_message or 'rate limit' in error_message.lower():
            stale_cache = _get_cached_plugins(allow_expired=True)  # Get cache even if expired
            if stale_cache is not None:
                logging.writeToFile("Using stale cache due to rate limit")
                enriched_plugins = _enrich_store_plugins(stale_cache)
                return JsonResponse({
                    'success': True,
                    'plugins': enriched_plugins,
                    'cached': True,
                    'warning': 'Using cached data due to GitHub rate limit. Data may be outdated.'
                })
        
        # No cache available, return error
        return JsonResponse({
            'success': False,
            'error': error_message,
            'plugins': []
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def upgrade_plugin(request, plugin_name):
    """Upgrade an installed plugin from GitHub store"""
    mailUtilities.checkHome()
    
    try:
        if not user_can_manage_plugins(request):
            return deny_plugin_manage_json_response(request)
        # Check if plugin is installed
        pluginInstalled = '/usr/local/CyberCP/' + plugin_name
        if not os.path.exists(pluginInstalled):
            return JsonResponse({
                'success': False,
                'error': f'Plugin not installed: {plugin_name}'
            }, status=400)
        
        # Get current version before upgrade
        installed_version = _get_installed_version(plugin_name, '/usr/local/CyberCP')
        
        # Create automatic backup before upgrade
        backup_path, backup_info = _create_plugin_backup(plugin_name)
        if backup_path:
            logging.writeToFile(f"Created automatic backup for {plugin_name} before upgrade: {backup_path}")
        else:
            logging.writeToFile(f"Warning: Failed to create backup for {plugin_name}, continuing with upgrade anyway")
        
        logging.writeToFile(f"Starting upgrade of {plugin_name} from version {installed_version}")
        
        # Download and install plugin from GitHub (same as install_from_store)
        import tempfile
        import shutil
        import zipfile
        import io
        
        # Create temporary directory
        temp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(temp_dir, plugin_name + '.zip')
        
        try:
            # Download from GitHub
            repo_zip_url = 'https://github.com/master3395/cyberpanel-plugins/archive/refs/heads/main.zip'
            logging.writeToFile(f"Downloading plugin upgrade from: {repo_zip_url}")
            
            repo_req = urllib.request.Request(
                repo_zip_url,
                headers={
                    'User-Agent': 'CyberPanel-Plugin-Store/1.0',
                    'Accept': 'application/zip'
                }
            )
            
            with urllib.request.urlopen(repo_req, timeout=30) as repo_response:
                repo_zip_data = repo_response.read()
            
            # Extract plugin directory from repository ZIP
            repo_zip = zipfile.ZipFile(io.BytesIO(repo_zip_data))
            namelist = repo_zip.namelist()
            
            # Find plugin folder (supports flat repo or nested e.g. Category/pluginName)
            top_level, plugin_prefix = _find_plugin_prefix_in_archive(namelist, plugin_name)
            if not top_level:
                raise Exception('GitHub archive has no recognizable structure')
            if not plugin_prefix:
                sample = namelist[:15] if len(namelist) > 15 else namelist
                logging.writeToFile(f"Plugin {plugin_name} not in archive. Top-level={top_level}, sample paths: {sample}")
                raise Exception(f'Plugin {plugin_name} not found in GitHub repository (checked under {top_level}/)')
            
            plugin_files = [f for f in namelist if f.startswith(plugin_prefix)]
            if not plugin_files:
                logging.writeToFile(f"Plugin {plugin_name}: no files under prefix {plugin_prefix}")
                raise Exception(f'Plugin {plugin_name} not found in GitHub repository')
            
            logging.writeToFile(f"Found {len(plugin_files)} files for plugin {plugin_name} in GitHub (prefix {plugin_prefix})")
            
            # Create plugin ZIP with correct structure: plugin_name/... for install to /usr/local/CyberCP/plugin_name/
            plugin_zip = zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED)
            for file_path in plugin_files:
                relative_path = file_path[len(plugin_prefix):]
                if relative_path:  # Skip directory-only entries
                    file_data = repo_zip.read(file_path)
                    arcname = os.path.join(plugin_name, relative_path)
                    plugin_zip.writestr(arcname, file_data)
            
            plugin_zip.close()
            repo_zip.close()
            
            # Verify ZIP was created
            if not os.path.exists(zip_path):
                raise Exception(f'Failed to create plugin ZIP file')
            
            logging.writeToFile(f"Created plugin ZIP: {zip_path}")
            
            zip_path_abs = os.path.abspath(zip_path)
            if not os.path.exists(zip_path_abs):
                raise Exception(f'Zip file not found: {zip_path_abs}')

            expected_from_zip = _read_version_from_plugin_zip(zip_path_abs, plugin_name)
            if expected_from_zip:
                logging.writeToFile(
                    'Plugin %s: version in upgrade archive meta.xml: %s' % (plugin_name, expected_from_zip)
                )
            
            logging.writeToFile(f"Upgrading plugin using pluginInstaller (zip={zip_path_abs})")
            
            # Install using pluginInstaller (zip_path kw when supported; else legacy)
            try:
                _install_plugin_compat(plugin_name, zip_path_abs)
            except Exception as install_error:
                error_msg = str(install_error)
                logging.writeToFile(f"pluginInstaller.installPlugin raised exception: {error_msg}")
                # Check if plugin directory exists despite the error
                if not os.path.exists(pluginInstalled):
                    raise Exception(f'Plugin upgrade failed: {error_msg}')
            
            # Wait for file system to sync
            import time
            time.sleep(3)
            
            # Verify plugin was upgraded
            if not os.path.exists(pluginInstalled):
                raise Exception(f'Plugin upgrade failed: {pluginInstalled} does not exist after upgrade')
            
            # Sync meta.xml from GitHub raw (never downgrades vs disk — avoids stale CDN on raw.githubusercontent.com)
            _sync_meta_xml_from_github(plugin_name, '/usr/local/CyberCP')
            new_version = _get_installed_version(plugin_name, '/usr/local/CyberCP')
            if new_version == installed_version:
                logging.writeToFile(f"Plugin {plugin_name}: version unchanged after first meta sync, retrying sync")
                _sync_meta_xml_from_github(plugin_name, '/usr/local/CyberCP')
                new_version = _get_installed_version(plugin_name, '/usr/local/CyberCP')
            if (
                new_version == installed_version
                and expected_from_zip
                and installed_version
                and _compare_versions(expected_from_zip, installed_version) > 0
            ):
                logging.writeToFile(
                    'Plugin %s: forcing meta.xml from upgrade ZIP (archive says %s, disk still %s)'
                    % (plugin_name, expected_from_zip, installed_version)
                )
                _write_meta_xml_from_plugin_zip(zip_path_abs, plugin_name, '/usr/local/CyberCP')
                new_version = _get_installed_version(plugin_name, '/usr/local/CyberCP')
            if (
                new_version == installed_version
                and expected_from_zip
                and installed_version
                and _compare_versions(expected_from_zip, installed_version) > 0
            ):
                err = (
                    'Upgrade did not update version on disk (still %s; archive has %s). '
                    'Check ownership of /usr/local/CyberCP/%s and CyberPanel logs.'
                    % (installed_version, expected_from_zip, plugin_name)
                )
                logging.writeToFile('Plugin %s: %s' % (plugin_name, err))
                return JsonResponse({'success': False, 'error': err}, status=500)

            _invalidate_plugin_store_cache()
            logging.writeToFile(
                'Plugin %s upgraded successfully from %s to %s' % (plugin_name, installed_version, new_version)
            )
            
            backup_message = ''
            if backup_path:
                backup_message = f' Backup created at: {backup_info.get("timestamp", "unknown")}'
            
            return JsonResponse({
                'success': True,
                'message': f'Plugin {plugin_name} upgraded successfully from {installed_version} to {new_version}.{backup_message}',
                'backup_created': backup_path is not None,
                'backup_path': backup_path if backup_path else None
            })
                
        finally:
            # Cleanup
            shutil.rmtree(temp_dir, ignore_errors=True)
            
    except urllib.error.HTTPError as e:
        error_msg = f'Failed to download plugin from GitHub: HTTP {e.code}'
        if e.code == 404:
            error_msg = f'Plugin {plugin_name} not found in GitHub repository'
        logging.writeToFile(f"Error upgrading {plugin_name}: {error_msg}")
        return JsonResponse({
            'success': False,
            'error': error_msg
        }, status=500)
    except Exception as e:
        logging.writeToFile(f"Error upgrading plugin {plugin_name}: {str(e)}")
        import traceback
        error_details = traceback.format_exc()
        logging.writeToFile(f"Traceback: {error_details}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def get_plugin_backups(request, plugin_name):
    """Get list of available backups for a plugin"""
    mailUtilities.checkHome()
    
    try:
        if not user_can_manage_plugins(request):
            return deny_plugin_manage_json_response(request)
        backups = _get_plugin_backups(plugin_name)
        return JsonResponse({
            'success': True,
            'backups': backups,
            'count': len(backups)
        })
    except Exception as e:
        logging.writeToFile(f"Error getting backups for {plugin_name}: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def revert_plugin(request, plugin_name):
    """Revert a plugin to a previous version from backup"""
    mailUtilities.checkHome()
    
    try:
        if not user_can_manage_plugins(request):
            return deny_plugin_manage_json_response(request)
        # Get backup path from request
        data = json.loads(request.body)
        backup_path = data.get('backup_path')
        
        if not backup_path:
            return JsonResponse({
                'success': False,
                'error': 'Backup path is required'
            }, status=400)
        
        # Verify backup exists
        if not os.path.exists(backup_path):
            return JsonResponse({
                'success': False,
                'error': f'Backup not found: {backup_path}'
            }, status=404)
        
        # Get backup version info
        metadata_file = os.path.join(backup_path, '.backup_metadata.json')
        backup_version = 'unknown'
        if os.path.exists(metadata_file):
            try:
                with open(metadata_file, 'r') as f:
                    backup_info = json.load(f)
                    backup_version = backup_info.get('version', 'unknown')
            except:
                pass
        
        logging.writeToFile(f"Reverting {plugin_name} to version {backup_version} from backup {backup_path}")
        
        # Restore from backup
        if _restore_plugin_from_backup(plugin_name, backup_path):
            try:
                pluginInstaller.restartGunicorn()
            except Exception as re:
                logging.writeToFile(
                    'revert_plugin: restartGunicorn after restore failed (non-fatal): %s' % str(re)
                )
            return JsonResponse({
                'success': True,
                'message': f'Plugin {plugin_name} reverted successfully to version {backup_version}'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Failed to restore plugin from backup'
            }, status=500)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logging.writeToFile(f"Error reverting plugin {plugin_name}: {str(e)}")
        import traceback
        error_details = traceback.format_exc()
        logging.writeToFile(f"Traceback: {error_details}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def install_from_store(request, plugin_name):
    """Install plugin from GitHub store, with fallback to local source"""
    mailUtilities.checkHome()
    
    try:
        if not user_can_manage_plugins(request):
            return deny_plugin_manage_json_response(request)
        # Check if already installed
        pluginInstalled = '/usr/local/CyberCP/' + plugin_name
        if os.path.exists(pluginInstalled):
            return JsonResponse({
                'success': False,
                'error': f'Plugin already installed: {plugin_name}'
            }, status=400)
        
        # Download plugin from GitHub
        import tempfile
        import shutil
        import zipfile
        import io
        
        logging.writeToFile(f"Starting installation of {plugin_name} from GitHub store")
        
        # Create temporary directory
        temp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(temp_dir, plugin_name + '.zip')
        
        try:
            # Try to download from GitHub first
            use_local_fallback = False
            try:
                # Download repository as ZIP
                repo_zip_url = 'https://github.com/master3395/cyberpanel-plugins/archive/refs/heads/main.zip'
                logging.writeToFile(f"Downloading plugin from: {repo_zip_url}")
                
                repo_req = urllib.request.Request(
                    repo_zip_url,
                    headers={
                        'User-Agent': 'CyberPanel-Plugin-Store/1.0',
                        'Accept': 'application/zip'
                    }
                )
                
                with urllib.request.urlopen(repo_req, timeout=30) as repo_response:
                    repo_zip_data = repo_response.read()
                
                # Extract plugin directory from repository ZIP
                repo_zip = zipfile.ZipFile(io.BytesIO(repo_zip_data))
                namelist = repo_zip.namelist()
                
                # Find plugin folder (supports flat repo or nested e.g. Category/pluginName)
                top_level, plugin_prefix = _find_plugin_prefix_in_archive(namelist, plugin_name)
                if not top_level:
                    raise Exception('GitHub archive has no recognizable structure')
                if not plugin_prefix:
                    repo_zip.close()
                    logging.writeToFile(f"Plugin {plugin_name} not found in GitHub repository, trying local source")
                    use_local_fallback = True
                else:
                    plugin_files = [f for f in namelist if f.startswith(plugin_prefix)]
                    if not plugin_files:
                        repo_zip.close()
                        logging.writeToFile(f"Plugin {plugin_name} not found in GitHub repository, trying local source")
                        use_local_fallback = True
                    else:
                        logging.writeToFile(f"Found {len(plugin_files)} files for plugin {plugin_name} in GitHub")
                        plugin_zip = zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED)
                        for file_path in plugin_files:
                            relative_path = file_path[len(plugin_prefix):]
                            if relative_path:
                                file_data = repo_zip.read(file_path)
                                arcname = os.path.join(plugin_name, relative_path)
                                plugin_zip.writestr(arcname, file_data)
                        plugin_zip.close()
                        repo_zip.close()
            except Exception as github_error:
                logging.writeToFile(f"GitHub download failed for {plugin_name}: {str(github_error)}, trying local source")
                use_local_fallback = True
            
            # Fallback to local source if GitHub download failed
            if use_local_fallback:
                pluginSource = _get_plugin_source_path(plugin_name)
                if not pluginSource:
                    raise Exception(f'Plugin {plugin_name} not found in GitHub repository and local source not found (checked: {", ".join(PLUGIN_SOURCE_PATHS)})')
                
                logging.writeToFile(f"Using local source for {plugin_name} from {pluginSource}")
                
                # Create zip from local source directory with correct structure
                # The ZIP must contain plugin_name/ directory structure for proper extraction
                import zipfile
                plugin_zip = zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED)
                
                # Walk through source directory and add files with plugin_name prefix
                for root, dirs, files in os.walk(pluginSource):
                    for file in files:
                        file_path = os.path.join(root, file)
                        # Calculate relative path from plugin source
                        arcname = os.path.relpath(file_path, pluginSource)
                        # Add plugin_name prefix to maintain directory structure
                        arcname = os.path.join(plugin_name, arcname)
                        plugin_zip.write(file_path, arcname)
                
                plugin_zip.close()
            
            # Verify ZIP was created
            if not os.path.exists(zip_path):
                raise Exception(f'Failed to create plugin ZIP file')
            
            logging.writeToFile(f"Created plugin ZIP: {zip_path}")
            
            if not os.path.exists(zip_path):
                raise Exception(f'Zip file not found: {zip_path}')
            
            # Pass absolute path so extraction does not depend on cwd (installPlugin may change cwd)
            zip_path_abs = os.path.abspath(zip_path)
            
            logging.writeToFile(f"Installing plugin using pluginInstaller (zip={zip_path_abs})")
            
            # Install using pluginInstaller (zip_path kw when supported; else legacy)
            try:
                _install_plugin_compat(plugin_name, zip_path_abs)
            except Exception as install_error:
                # Log the full error for debugging
                error_msg = str(install_error)
                logging.writeToFile(f"pluginInstaller.installPlugin raised exception: {error_msg}")
                # Check if plugin directory exists despite the error
                pluginInstalled = '/usr/local/CyberCP/' + plugin_name
                if os.path.exists(pluginInstalled):
                    logging.writeToFile(f"Plugin directory exists despite error, continuing...")
                else:
                    raise Exception(f'Plugin installation failed: {error_msg}')
            
            # Wait a moment for file system to sync and service to restart
            import time
            time.sleep(3)  # Increased wait time for file system sync
            
            # Verify plugin was actually installed
            pluginInstalled = '/usr/local/CyberCP/' + plugin_name
            if not os.path.exists(pluginInstalled):
                # Exclude README.md - main CyberPanel repo has it at root
                root_files = ['apps.py', 'meta.xml', 'urls.py', 'views.py']
                found_root_files = [f for f in root_files if os.path.exists(os.path.join('/usr/local/CyberCP', f))]
                if found_root_files:
                    raise Exception(f'Plugin installation failed: Files extracted to wrong location. Found {found_root_files} in /usr/local/CyberCP/ root instead of {pluginInstalled}/')
                raise Exception(f'Plugin installation failed: {pluginInstalled} does not exist after installation')
            
            # Sync meta.xml from GitHub raw so version matches store
            _sync_meta_xml_from_github(plugin_name, '/usr/local/CyberCP')
            
            logging.writeToFile(f"Plugin {plugin_name} installed successfully")
            
            # Set plugin to enabled by default after installation
            _set_plugin_state(plugin_name, True)
            
            _ensure_plugin_meta_xml(plugin_name)
            return JsonResponse({
                'success': True,
                'message': f'Plugin {plugin_name} installed successfully from store'
            })
                
        finally:
            # Cleanup
            shutil.rmtree(temp_dir, ignore_errors=True)
            
    except urllib.error.HTTPError as e:
        error_msg = f'Failed to download plugin from GitHub: HTTP {e.code}'
        if e.code == 404:
            error_msg = f'Plugin {plugin_name} not found in GitHub repository'
        logging.writeToFile(f"Error installing {plugin_name}: {error_msg}")
        return JsonResponse({
            'success': False,
            'error': error_msg
        }, status=500)
    except Exception as e:
        logging.writeToFile(f"Error installing plugin {plugin_name}: {str(e)}")
        import traceback
        error_details = traceback.format_exc()
        logging.writeToFile(f"Traceback: {error_details}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def debug_loaded_plugins(request):
    """Return which plugins have URL routes loaded and which failed (for diagnosing 404s)."""
    try:
        if not user_can_manage_plugins(request):
            return deny_plugin_manage_json_response(request)
        import pluginHolder.urls as urls_mod
        loaded = list(getattr(urls_mod, '_loaded_plugins', []))
        failed = dict(getattr(urls_mod, '_failed_plugins', {}))
        return JsonResponse({
            'success': True,
            'loaded': loaded,
            'failed': failed,
            'loaded_count': len(loaded),
            'failed_count': len(failed),
        }, json_dumps_params={'indent': 2})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["GET", "POST"])
def plugin_settings_proxy(request, plugin_name):
    """
    Proxy for /plugins/<plugin_name>/settings/ so plugin settings pages work even when
    the plugin was installed after the worker started (dynamic URL list is built at import time).
    """
    import re
    import sys
    import importlib

    mailUtilities.checkHome()
    if not user_can_manage_plugins(request):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('You are not authorized to manage plugins.')

    # Basic hardening against path traversal / unexpected module names.
    if not plugin_name or not re.match(r'^[A-Za-z0-9_]+$', plugin_name):
        from django.http import HttpResponseNotFound
        return HttpResponseNotFound('Invalid plugin.')

    # Reserved internal directories / apps.
    if plugin_name in RESERVED_PLUGIN_DIRS or plugin_name in (
        'api', 'installed', 'help', 'emailMarketing', 'emailPremium', 'pluginHolder'
    ):
        from django.http import HttpResponseNotFound
        return HttpResponseNotFound('Invalid plugin.')

    installed_plugin_path = os.path.join('/usr/local/CyberCP', plugin_name)

    # Try to import plugin settings from either:
    # - installed plugin directory (/usr/local/CyberCP/<plugin_name>/)
    # - plugin source directories (/home/cyberpanel-plugins/<plugin_name>/ etc)
    # This fixes 404s when the installed copy is incomplete.
    source_candidates = []
    for src_base in PLUGIN_SOURCE_PATHS:
        src_dir = os.path.join(src_base, plugin_name)
        if os.path.isdir(src_dir):
            source_candidates.append((src_base, src_dir))

    parents_to_try = ['/usr/local/CyberCP'] + [p for (p, _) in source_candidates]

    orig_sys_path = list(sys.path)
    last_err = None
    try:
        for parent in parents_to_try:
            if not parent or not os.path.isdir(parent):
                continue

            # Ensure import searches this candidate parent first.
            if parent in sys.path:
                sys.path.remove(parent)
            sys.path.insert(0, parent)

            # Clear partially imported modules so we can retry from a different path.
            for mod_name in [plugin_name, plugin_name + '.views', plugin_name + '.urls']:
                if mod_name in sys.modules:
                    del sys.modules[mod_name]

            try:
                views_mod = importlib.import_module(plugin_name + '.views')
                # Different plugins use different view function names.
                # Common ones are:
                # - settings(request)
                # - settings_view(request)  (used by multiple first-party plugins)
                for candidate in ('settings', 'settings_view', 'settings_simple', 'unified_settings'):
                    settings_view = getattr(views_mod, candidate, None)
                    if callable(settings_view):
                        response = settings_view(request)
                        response = _inject_plugin_settings_back_bar(response)
                        return _inject_activation_store_hook(response, plugin_name)
            except ModuleNotFoundError as e:
                last_err = str(e)
                continue
            except Exception as e:
                last_err = str(e)
                continue
    finally:
        sys.path = orig_sys_path

    from django.http import HttpResponseNotFound
    # If the plugin directory exists under /usr/local/CyberCP, treat this as a broken/incomplete install.
    if os.path.isdir(installed_plugin_path):
        return HttpResponseNotFound('Plugin settings not available (incomplete installation).')
    return HttpResponseNotFound('Plugin not found.')


def _inject_plugin_settings_back_bar(response):
    """
    Add a consistent 'Back to installed Plugins' link at the top of proxied plugin
    settings HTML so users need not use the sidebar. Only touches HTML responses.
    """
    try:
        if isinstance(response, StreamingHttpResponse):
            return response
        content_type = (response.get('Content-Type', '') or '').lower()
        if 'text/html' not in content_type:
            return response
        if not getattr(response, 'content', None):
            return response
        body = response.content.decode('utf-8', errors='ignore')
        if not body.strip():
            return response
        from django.utils.html import escape
        from django.utils.translation import gettext as _

        if 'cp-plugin-settings-back' in body:
            return response
        label = escape(str(_('Back to installed Plugins')))
        # Inside #main-content only: avoids full-viewport strip over the sidebar (baseTemplate uses
        # #sidebar + #main-content { margin-left: 260px; }).
        back_html = (
            '<div id="cp-plugin-settings-back" style="margin:0 0 16px 0;padding:10px 16px;'
            'background:linear-gradient(90deg,#f1f5f9,#e8eef5);border:1px solid #cbd5e1;border-radius:8px;'
            'font-size:14px;line-height:1.4;position:relative;max-width:100%;box-sizing:border-box;">'
            '<a href="/plugins/installed" id="cp-plugin-settings-back-link" '
            'style="display:inline-flex;align-items:center;gap:8px;color:#1e293b;font-weight:600;'
            'text-decoration:none;">'
            '<span aria-hidden="true" style="font-size:1.1em;">←</span><span>' + label + '</span></a></div>'
        )
        main_content_m = re.search(
            r'(<div\s+id\s*=\s*["\']main-content["\'][^>]*>)',
            body,
            flags=re.IGNORECASE,
        )
        if main_content_m:
            pos = main_content_m.end()
            body = body[:pos] + back_html + body[pos:]
        elif re.search(r'<body[^>]*>', body, flags=re.IGNORECASE):
            body = re.sub(
                r'(<body[^>]*>)',
                r'\1' + back_html,
                body,
                count=1,
                flags=re.IGNORECASE,
            )
        else:
            body = back_html + body
        response.content = body.encode('utf-8')
        return response
    except Exception:
        return response


def _inject_activation_store_hook(response, plugin_name):
    """
    Tiny safety hook for plugin settings pages:
    if a plugin activation request succeeds client-side, persist the key in
    CyberPanel DB via /plugins/api/store-activation/<plugin>/.
    """
    try:
        content_type = (response.get('Content-Type', '') or '').lower()
        if 'text/html' not in content_type:
            return response
        body = response.content.decode('utf-8', errors='ignore')
        hook_script = """
<script>
(function () {
  if (window.__cpActivationStoreHookInstalled) return;
  window.__cpActivationStoreHookInstalled = true;
  var pluginName = %s;
  function getCsrfToken() {
    var m = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : '';
  }
  function tryParseBody(body) {
    if (!body || typeof body !== 'string') return '';
    try {
      var obj = JSON.parse(body);
      if (obj && typeof obj.activation_key === 'string') return obj.activation_key.trim();
    } catch (e) {}
    var rx = /activation_key\\s*[:=]\\s*["']?([A-Za-z0-9\\-_.]{6,})/i;
    var m = body.match(rx);
    return m ? m[1] : '';
  }
  async function persistActivationKey(activationKey) {
    if (!activationKey) return;
    try {
      await window.__cpOriginalFetch('/plugins/api/store-activation/' + encodeURIComponent(pluginName) + '/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({ activation_key: activationKey })
      });
    } catch (e) {}
  }
  if (!window.fetch) return;
  window.__cpOriginalFetch = window.fetch.bind(window);
  window.fetch = async function(input, init) {
    var url = (typeof input === 'string') ? input : ((input && input.url) || '');
    var body = init && init.body ? String(init.body) : '';
    var activationKey = tryParseBody(body);
    var resp = await window.__cpOriginalFetch(input, init);
    try {
      var looksLikeActivation = /activate|activation|activate_key/i.test(url || '');
      if (!looksLikeActivation) return resp;
      var clone = resp.clone();
      var ct = (clone.headers.get('content-type') || '').toLowerCase();
      if (ct.indexOf('application/json') === -1) return resp;
      var data = await clone.json();
      var ok = !!(data && (data.has_access === true || data.status === 1 || data.success === true));
      if (ok && activationKey) {
        persistActivationKey(activationKey);
      }
    } catch (e) {}
    return resp;
  };
})();
</script>
""" % json.dumps(plugin_name)
        if '</body>' in body:
            body = body.replace('</body>', hook_script + '</body>')
        else:
            body += hook_script
        response.content = body.encode('utf-8')
        return response
    except Exception:
        return response


def plugin_help(request, plugin_name):
    """Plugin-specific help page - shows plugin information, version history, and help content"""
    mailUtilities.checkHome()
    
    # Paths for the plugin
    installed_plugin_path = '/usr/local/CyberCP/' + plugin_name
    meta_xml_path = os.path.join(installed_plugin_path, 'meta.xml')

    # If installed meta.xml is missing (e.g. incomplete install), fall back to plugin source.
    plugin_path = installed_plugin_path
    if not os.path.exists(meta_xml_path):
        for src_base in PLUGIN_SOURCE_PATHS:
            candidate = os.path.join(src_base, plugin_name, 'meta.xml')
            if os.path.exists(candidate):
                plugin_path = os.path.join(src_base, plugin_name)
                meta_xml_path = candidate
                break

    # Check if plugin exists (at least meta.xml must exist)
    if not os.path.exists(meta_xml_path):
        proc = httpProc(request, 'pluginHolder/plugin_not_found.html', {
            'plugin_name': plugin_name
        }, 'managePlugins')
        return proc.render()
    
    # Parse meta.xml
    try:
        plugin_meta = ElementTree.parse(meta_xml_path)
        root = plugin_meta.getroot()
        
        # Extract plugin information
        plugin_display_name = root.find('name').text if root.find('name') is not None else plugin_name
        plugin_description = root.find('description').text if root.find('description') is not None else ''
        plugin_version = root.find('version').text if root.find('version') is not None else 'Unknown'
        plugin_author = root.find('author').text if root.find('author') is not None else 'Unknown'
        plugin_type = root.find('type').text if root.find('type') is not None else 'Plugin'
        
        # Check if plugin is installed
        installed = os.path.exists(installed_plugin_path)
        
    except Exception as e:
        logging.writeToFile(f"Error parsing meta.xml for {plugin_name}: {str(e)}")
        proc = httpProc(request, 'pluginHolder/plugin_not_found.html', {
            'plugin_name': plugin_name
        }, 'managePlugins')
        return proc.render()
    
    # Look for help content files (README.md, CHANGELOG.md, HELP.md, etc.)
    help_content = ''
    changelog_content = ''
    
    # Check for README.md or HELP.md
    help_files = ['HELP.md', 'README.md', 'docs/HELP.md', 'docs/README.md']
    help_file_path = None
    for help_file in help_files:
        potential_path = os.path.join(plugin_path, help_file)
        if os.path.exists(potential_path):
            help_file_path = potential_path
            break
    
    if help_file_path:
        try:
            with open(help_file_path, 'r', encoding='utf-8') as f:
                help_content = f.read()
        except Exception as e:
            logging.writeToFile(f"Error reading help file for {plugin_name}: {str(e)}")
            help_content = ''
    
    # Check for CHANGELOG.md
    changelog_paths = ['CHANGELOG.md', 'changelog.md', 'CHANGELOG.txt', 'docs/CHANGELOG.md']
    for changelog_file in changelog_paths:
        potential_path = os.path.join(plugin_path, changelog_file)
        if os.path.exists(potential_path):
            try:
                with open(potential_path, 'r', encoding='utf-8') as f:
                    changelog_content = f.read()
                break
            except Exception as e:
                logging.writeToFile(f"Error reading changelog for {plugin_name}: {str(e)}")
    
    # If no local changelog, try fetching from GitHub (non-blocking)
    if not changelog_content:
        try:
            github_changelog_url = f'{GITHUB_RAW_BASE}/{plugin_name}/CHANGELOG.md'
            try:
                with urllib.request.urlopen(github_changelog_url, timeout=3) as response:
                    if response.getcode() == 200:
                        changelog_content = response.read().decode('utf-8')
                        logging.writeToFile(f"Fetched CHANGELOG.md from GitHub for {plugin_name}")
            except (urllib.error.HTTPError, urllib.error.URLError, Exception):
                # Silently fail - GitHub fetch is optional
                pass
        except Exception:
            # Silently fail - GitHub fetch is optional
            pass
    
    # If no help content and no local README, try fetching README.md from GitHub
    if not help_content:
        try:
            github_readme_url = f'{GITHUB_RAW_BASE}/{plugin_name}/README.md'
            try:
                with urllib.request.urlopen(github_readme_url, timeout=3) as response:
                    if response.getcode() == 200:
                        help_content = response.read().decode('utf-8')
                        logging.writeToFile(f"Fetched README.md from GitHub for {plugin_name}")
            except (urllib.error.HTTPError, urllib.error.URLError, Exception):
                # Silently fail - GitHub fetch is optional
                pass
        except Exception:
            # Silently fail - GitHub fetch is optional
            pass
    
    # If no help content found, create default content from meta.xml
    if not help_content:
        help_content = f"""
<h2>Plugin Information</h2>
<p><strong>Name:</strong> {plugin_display_name}</p>
<p><strong>Type:</strong> {plugin_type}</p>
<p><strong>Version:</strong> {plugin_version}</p>
<p><strong>Author:</strong> {plugin_author}</p>

<h2>Description</h2>
<p>{plugin_description}</p>

<h2>Usage</h2>
<p>For detailed information about this plugin, please visit the GitHub repository or check the plugin's documentation.</p>
"""
    else:
        # Convert markdown to HTML (basic conversion)
        import re
        # Convert linked images first (badges): [![alt](img_url)](link_url)
        help_content = re.sub(
            r'\[!\[([^\]]*)\]\(([^\)]+)\)\]\(([^\)]+)\)',
            r'<a href="\3" target="_blank" rel="noopener noreferrer"><img src="\2" alt="\1" style="display:inline-block;margin:0 4px;vertical-align:middle;"></a>',
            help_content
        )
        # Convert regular images: ![alt](img_url)
        help_content = re.sub(
            r'!\[([^\]]*)\]\(([^\)]+)\)',
            r'<img src="\2" alt="\1" style="display:inline-block;margin:4px 0;max-width:100%;">',
            help_content
        )
        # Convert regular links: [text](url)
        help_content = re.sub(
            r'\[([^\]]+)\]\(([^\)]+)\)',
            r'<a href="\2" target="_blank" rel="noopener noreferrer">\1</a>',
            help_content
        )
        # Convert headings
        help_content = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', help_content, flags=re.MULTILINE)
        help_content = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', help_content, flags=re.MULTILINE)
        help_content = re.sub(r'^# (.*?)$', r'<h1>\1</h1>', help_content, flags=re.MULTILINE)
        # Convert formatting
        help_content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', help_content)
        help_content = re.sub(r'\*(.*?)\*', r'<em>\1</em>', help_content)
        help_content = re.sub(r'`([^`]+)`', r'<code>\1</code>', help_content)
        # Convert lists
        help_content = re.sub(r'^\- (.*?)$', r'<li>\1</li>', help_content, flags=re.MULTILINE)
        help_content = re.sub(r'^(\d+)\. (.*?)$', r'<li>\2</li>', help_content, flags=re.MULTILINE)
        # Wrap paragraphs (but preserve HTML tags and images)
        lines = help_content.split('\n')
        processed_lines = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith('<') and not line.startswith('http') and not '<img' in line and not '<a' in line:
                processed_lines.append(f'<p>{line}</p>')
            elif line:
                processed_lines.append(line)
        help_content = '\n'.join(processed_lines)
    
    # Add changelog if available
    if changelog_content:
        # Convert changelog markdown to HTML
        import re
        changelog_html = changelog_content
        changelog_html = re.sub(r'^## (.*?)$', r'<h3>\1</h3>', changelog_html, flags=re.MULTILINE)
        changelog_html = re.sub(r'^### (.*?)$', r'<h4>\1</h4>', changelog_html, flags=re.MULTILINE)
        changelog_html = re.sub(r'^\- (.*?)$', r'<li>\1</li>', changelog_html, flags=re.MULTILINE)
        changelog_html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', changelog_html)
        # Wrap in pre for code-like formatting
        changelog_html = f'<div class="changelog-content"><h2>Version History</h2><pre>{changelog_html}</pre></div>'
        help_content += changelog_html
    
    # Context for template
    context = {
        'plugin_name': plugin_display_name,
        'plugin_name_dir': plugin_name,
        'plugin_description': plugin_description,
        'plugin_version': plugin_version,
        'plugin_author': plugin_author,
        'plugin_type': plugin_type,
        'installed': installed,
        'help_content': help_content,
    }
    
    proc = httpProc(request, 'pluginHolder/plugin_help.html', context, 'managePlugins')
    return proc.render()

@csrf_exempt
@require_http_methods(["GET", "POST"])
def check_plugin_subscription(request, plugin_name):
    """
    API endpoint to check plugin premium access.
    Supports optional activation key save/verify to persist entitlement in MariaDB.
    
    Args:
        request: Django request object
        plugin_name: Name of the plugin to check
        
    Returns:
        JsonResponse: {
            'has_access': bool,
            'is_paid': bool,
            'message': str,
            'patreon_url': str or None
        }
    """
    try:
        if not user_can_manage_plugins(request):
            return deny_plugin_manage_json_response(request)
        
        # Load plugin metadata
        from .plugin_access import (
            check_plugin_access,
            _load_plugin_meta,
            save_activation_key,
            verify_saved_activation_key
        )
        
        plugin_meta = _load_plugin_meta(plugin_name)
        
        user_email = _resolve_logged_in_plugin_identity(request)
        if not user_email:
            return JsonResponse({
                'success': False,
                'has_access': False,
                'is_paid': False,
                'message': 'Unable to determine user identity',
                'patreon_url': None
            }, status=400)
        activation_key = ''
        if request.method == 'POST':
            try:
                payload = json.loads(request.body.decode('utf-8') or '{}')
            except Exception:
                payload = {}
            activation_key = str(payload.get('activation_key', '')).strip()
            if activation_key and user_email:
                # If key is already known for this user/plugin -> immediate access
                if verify_saved_activation_key(plugin_name, user_email, activation_key):
                    return JsonResponse({
                        'success': True,
                        'has_access': True,
                        'is_paid': bool(plugin_meta and plugin_meta.get('is_paid', False)),
                        'message': 'Access granted',
                        'patreon_url': None,
                        'activation_saved': True
                    })
                # Save submitted key as persistent entitlement (admin-managed workflow)
                saved = save_activation_key(plugin_name, user_email, activation_key, source='plugin_settings')
                if saved:
                    return JsonResponse({
                        'success': True,
                        'has_access': True,
                        'is_paid': bool(plugin_meta and plugin_meta.get('is_paid', False)),
                        'message': 'Activation key saved',
                        'patreon_url': None,
                        'activation_saved': True
                    })

        # Check access
        access_result = check_plugin_access(request, plugin_name, plugin_meta)
        
        return JsonResponse({
            'success': True,
            'has_access': access_result['has_access'],
            'is_paid': access_result['is_paid'],
            'message': access_result['message'],
            'patreon_url': access_result.get('patreon_url'),
            'activation_saved': access_result['has_access'] and access_result['is_paid']
        })
        
    except Exception as e:
        logging.writeToFile(f"Error checking subscription for {plugin_name}: {str(e)}")
        return JsonResponse({
            'success': False,
            'has_access': False,
            'is_paid': False,
            'message': 'Error checking subscription',
            'patreon_url': None
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def store_plugin_activation_key(request, plugin_name):
    """
    Store activation key in MariaDB so upgrades do not lose premium entitlement.
    """
    try:
        if not user_can_manage_plugins(request):
            return deny_plugin_manage_json_response(request)

        try:
            payload = json.loads(request.body.decode('utf-8') or '{}')
        except Exception:
            payload = {}

        activation_key = str(payload.get('activation_key', '')).strip()
        if not activation_key:
            return JsonResponse({'success': False, 'message': 'activation_key is required'}, status=400)

        user_email = _resolve_logged_in_plugin_identity(request)
        if not user_email:
            return JsonResponse({'success': False, 'message': 'Unable to determine user identity'}, status=400)

        from .plugin_access import save_activation_key
        ok = save_activation_key(plugin_name, user_email, activation_key, source='api')
        if not ok:
            return JsonResponse({'success': False, 'message': 'Failed to persist activation key'}, status=500)

        return JsonResponse({'success': True, 'message': 'Activation key saved'})
    except Exception as e:
        logging.writeToFile('store_plugin_activation_key failed for %s: %s' % (plugin_name, str(e)))
        return JsonResponse({'success': False, 'message': 'Internal server error'}, status=500)
