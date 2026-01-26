# -*- coding: utf-8 -*-
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from plogical.mailUtilities import mailUtilities
import os
import subprocess
import shlex
import json
from datetime import datetime, timedelta
from xml.etree import ElementTree
from plogical.httpProc import httpProc
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
import sys
import urllib.request
import urllib.error
import time
sys.path.append('/usr/local/CyberCP')
from pluginInstaller.pluginInstaller import pluginInstaller
from .patreon_verifier import PatreonVerifier

# Plugin state file location
PLUGIN_STATE_DIR = '/home/cyberpanel/plugin_states'

# Plugin store cache configuration
PLUGIN_STORE_CACHE_DIR = '/home/cyberpanel/plugin_store_cache'
PLUGIN_STORE_CACHE_FILE = os.path.join(PLUGIN_STORE_CACHE_DIR, 'plugins_cache.json')
PLUGIN_STORE_CACHE_DURATION = 3600  # Cache for 1 hour (3600 seconds)
GITHUB_REPO_API = 'https://api.github.com/repos/master3395/cyberpanel-plugins/contents'
GITHUB_RAW_BASE = 'https://raw.githubusercontent.com/master3395/cyberpanel-plugins/main'
GITHUB_COMMITS_API = 'https://api.github.com/repos/master3395/cyberpanel-plugins/commits'

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
    proc = httpProc(request, 'pluginHolder/help.html', {}, 'admin')
    return proc.render()

def installed(request):
    mailUtilities.checkHome()
    pluginPath = '/home/cyberpanel/plugins'
    installedPath = '/usr/local/CyberCP'
    pluginList = []
    errorPlugins = []
    processed_plugins = set()  # Track which plugins we've already processed

    # First, process plugins from source directory
    if os.path.exists(pluginPath):
        for plugin in os.listdir(pluginPath):
            # Skip files (like .zip files) - only process directories
            pluginDir = os.path.join(pluginPath, plugin)
            if not os.path.isdir(pluginDir):
                continue
            
            data = {}
            # Try installed location first, then fallback to source location
            completePath = installedPath + '/' + plugin + '/meta.xml'
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
                    # No meta.xml found in either location - skip silently
                    continue
                
                pluginMetaData = ElementTree.parse(metaXmlPath)
                root = pluginMetaData.getroot()
                
                # Validate required fields exist (handle both <plugin> and <cyberpanelPluginConfig> formats)
                name_elem = root.find('name')
                type_elem = root.find('type')
                desc_elem = root.find('description')
                version_elem = root.find('version')
                
                # Type field is optional (testPlugin doesn't have it)
                if name_elem is None or desc_elem is None or version_elem is None:
                    errorPlugins.append({'name': plugin, 'error': 'Missing required metadata fields (name, description, or version)'})
                    logging.writeToFile(f"Plugin {plugin}: Missing required metadata fields in meta.xml")
                    continue
                
                # Check if text is None (empty elements)
                if name_elem.text is None or desc_elem.text is None or version_elem.text is None:
                    errorPlugins.append({'name': plugin, 'error': 'Empty metadata fields'})
                    logging.writeToFile(f"Plugin {plugin}: Empty metadata fields in meta.xml")
                    continue
                
                data['name'] = name_elem.text
                data['type'] = type_elem.text if type_elem is not None and type_elem.text is not None else 'Plugin'
                data['desc'] = desc_elem.text
                data['version'] = version_elem.text
                data['plugin_dir'] = plugin  # Plugin directory name
                data['installed'] = os.path.exists(completePath)  # True if installed, False if only in source
                
                # Get plugin enabled state (only for installed plugins)
                if data['installed']:
                    data['enabled'] = _is_plugin_enabled(plugin)
                else:
                    data['enabled'] = False
                
                # Initialize is_paid to False by default (will be set later if paid)
                data['is_paid'] = False
                data['patreon_tier'] = None
                data['patreon_url'] = None
                data['paypal_me_url'] = None
                data['paypal_payment_link'] = None
                data['payment_type'] = None  # 'patreon' or 'paypal'
                
                # Get modify date from local file (fast, no API calls)
                # GitHub commit dates are fetched in the plugin store, not here to avoid timeouts
                modify_date = 'N/A'
                try:
                    if os.path.exists(metaXmlPath):
                        modify_time = os.path.getmtime(metaXmlPath)
                        modify_date = datetime.fromtimestamp(modify_time).strftime('%Y-%m-%d %H:%M:%S')
                except Exception:
                    modify_date = 'N/A'
                
                data['modify_date'] = modify_date
                
                # Calculate NEW and Stale badges based on modify_date
                data['is_new'] = False
                data['is_stale'] = False
                
                if modify_date and modify_date != 'N/A':
                    try:
                        # Parse the modify_date (format: YYYY-MM-DD HH:MM:SS)
                        modify_date_obj = datetime.strptime(modify_date, '%Y-%m-%d %H:%M:%S')
                        now = datetime.now()
                        time_diff = now - modify_date_obj
                        
                        # NEW: updated within last 90 days (3 months)
                        if time_diff.days <= 90:
                            data['is_new'] = True
                        
                        # Stale: not updated in last 2 years (730 days)
                        if time_diff.days > 730:
                            data['is_stale'] = True
                    except Exception:
                        # If date parsing fails, leave as False
                        pass
                
                # Extract settings URL or main URL for "Manage" button
                settings_url_elem = root.find('settings_url')
                url_elem = root.find('url')
                
                # Priority: settings_url > url > default pattern
                # Special handling for core plugins that don't use /plugins/ prefix
                # emailMarketing removed from INSTALLED_APPS - skip it
                if plugin == 'emailMarketing':
                    continue
                elif settings_url_elem is not None and settings_url_elem.text:
                    data['manage_url'] = settings_url_elem.text
                elif url_elem is not None and url_elem.text:
                    data['manage_url'] = url_elem.text
                else:
                    # Default: try /plugins/{plugin_dir}/settings/ or /plugins/{plugin_dir}/
                    # Only set if plugin is installed (we can't know if the URL exists otherwise)
                    if os.path.exists(completePath):
                        # Check if settings route exists, otherwise use main plugin URL
                        settings_route = f'/plugins/{plugin}/settings/'
                        main_route = f'/plugins/{plugin}/'
                        # Default to main route - most plugins have a main route even if no settings
                        data['manage_url'] = main_route
                    else:
                        data['manage_url'] = None
                
                # Extract author information
                author_elem = root.find('author')
                if author_elem is not None and author_elem.text:
                    data['author'] = author_elem.text
                else:
                    data['author'] = 'Unknown'
                
                # Extract paid plugin information - support both Patreon and PayPal
                paid_elem = root.find('paid')
                
                # CRITICAL: Always explicitly set is_paid as boolean True/False
                if paid_elem is not None and paid_elem.text and str(paid_elem.text).strip().lower() == 'true':
                    data['is_paid'] = True  # Explicit boolean True
                    
                    # Check for PayPal payment method first
                    paypal_me_elem = root.find('paypal_me_url')
                    paypal_payment_link_elem = root.find('paypal_payment_link')
                    
                    if (paypal_me_elem is not None and paypal_me_elem.text) or (paypal_payment_link_elem is not None and paypal_payment_link_elem.text):
                        # This is a PayPal plugin
                        data['payment_type'] = 'paypal'
                        data['paypal_me_url'] = paypal_me_elem.text if paypal_me_elem is not None and paypal_me_elem.text else None
                        data['paypal_payment_link'] = paypal_payment_link_elem.text if paypal_payment_link_elem is not None and paypal_payment_link_elem.text else None
                        data['patreon_tier'] = None
                        data['patreon_url'] = None
                    else:
                        # This is a Patreon plugin (default/fallback)
                        data['payment_type'] = 'patreon'
                        patreon_tier_elem = root.find('patreon_tier')
                        data['patreon_tier'] = patreon_tier_elem.text if patreon_tier_elem is not None and patreon_tier_elem.text else 'CyberPanel Paid Plugin'
                        data['patreon_url'] = root.find('patreon_url').text if root.find('patreon_url') is not None else 'https://www.patreon.com/c/newstargeted/membership'
                        data['paypal_me_url'] = None
                        data['paypal_payment_link'] = None
                else:
                    data['is_paid'] = False  # Explicit boolean False
                    data['patreon_tier'] = None
                    data['patreon_url'] = None
                    data['paypal_me_url'] = None
                    data['paypal_payment_link'] = None
                    data['payment_type'] = None
                
                # Force boolean type (defensive programming) - CRITICAL: Always ensure boolean
                data['is_paid'] = bool(data['is_paid']) if 'is_paid' in data else False
                
                # Final safety check - ensure is_paid exists and is boolean before adding to list
                if 'is_paid' not in data or not isinstance(data['is_paid'], bool):
                    data['is_paid'] = False

                # Only add to list if plugin is actually installed
                # Uninstalled plugins should only appear in Plugin Store, not Installed Plugins page
                if data['installed']:
                    pluginList.append(data)
                processed_plugins.add(plugin)  # Mark as processed
            except ElementTree.ParseError as e:
                errorPlugins.append({'name': plugin, 'error': f'XML parse error: {str(e)}'})
                logging.writeToFile(f"Plugin {plugin}: XML parse error - {str(e)}")
                continue
            except Exception as e:
                errorPlugins.append({'name': plugin, 'error': f'Error loading plugin: {str(e)}'})
                logging.writeToFile(f"Plugin {plugin}: Error loading - {str(e)}")
                continue
    
    # Also check for installed plugins that don't have source directories
    # This handles plugins installed from the store that may not be in /home/cyberpanel/plugins/
    if os.path.exists(installedPath):
        for plugin in os.listdir(installedPath):
            # Skip if already processed
            if plugin in processed_plugins:
                continue
            
            # Only check directories that look like plugins (have meta.xml)
            pluginInstalledDir = os.path.join(installedPath, plugin)
            if not os.path.isdir(pluginInstalledDir):
                continue
            
            metaXmlPath = os.path.join(pluginInstalledDir, 'meta.xml')
            if not os.path.exists(metaXmlPath):
                continue
            
            # This is an installed plugin without a source directory - process it
            try:
                data = {}
                pluginMetaData = ElementTree.parse(metaXmlPath)
                root = pluginMetaData.getroot()
                
                # Validate required fields
                name_elem = root.find('name')
                type_elem = root.find('type')
                desc_elem = root.find('description')
                version_elem = root.find('version')
                
                if name_elem is None or desc_elem is None or version_elem is None:
                    continue
                
                if name_elem.text is None or desc_elem.text is None or version_elem.text is None:
                    continue
                
                data['name'] = name_elem.text
                data['type'] = type_elem.text if type_elem is not None and type_elem.text is not None else 'Plugin'
                data['desc'] = desc_elem.text
                data['version'] = version_elem.text
                data['plugin_dir'] = plugin
                data['installed'] = True  # This is an installed plugin
                data['enabled'] = _is_plugin_enabled(plugin)
                
                # Initialize is_paid to False by default (will be set later if paid)
                data['is_paid'] = False
                data['patreon_tier'] = None
                data['patreon_url'] = None
                
                # Get modify date from installed location
                modify_date = 'N/A'
                try:
                    if os.path.exists(metaXmlPath):
                        modify_time = os.path.getmtime(metaXmlPath)
                        modify_date = datetime.fromtimestamp(modify_time).strftime('%Y-%m-%d %H:%M:%S')
                except Exception:
                    modify_date = 'N/A'
                
                data['modify_date'] = modify_date
                
                # Calculate NEW and Stale badges based on modify_date
                data['is_new'] = False
                data['is_stale'] = False
                
                if modify_date and modify_date != 'N/A':
                    try:
                        # Parse the modify_date (format: YYYY-MM-DD HH:MM:SS)
                        modify_date_obj = datetime.strptime(modify_date, '%Y-%m-%d %H:%M:%S')
                        now = datetime.now()
                        time_diff = now - modify_date_obj
                        
                        # NEW: updated within last 90 days (3 months)
                        if time_diff.days <= 90:
                            data['is_new'] = True
                        
                        # Stale: not updated in last 2 years (730 days)
                        if time_diff.days > 730:
                            data['is_stale'] = True
                    except Exception:
                        # If date parsing fails, leave as False
                        pass
                
                # Extract settings URL or main URL
                settings_url_elem = root.find('settings_url')
                url_elem = root.find('url')
                
                # Priority: settings_url > url > default pattern
                # Special handling for core plugins that don't use /plugins/ prefix
                # emailMarketing removed from INSTALLED_APPS - skip it
                if plugin == 'emailMarketing':
                    continue
                elif settings_url_elem is not None and settings_url_elem.text:
                    data['manage_url'] = settings_url_elem.text
                elif url_elem is not None and url_elem.text:
                    data['manage_url'] = url_elem.text
                else:
                    # Default to /plugins/{plugin}/ for regular plugins
                        # Default to main plugin route (most plugins work from main route)
                        data['manage_url'] = f'/plugins/{plugin}/'
                
                # Extract author information
                author_elem = root.find('author')
                if author_elem is not None and author_elem.text:
                    data['author'] = author_elem.text
                else:
                    data['author'] = 'Unknown'
                
                # Extract paid plugin information - support both Patreon and PayPal
                paid_elem = root.find('paid')
                
                # CRITICAL: Always explicitly set is_paid as boolean True/False
                if paid_elem is not None and paid_elem.text and str(paid_elem.text).strip().lower() == 'true':
                    data['is_paid'] = True  # Explicit boolean True
                    
                    # Check for PayPal payment method first
                    paypal_me_elem = root.find('paypal_me_url')
                    paypal_payment_link_elem = root.find('paypal_payment_link')
                    
                    if (paypal_me_elem is not None and paypal_me_elem.text) or (paypal_payment_link_elem is not None and paypal_payment_link_elem.text):
                        # This is a PayPal plugin
                        data['payment_type'] = 'paypal'
                        data['paypal_me_url'] = paypal_me_elem.text if paypal_me_elem is not None and paypal_me_elem.text else None
                        data['paypal_payment_link'] = paypal_payment_link_elem.text if paypal_payment_link_elem is not None and paypal_payment_link_elem.text else None
                        data['patreon_tier'] = None
                        data['patreon_url'] = None
                    else:
                        # This is a Patreon plugin (default/fallback)
                        data['payment_type'] = 'patreon'
                        patreon_tier_elem = root.find('patreon_tier')
                        data['patreon_tier'] = patreon_tier_elem.text if patreon_tier_elem is not None and patreon_tier_elem.text else 'CyberPanel Paid Plugin'
                        patreon_url_elem = root.find('patreon_url')
                        data['patreon_url'] = patreon_url_elem.text if patreon_url_elem is not None and patreon_url_elem.text else 'https://www.patreon.com/membership/27789984'
                        data['paypal_me_url'] = None
                        data['paypal_payment_link'] = None
                else:
                    data['is_paid'] = False  # Explicit boolean False
                    data['patreon_tier'] = None
                    data['patreon_url'] = None
                    data['paypal_me_url'] = None
                    data['paypal_payment_link'] = None
                    data['payment_type'] = None
                
                # Force boolean type (defensive programming) - CRITICAL: Always ensure boolean
                data['is_paid'] = bool(data['is_paid']) if 'is_paid' in data else False
                
                # Final safety check - ensure is_paid exists and is boolean before adding to list
                if 'is_paid' not in data or not isinstance(data['is_paid'], bool):
                    data['is_paid'] = False

                pluginList.append(data)
                
            except ElementTree.ParseError as e:
                errorPlugins.append({'name': plugin, 'error': f'XML parse error: {str(e)}'})
                logging.writeToFile(f"Installed plugin {plugin}: XML parse error - {str(e)}")
                continue
            except Exception as e:
                errorPlugins.append({'name': plugin, 'error': f'Error loading installed plugin: {str(e)}'})
                logging.writeToFile(f"Installed plugin {plugin}: Error loading - {str(e)}")
                continue

    # Sort plugins deterministically by name to prevent order changes
    pluginList.sort(key=lambda x: x.get('name', '').lower())
    
    # Add cache-busting timestamp to context to prevent browser caching
    import time
    context = {
        'plugins': pluginList,
        'error_plugins': errorPlugins,
        'cache_buster': int(time.time())  # Add timestamp to force template reload
    }
    
    proc = httpProc(request, 'pluginHolder/plugins.html', context, 'admin')
    response = proc.render()
    
    # Add cache-busting headers to prevent browser caching
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    
    return response

@csrf_exempt
@require_http_methods(["POST"])
def install_plugin(request, plugin_name):
    """Install a plugin"""
    try:
        # Check if plugin source exists
        pluginSource = '/home/cyberpanel/plugins/' + plugin_name
        if not os.path.exists(pluginSource):
            return JsonResponse({
                'success': False,
                'error': f'Plugin source not found: {plugin_name}'
            }, status=404)
        
        # Check if already installed (must have meta.xml to be considered installed)
        pluginInstalled = '/usr/local/CyberCP/' + plugin_name
        if os.path.exists(pluginInstalled):
            # Check if it's a valid installation (has meta.xml) or just leftover files
            metaXmlPath = os.path.join(pluginInstalled, 'meta.xml')
            if os.path.exists(metaXmlPath):
                return JsonResponse({
                    'success': False,
                    'error': f'Plugin already installed: {plugin_name}'
                }, status=400)
            else:
                # Directory exists but no meta.xml - likely incomplete/uninstalled
                # Try to clean it up first using pluginInstaller.removeFiles which handles permissions
                try:
                    from pluginInstaller.pluginInstaller import pluginInstaller
                    pluginInstaller.removeFiles(plugin_name)
                    logging.writeToFile(f'Cleaned up incomplete plugin directory: {plugin_name}')
                except Exception as e:
                    logging.writeToFile(f'Warning: Could not clean up incomplete directory: {str(e)}')
                    # Try fallback: use system rm -rf
                    try:
                        import subprocess
                        result = subprocess.run(['rm', '-rf', pluginInstalled], capture_output=True, text=True, timeout=30)
                        if result.returncode == 0:
                            logging.writeToFile(f'Cleaned up incomplete plugin directory using rm -rf: {plugin_name}')
                        else:
                            raise Exception(f"rm -rf failed: {result.stderr}")
                    except Exception as e2:
                        logging.writeToFile(f'Error: Both cleanup methods failed: {str(e)}, {str(e2)}')
                        return JsonResponse({
                            'success': False,
                            'error': f'Incomplete plugin directory found. Please uninstall first or manually remove: {pluginInstalled}'
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
        
        # Copy zip to current directory (pluginInstaller expects it in cwd)
        original_cwd = os.getcwd()
        os.chdir(temp_dir)
        
        try:
            # Verify zip file exists in current directory
            zip_file = plugin_name + '.zip'
            if not os.path.exists(zip_file):
                raise Exception(f'Zip file {zip_file} not found in temp directory')
            
            # Install using pluginInstaller
            try:
                pluginInstaller.installPlugin(plugin_name)
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
                # Check if files were extracted to root instead
                root_files = ['README.md', 'apps.py', 'meta.xml', 'urls.py', 'views.py']
                found_root_files = [f for f in root_files if os.path.exists(os.path.join('/usr/local/CyberCP', f))]
                if found_root_files:
                    raise Exception(f'Plugin installation failed: Files extracted to wrong location. Found {found_root_files} in /usr/local/CyberCP/ root instead of {pluginInstalled}/')
                raise Exception(f'Plugin installation failed: {pluginInstalled} does not exist after installation')
            
            # Set plugin to enabled by default after installation
            _set_plugin_state(plugin_name, True)
            
            # Restart lscpd service to ensure plugin loads immediately
            try:
                logging.writeToFile(f"Restarting lscpd service after plugin installation...")
                subprocess.run(['systemctl', 'restart', 'lscpd'], check=True, timeout=30)
                logging.writeToFile(f"lscpd service restarted successfully")
            except subprocess.TimeoutExpired:
                logging.writeToFile(f"Warning: lscpd restart timed out, but continuing...")
            except Exception as restart_error:
                logging.writeToFile(f"Warning: Failed to restart lscpd: {str(restart_error)}")
                # Don't fail installation if restart fails, just log it
            
            return JsonResponse({
                'success': True,
                'message': f'Plugin {plugin_name} installed successfully'
            })
        finally:
            os.chdir(original_cwd)
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
        try:
            pluginInstaller.removeFiles(plugin_name)
            
            # Verify removal succeeded
            pluginInstalled = '/usr/local/CyberCP/' + plugin_name
            if os.path.exists(pluginInstalled):
                # Removal failed - try again with more aggressive methods
                logging.writeToFile(f'Plugin directory still exists after removeFiles, trying ProcessUtilities')
                try:
                    from plogical.processUtilities import ProcessUtilities
                    import time
                    import subprocess
                    
                    # First, try to fix permissions with ProcessUtilities
                    chown_cmd = f'chown -R cyberpanel:cyberpanel {pluginInstalled}'
                    chown_result = ProcessUtilities.normalExecutioner(chown_cmd)
                    if chown_result == 0:
                        logging.writeToFile(f'Warning: chown failed for {pluginInstalled}')
                    
                    chmod_cmd = f'chmod -R u+rwX,go+rX {pluginInstalled}'
                    chmod_result = ProcessUtilities.normalExecutioner(chmod_cmd)
                    if chmod_result == 0:
                        logging.writeToFile(f'Warning: chmod failed for {pluginInstalled}')
                    
                    # Then try to remove with ProcessUtilities
                    rm_cmd = f'rm -rf {pluginInstalled}'
                    rm_result = ProcessUtilities.normalExecutioner(rm_cmd)
                    
                    # Wait a moment for filesystem to sync
                    time.sleep(0.5)
                    
                    # Verify again
                    if os.path.exists(pluginInstalled):
                        # ProcessUtilities failed - try subprocess directly
                        logging.writeToFile(f'ProcessUtilities removal failed (exit code: {rm_result}), trying subprocess')
                        try:
                            # Check if we're root
                            is_root = os.geteuid() == 0 if hasattr(os, 'geteuid') else False
                            if is_root:
                                # Running as root - use subprocess directly
                                result = subprocess.run(
                                    ['rm', '-rf', pluginInstalled],
                                    capture_output=True, text=True, timeout=30
                                )
                                time.sleep(0.5)
                                if os.path.exists(pluginInstalled):
                                    # Last resort: try with shell=True
                                    logging.writeToFile(f'Subprocess rm -rf failed, trying with shell=True')
                                    subprocess.run(f'rm -rf {pluginInstalled}', shell=True, timeout=30)
                                    time.sleep(0.5)
                                    if os.path.exists(pluginInstalled):
                                        raise Exception(f'Plugin directory still exists after all removal attempts: {pluginInstalled}')
                            else:
                                # Not root - try with shell=True which might work better
                                logging.writeToFile(f'Not root, trying rm -rf with shell=True')
                                subprocess.run(f'rm -rf {pluginInstalled}', shell=True, timeout=30)
                                time.sleep(0.5)
                                if os.path.exists(pluginInstalled):
                                    raise Exception(f'Plugin directory still exists after ProcessUtilities and subprocess removal: {pluginInstalled}')
                        except Exception as e3:
                            logging.writeToFile(f'Subprocess removal also failed: {str(e3)}')
                            raise Exception(f'Failed to remove plugin directory. Tried removeFiles(), ProcessUtilities, and subprocess. Directory still exists: {pluginInstalled}')
                except Exception as e2:
                    logging.writeToFile(f'ProcessUtilities removal failed: {str(e2)}')
                    raise Exception(f'Failed to remove plugin directory. Tried removeFiles() and ProcessUtilities. Directory still exists: {pluginInstalled}')
        except Exception as e:
            logging.writeToFile(f'Error removing plugin files: {str(e)}')
            return JsonResponse({
                'success': False,
                'error': f'Failed to remove plugin directory: {str(e)}'
            }, status=500)
        
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
def enable_plugin(request, plugin_name):
    """Enable a plugin"""
    try:
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

def _get_cached_plugins(allow_expired=False):
    """Get plugins from cache if available and not expired
    
    Args:
        allow_expired: If True, return cache even if expired (for fallback)
    """
    try:
        if not os.path.exists(PLUGIN_STORE_CACHE_FILE):
            return None
        
        # Check if cache is expired
        cache_mtime = os.path.getmtime(PLUGIN_STORE_CACHE_FILE)
        cache_age = time.time() - cache_mtime
        
        if cache_age > PLUGIN_STORE_CACHE_DURATION:
            if not allow_expired:
                logging.writeToFile(f"Plugin store cache expired (age: {cache_age:.0f}s)")
                return None
            else:
                logging.writeToFile(f"Using expired cache as fallback (age: {cache_age:.0f}s)")
        
        # Read cache file
        with open(PLUGIN_STORE_CACHE_FILE, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        
        if not allow_expired or cache_age <= PLUGIN_STORE_CACHE_DURATION:
            logging.writeToFile(f"Using cached plugin store data (age: {cache_age:.0f}s)")
        return cache_data.get('plugins', [])
    except Exception as e:
        logging.writeToFile(f"Error reading plugin store cache: {str(e)}")
        return None

def _save_plugins_cache(plugins):
    """Save plugins to cache"""
    try:
        _ensure_cache_dir()
        cache_data = {
            'plugins': plugins,
            'cached_at': datetime.now().isoformat(),
            'cache_duration': PLUGIN_STORE_CACHE_DURATION
        }
        with open(PLUGIN_STORE_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)
        logging.writeToFile("Plugin store cache saved successfully")
    except Exception as e:
        logging.writeToFile(f"Error saving plugin store cache: {str(e)}")

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
        # IMPORTANT: Only check installed location, not source location
        # Plugins in /home/cyberpanel/plugins/ are just source files, not installed plugins
        installed_path = os.path.join(plugin_install_dir, plugin_dir)
        installed_meta = os.path.join(installed_path, 'meta.xml')
        
        # Plugin is only considered installed if:
        # 1. The plugin directory exists in /usr/local/CyberCP/
        # 2. AND meta.xml exists (indicates actual installation, not just leftover files)
        plugin['installed'] = os.path.exists(installed_path) and os.path.exists(installed_meta)
        
        # Check if plugin is enabled (only if installed)
        if plugin['installed']:
            plugin['enabled'] = _is_plugin_enabled(plugin_dir)
        else:
            plugin['enabled'] = False
        
        # Ensure is_paid field exists and is properly set (default to False if not set or invalid)
        # CRITICAL FIX: Always check local meta.xml FIRST as source of truth
        # This ensures cache entries without is_paid are properly enriched
        # Check installed location first, then fallback to source location for metadata
        meta_path = None
        source_path = os.path.join(plugin_source_dir, plugin_dir)
        if os.path.exists(installed_meta):
            meta_path = installed_meta
        elif os.path.exists(source_path):
            source_meta = os.path.join(source_path, 'meta.xml')
            if os.path.exists(source_meta):
                meta_path = source_meta
        
        # If we have a local meta.xml, use it as the source of truth (most reliable)
        if meta_path and os.path.exists(meta_path):
            try:
                pluginMetaData = ElementTree.parse(meta_path)
                root = pluginMetaData.getroot()
                paid_elem = root.find('paid')
                if paid_elem is not None and paid_elem.text and str(paid_elem.text).strip().lower() == 'true':
                    plugin['is_paid'] = True
                    
                    # Check for PayPal payment method first
                    paypal_me_elem = root.find('paypal_me_url')
                    paypal_payment_link_elem = root.find('paypal_payment_link')
                    
                    if (paypal_me_elem is not None and paypal_me_elem.text) or (paypal_payment_link_elem is not None and paypal_payment_link_elem.text):
                        # This is a PayPal plugin
                        plugin['payment_type'] = 'paypal'
                        plugin['paypal_me_url'] = paypal_me_elem.text if paypal_me_elem is not None and paypal_me_elem.text else None
                        plugin['paypal_payment_link'] = paypal_payment_link_elem.text if paypal_payment_link_elem is not None and paypal_payment_link_elem.text else None
                        plugin['patreon_tier'] = None
                        plugin['patreon_url'] = None
                    else:
                        # This is a Patreon plugin (default/fallback)
                        plugin['payment_type'] = 'patreon'
                        patreon_tier_elem = root.find('patreon_tier')
                        plugin['patreon_tier'] = patreon_tier_elem.text if patreon_tier_elem is not None and patreon_tier_elem.text else 'CyberPanel Paid Plugin'
                        patreon_url_elem = root.find('patreon_url')
                        plugin['patreon_url'] = patreon_url_elem.text if patreon_url_elem is not None and patreon_url_elem.text else 'https://www.patreon.com/c/newstargeted/membership'
                        plugin['paypal_me_url'] = None
                        plugin['paypal_payment_link'] = None
                else:
                    plugin['is_paid'] = False
                    plugin['payment_type'] = None
                    plugin['patreon_tier'] = None
                    plugin['patreon_url'] = None
                    plugin['paypal_me_url'] = None
                    plugin['paypal_payment_link'] = None
            except Exception as e:
                logging.writeToFile(f"Error parsing meta.xml for {plugin_dir} in _enrich_store_plugins: {str(e)}")
                # Fall back to normalizing existing value
                is_paid_value = plugin.get('is_paid', False)
                if is_paid_value is None or is_paid_value == '' or is_paid_value == 'false' or is_paid_value == 'False' or is_paid_value == '0':
                    plugin['is_paid'] = False
                elif is_paid_value is True or is_paid_value == 'true' or is_paid_value == 'True' or is_paid_value == '1' or str(is_paid_value).lower() == 'true':
                    plugin['is_paid'] = True
                else:
                    plugin['is_paid'] = False
        else:
            # No local meta.xml, normalize existing value from cache/API
            is_paid_value = plugin.get('is_paid', False)
            if is_paid_value is None or is_paid_value == '' or is_paid_value == 'false' or is_paid_value == 'False' or is_paid_value == '0':
                plugin['is_paid'] = False
            elif is_paid_value is True or is_paid_value == 'true' or is_paid_value == 'True' or is_paid_value == '1' or str(is_paid_value).lower() == 'true':
                plugin['is_paid'] = True
            else:
                plugin['is_paid'] = False  # Default to free if we can't determine
        
        # Ensure it's a proper boolean (not string or other type) - CRITICAL for consistency
        if plugin['is_paid'] not in [True, False]:
            plugin['is_paid'] = bool(plugin['is_paid'])
        # Final safety check - force boolean type (defensive programming)
        plugin['is_paid'] = True if plugin['is_paid'] is True else False
        
        # Ensure payment_type is set if is_paid is True
        if plugin['is_paid'] and 'payment_type' not in plugin:
            # Default to patreon if payment_type not set
            plugin['payment_type'] = 'patreon'
        
        # Calculate NEW and Stale badges based on modify_date
        modify_date_str = plugin.get('modify_date', 'N/A')
        plugin['is_new'] = False
        plugin['is_stale'] = False
        
        if modify_date_str and modify_date_str != 'N/A':
            try:
                # Parse the modify_date (could be various formats)
                modify_date = None
                if isinstance(modify_date_str, str):
                    # Handle ISO format with timezone (from GitHub API)
                    if 'T' in modify_date_str:
                        # ISO format: 2026-01-25T04:24:52Z or 2026-01-25T04:24:52+00:00
                        try:
                            # Remove timezone info for simpler parsing
                            date_part = modify_date_str.split('T')[0]
                            time_part = modify_date_str.split('T')[1].split('+')[0].split('Z')[0]
                            modify_date = datetime.strptime(f"{date_part} {time_part}", '%Y-%m-%d %H:%M:%S')
                        except:
                            # Fallback: try standard format
                            modify_date = datetime.strptime(modify_date_str[:19], '%Y-%m-%d %H:%M:%S')
                    else:
                        # Standard format: YYYY-MM-DD HH:MM:SS
                        modify_date = datetime.strptime(modify_date_str, '%Y-%m-%d %H:%M:%S')
                else:
                    modify_date = modify_date_str
                
                if modify_date:
                    now = datetime.now()
                    # Handle timezone-aware datetime
                    if modify_date.tzinfo:
                        from datetime import timezone
                        modify_date = modify_date.replace(tzinfo=None)
                    
                    # Calculate time difference
                    time_diff = now - modify_date
                    
                    # NEW: updated within last 3 months (90 days)
                    if time_diff.days <= 90:
                        plugin['is_new'] = True
                    
                    # Stale: not updated in last 2 years (730 days)
                    if time_diff.days > 730:
                        plugin['is_stale'] = True
                        
            except Exception as e:
                logging.writeToFile(f"Error calculating NEW/Stale status for {plugin_dir}: {str(e)}")
                # Default to not new and not stale if parsing fails
                plugin['is_new'] = False
                plugin['is_stale'] = False
        
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
                
                # Fetch last commit date for this plugin from GitHub
                modify_date = 'N/A'
                try:
                    commits_url = f"{GITHUB_COMMITS_API}?path={plugin_name}&per_page=1"
                    commits_req = urllib.request.Request(
                        commits_url,
                        headers={
                            'User-Agent': 'CyberPanel-Plugin-Store/1.0',
                            'Accept': 'application/vnd.github.v3+json'
                        }
                    )
                    
                    with urllib.request.urlopen(commits_req, timeout=10) as commits_response:
                        commits_data = json.loads(commits_response.read().decode('utf-8'))
                        if commits_data and len(commits_data) > 0:
                            commit_date = commits_data[0].get('commit', {}).get('author', {}).get('date', '')
                            if commit_date:
                                # Parse ISO 8601 date and format it
                                try:
                                    from datetime import datetime
                                    dt = datetime.fromisoformat(commit_date.replace('Z', '+00:00'))
                                    modify_date = dt.strftime('%Y-%m-%d %H:%M:%S')
                                except Exception:
                                    modify_date = commit_date[:19].replace('T', ' ')  # Fallback formatting
                except Exception as e:
                    logging.writeToFile(f"Could not fetch commit date for {plugin_name}: {str(e)}")
                    modify_date = 'N/A'
                
                # Calculate NEW and Stale badges based on modify_date
                is_new = False
                is_stale = False
                
                if modify_date and modify_date != 'N/A':
                    try:
                        # Parse the modify_date
                        modify_date_obj = None
                        if isinstance(modify_date, str):
                            if 'T' in modify_date:
                                # ISO format: 2026-01-25T04:24:52Z or 2026-01-25T04:24:52+00:00
                                try:
                                    date_part = modify_date.split('T')[0]
                                    time_part = modify_date.split('T')[1].split('+')[0].split('Z')[0]
                                    modify_date_obj = datetime.strptime(f"{date_part} {time_part}", '%Y-%m-%d %H:%M:%S')
                                except:
                                    modify_date_obj = datetime.strptime(modify_date[:19], '%Y-%m-%d %H:%M:%S')
                            else:
                                # Standard format: YYYY-MM-DD HH:MM:SS
                                modify_date_obj = datetime.strptime(modify_date, '%Y-%m-%d %H:%M:%S')
                        else:
                            modify_date_obj = modify_date
                        
                        if modify_date_obj:
                            now = datetime.now()
                            if modify_date_obj.tzinfo:
                                modify_date_obj = modify_date_obj.replace(tzinfo=None)
                            
                            time_diff = now - modify_date_obj
                            
                            # NEW: updated within last 3 months (90 days)
                            if time_diff.days <= 90:
                                is_new = True
                            
                            # Stale: not updated in last 2 years (730 days)
                            if time_diff.days > 730:
                                is_stale = True
                    except Exception as e:
                        logging.writeToFile(f"Error calculating NEW/Stale for {plugin_name}: {str(e)}")
                
                # Extract paid plugin information - support both Patreon and PayPal
                paid_elem = root.find('paid')
                
                is_paid = False
                patreon_tier = None
                patreon_url = None
                paypal_me_url = None
                paypal_payment_link = None
                payment_type = None
                
                if paid_elem is not None and paid_elem.text and str(paid_elem.text).strip().lower() == 'true':
                    is_paid = True
                    
                    # Check for PayPal payment method first
                    paypal_me_elem = root.find('paypal_me_url')
                    paypal_payment_link_elem = root.find('paypal_payment_link')
                    
                    if (paypal_me_elem is not None and paypal_me_elem.text) or (paypal_payment_link_elem is not None and paypal_payment_link_elem.text):
                        # This is a PayPal plugin
                        payment_type = 'paypal'
                        paypal_me_url = paypal_me_elem.text if paypal_me_elem is not None and paypal_me_elem.text else None
                        paypal_payment_link = paypal_payment_link_elem.text if paypal_payment_link_elem is not None and paypal_payment_link_elem.text else None
                        patreon_tier = None
                        patreon_url = None
                    else:
                        # This is a Patreon plugin (default/fallback)
                        payment_type = 'patreon'
                        patreon_tier_elem = root.find('patreon_tier')
                        patreon_tier = patreon_tier_elem.text if patreon_tier_elem is not None and patreon_tier_elem.text else 'CyberPanel Paid Plugin'
                        patreon_url_elem = root.find('patreon_url')
                        patreon_url = patreon_url_elem.text if patreon_url_elem is not None and patreon_url_elem.text else 'https://www.patreon.com/c/newstargeted/membership'
                        paypal_me_url = None
                        paypal_payment_link = None
                
                plugin_data = {
                    'plugin_dir': plugin_name,
                    'name': root.find('name').text if root.find('name') is not None else plugin_name,
                    'type': root.find('type').text if root.find('type') is not None else 'Plugin',
                    'description': root.find('description').text if root.find('description') is not None else '',
                    'version': root.find('version').text if root.find('version') is not None else '1.0.0',
                    'url': root.find('url').text if root.find('url') is not None else f'/plugins/{plugin_name}/',
                    'settings_url': root.find('settings_url').text if root.find('settings_url') is not None else f'/plugins/{plugin_name}/settings/',
                    'author': root.find('author').text if root.find('author') is not None else 'Unknown',
                    'github_url': f'https://github.com/master3395/cyberpanel-plugins/tree/main/{plugin_name}',
                    'about_url': f'https://github.com/master3395/cyberpanel-plugins/tree/main/{plugin_name}',
                    'modify_date': modify_date,
                    'is_paid': bool(is_paid),  # Force boolean type
                    'patreon_tier': patreon_tier,
                    'patreon_url': patreon_url,
                    'paypal_me_url': paypal_me_url,
                    'paypal_payment_link': paypal_payment_link,
                    'payment_type': payment_type,
                    'is_new': is_new,
                    'is_stale': is_stale
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
    mailUtilities.checkHome()
    
    # Add cache-busting headers to prevent browser caching
    response_headers = {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
    }
    
    # Try to get from cache first
    cached_plugins = _get_cached_plugins()
    if cached_plugins is not None:
        # Sort plugins deterministically by name to prevent order changes
        cached_plugins.sort(key=lambda x: x.get('name', '').lower())
        
        # Enrich cached plugins with installed/enabled status
        enriched_plugins = _enrich_store_plugins(cached_plugins)
        response = JsonResponse({
            'success': True,
            'plugins': enriched_plugins,
            'cached': True
        }, json_dumps_params={'ensure_ascii': False})
        # Add headers
        for key, value in response_headers.items():
            response[key] = value
        return response
    
    # Cache miss or expired - fetch from GitHub
    try:
        plugins = _fetch_plugins_from_github()
        
        # Sort plugins deterministically by name to prevent order changes
        plugins.sort(key=lambda x: x.get('name', '').lower())
        
        # Enrich plugins with installed/enabled status
        enriched_plugins = _enrich_store_plugins(plugins)
        
        # Save to cache (save original, not enriched, to keep cache clean)
        if plugins:
            _save_plugins_cache(plugins)
        
        response = JsonResponse({
            'success': True,
            'plugins': enriched_plugins,
            'cached': False
        }, json_dumps_params={'ensure_ascii': False})
        # Add cache-busting headers
        for key, value in response_headers.items():
            response[key] = value
        return response
    
    except Exception as e:
        error_message = str(e)
        
        # If rate limited, try to use stale cache as fallback
        if '403' in error_message or 'rate limit' in error_message.lower():
            stale_cache = _get_cached_plugins(allow_expired=True)  # Get cache even if expired
            if stale_cache is not None:
                logging.writeToFile("Using stale cache due to rate limit")
                # Sort plugins deterministically by name to prevent order changes
                stale_cache.sort(key=lambda x: x.get('name', '').lower())
                enriched_plugins = _enrich_store_plugins(stale_cache)
                response = JsonResponse({
                    'success': True,
                    'plugins': enriched_plugins,
                    'cached': True,
                    'warning': 'Using cached data due to GitHub rate limit. Data may be outdated.'
                }, json_dumps_params={'ensure_ascii': False})
                # Add cache-busting headers
                for key, value in response_headers.items():
                    response[key] = value
                return response
        
        # No cache available, return error
        return JsonResponse({
            'success': False,
            'error': error_message,
            'plugins': []
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def install_from_store(request, plugin_name):
    """Install plugin from GitHub store, with fallback to local source"""
    mailUtilities.checkHome()
    
    try:
        # Check if already installed (must have meta.xml to be considered installed)
        pluginInstalled = '/usr/local/CyberCP/' + plugin_name
        if os.path.exists(pluginInstalled):
            # Check if it's a valid installation (has meta.xml) or just leftover files
            metaXmlPath = os.path.join(pluginInstalled, 'meta.xml')
            if os.path.exists(metaXmlPath):
                return JsonResponse({
                    'success': False,
                    'error': f'Plugin already installed: {plugin_name}'
                }, status=400)
            else:
                # Directory exists but no meta.xml - likely incomplete/uninstalled
                # Try to clean it up first using pluginInstaller.removeFiles which handles permissions
                try:
                    from pluginInstaller.pluginInstaller import pluginInstaller
                    pluginInstaller.removeFiles(plugin_name)
                    logging.writeToFile(f'Cleaned up incomplete plugin directory: {plugin_name}')
                except Exception as e:
                    logging.writeToFile(f'Warning: Could not clean up incomplete directory: {str(e)}')
                    # Try fallback: use system rm -rf
                    try:
                        import subprocess
                        result = subprocess.run(['rm', '-rf', pluginInstalled], capture_output=True, text=True, timeout=30)
                        if result.returncode == 0:
                            logging.writeToFile(f'Cleaned up incomplete plugin directory using rm -rf: {plugin_name}')
                        else:
                            raise Exception(f"rm -rf failed: {result.stderr}")
                    except Exception as e2:
                        logging.writeToFile(f'Error: Both cleanup methods failed: {str(e)}, {str(e2)}')
                        return JsonResponse({
                            'success': False,
                            'error': f'Incomplete plugin directory found. Please uninstall first or manually remove: {pluginInstalled}'
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
                
                # Find plugin directory in ZIP
                plugin_prefix = f'cyberpanel-plugins-main/{plugin_name}/'
                plugin_files = [f for f in repo_zip.namelist() if f.startswith(plugin_prefix)]
                
                if not plugin_files:
                    logging.writeToFile(f"Plugin {plugin_name} not found in GitHub repository, trying local source")
                    use_local_fallback = True
                else:
                    logging.writeToFile(f"Found {len(plugin_files)} files for plugin {plugin_name} in GitHub")
                    
                    # Create plugin ZIP file from GitHub with correct structure
                    # The ZIP must contain plugin_name/ directory structure for proper extraction
                    plugin_zip = zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED)
                    
                    for file_path in plugin_files:
                        # Remove the repository root prefix
                        relative_path = file_path[len(plugin_prefix):]
                        if relative_path:  # Skip directories
                            file_data = repo_zip.read(file_path)
                            # Add plugin_name prefix to maintain directory structure
                            arcname = os.path.join(plugin_name, relative_path)
                            plugin_zip.writestr(arcname, file_data)
                    
                    plugin_zip.close()
                    repo_zip.close()
            except Exception as github_error:
                logging.writeToFile(f"GitHub download failed for {plugin_name}: {str(github_error)}, trying local source")
                use_local_fallback = True
            
            # Fallback to local source if GitHub download failed
            if use_local_fallback:
                pluginSource = '/home/cyberpanel/plugins/' + plugin_name
                if not os.path.exists(pluginSource):
                    raise Exception(f'Plugin {plugin_name} not found in GitHub repository and local source not found at {pluginSource}')
                
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
            
            # Copy ZIP to current directory (pluginInstaller expects it in cwd)
            original_cwd = os.getcwd()
            os.chdir(temp_dir)
            
            try:
                # Verify zip file exists in current directory
                zip_file = plugin_name + '.zip'
                if not os.path.exists(zip_file):
                    raise Exception(f'Zip file {zip_file} not found in temp directory')
                
                logging.writeToFile(f"Installing plugin using pluginInstaller")
                
                # Install using pluginInstaller (direct call, not via command line)
                try:
                    pluginInstaller.installPlugin(plugin_name)
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
                time.sleep(2)  # Wait for file system sync
                
                # Restart lscpd service to ensure plugin loads immediately
                try:
                    logging.writeToFile(f"Restarting lscpd service after plugin installation...")
                    subprocess.run(['systemctl', 'restart', 'lscpd'], check=True, timeout=30)
                    logging.writeToFile(f"lscpd service restarted successfully")
                    time.sleep(2)  # Wait for service to fully restart
                except subprocess.TimeoutExpired:
                    logging.writeToFile(f"Warning: lscpd restart timed out, but continuing...")
                except Exception as restart_error:
                    logging.writeToFile(f"Warning: Failed to restart lscpd: {str(restart_error)}")
                    # Don't fail installation if restart fails, just log it
                
                # Verify plugin was actually installed
                pluginInstalled = '/usr/local/CyberCP/' + plugin_name
                if not os.path.exists(pluginInstalled):
                    # Check if files were extracted to root instead
                    root_files = ['README.md', 'apps.py', 'meta.xml', 'urls.py', 'views.py']
                    found_root_files = [f for f in root_files if os.path.exists(os.path.join('/usr/local/CyberCP', f))]
                    if found_root_files:
                        raise Exception(f'Plugin installation failed: Files extracted to wrong location. Found {found_root_files} in /usr/local/CyberCP/ root instead of {pluginInstalled}/')
                    raise Exception(f'Plugin installation failed: {pluginInstalled} does not exist after installation')
                
                logging.writeToFile(f"Plugin {plugin_name} installed successfully")
                
                # Set plugin to enabled by default after installation
                _set_plugin_state(plugin_name, True)
                
                return JsonResponse({
                    'success': True,
                    'message': f'Plugin {plugin_name} installed successfully from store'
                })
            finally:
                os.chdir(original_cwd)
                
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

def plugin_help(request, plugin_name):
    """Plugin-specific help page - shows plugin information, version history, and help content"""
    mailUtilities.checkHome()
    
    # Paths for the plugin
    plugin_path = '/usr/local/CyberCP/' + plugin_name
    meta_xml_path = os.path.join(plugin_path, 'meta.xml')
    
    # Check if plugin exists
    if not os.path.exists(plugin_path) or not os.path.exists(meta_xml_path):
        proc = httpProc(request, 'pluginHolder/plugin_not_found.html', {
            'plugin_name': plugin_name
        }, 'admin')
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
        installed = os.path.exists(plugin_path)
        
    except Exception as e:
        logging.writeToFile(f"Error parsing meta.xml for {plugin_name}: {str(e)}")
        proc = httpProc(request, 'pluginHolder/plugin_not_found.html', {
            'plugin_name': plugin_name
        }, 'admin')
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
    
    proc = httpProc(request, 'pluginHolder/plugin_help.html', context, 'admin')
    return proc.render()

@csrf_exempt
@require_http_methods(["GET"])
def check_plugin_subscription(request, plugin_name):
    """
    API endpoint to check if user has Patreon subscription for a paid plugin
    
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
        # Check if user is authenticated
        if not request.user or not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'has_access': False,
                'is_paid': False,
                'message': 'Please log in to check subscription status',
                'patreon_url': None
            }, status=401)
        
        # Load plugin metadata
        from .plugin_access import check_plugin_access, _load_plugin_meta
        
        plugin_meta = _load_plugin_meta(plugin_name)
        
        # Check access
        access_result = check_plugin_access(request, plugin_name, plugin_meta)
        
        return JsonResponse({
            'success': True,
            'has_access': access_result['has_access'],
            'is_paid': access_result['is_paid'],
            'message': access_result['message'],
            'patreon_url': access_result.get('patreon_url')
        })
        
    except Exception as e:
        logging.writeToFile(f"Error checking subscription for {plugin_name}: {str(e)}")
        return JsonResponse({
            'success': False,
            'has_access': False,
            'is_paid': False,
            'message': f'Error checking subscription: {str(e)}',
            'patreon_url': None
        }, status=500)
