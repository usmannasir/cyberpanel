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
                
                processed_plugins.add(plugin)
                
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
                
                # Extract settings URL or main URL for "Manage" button
                settings_url_elem = root.find('settings_url')
                url_elem = root.find('url')
                
                # Priority: settings_url > url > default pattern
                if settings_url_elem is not None and settings_url_elem.text:
                    data['manage_url'] = settings_url_elem.text
                elif url_elem is not None and url_elem.text:
                    data['manage_url'] = url_elem.text
                else:
                    # Default: try /plugins/{plugin_dir}/settings/ or /plugins/{plugin_dir}/
                    # Only set if plugin is installed (we can't know if the URL exists otherwise)
                    if os.path.exists(completePath):
                        data['manage_url'] = f'/plugins/{plugin}/settings/'
                    else:
                        data['manage_url'] = None

                pluginList.append(data)
            except ElementTree.ParseError as e:
                errorPlugins.append({'name': plugin, 'error': f'XML parse error: {str(e)}'})
                logging.writeToFile(f"Plugin {plugin}: XML parse error - {str(e)}")
                continue
            except Exception as e:
                errorPlugins.append({'name': plugin, 'error': f'Error loading plugin: {str(e)}'})
                logging.writeToFile(f"Plugin {plugin}: Error loading - {str(e)}")
                continue

    proc = httpProc(request, 'pluginHolder/plugins.html',
                    {'plugins': pluginList, 'error_plugins': errorPlugins}, 'admin')
    return proc.render()

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
        temp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(temp_dir, plugin_name + '.zip')
        
        # Create zip from source directory
        shutil.make_archive(os.path.join(temp_dir, plugin_name), 'zip', pluginSource)
        
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
            pluginInstaller.installPlugin(plugin_name)
            
            # Verify plugin was actually installed
            pluginInstalled = '/usr/local/CyberCP/' + plugin_name
            if not os.path.exists(pluginInstalled):
                raise Exception(f'Plugin installation failed: {pluginInstalled} does not exist after installation')
            
            # Set plugin to enabled by default after installation
            _set_plugin_state(plugin_name, True)
            
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
        installed_path = os.path.join(plugin_install_dir, plugin_dir)
        source_path = os.path.join(plugin_source_dir, plugin_dir)
        
        plugin['installed'] = os.path.exists(installed_path) or os.path.exists(source_path)
        
        # Check if plugin is enabled (only if installed)
        if plugin['installed']:
            plugin['enabled'] = _is_plugin_enabled(plugin_dir)
        else:
            plugin['enabled'] = False
        
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
                    'modify_date': modify_date
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
    
    # Try to get from cache first
    cached_plugins = _get_cached_plugins()
    if cached_plugins is not None:
        # Enrich cached plugins with installed/enabled status
        enriched_plugins = _enrich_store_plugins(cached_plugins)
        return JsonResponse({
            'success': True,
            'plugins': enriched_plugins,
            'cached': True
        })
    
    # Cache miss or expired - fetch from GitHub
    try:
        plugins = _fetch_plugins_from_github()
        
        # Enrich plugins with installed/enabled status
        enriched_plugins = _enrich_store_plugins(plugins)
        
        # Save to cache (save original, not enriched, to keep cache clean)
        if plugins:
            _save_plugins_cache(plugins)
        
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
def install_from_store(request, plugin_name):
    """Install plugin from GitHub store"""
    mailUtilities.checkHome()
    
    try:
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
                raise Exception(f'Plugin {plugin_name} not found in GitHub repository')
            
            logging.writeToFile(f"Found {len(plugin_files)} files for plugin {plugin_name}")
            
            # Create plugin ZIP file
            plugin_zip = zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED)
            
            for file_path in plugin_files:
                # Remove the repository root prefix
                relative_path = file_path[len(plugin_prefix):]
                if relative_path:  # Skip directories
                    file_data = repo_zip.read(file_path)
                    plugin_zip.writestr(relative_path, file_data)
            
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
                pluginInstaller.installPlugin(plugin_name)
                
                # Wait a moment for file system to sync and service to restart
                import time
                time.sleep(2)
                
                # Verify plugin was actually installed
                pluginInstalled = '/usr/local/CyberCP/' + plugin_name
                if not os.path.exists(pluginInstalled):
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
    """Plugin-specific help page"""
    mailUtilities.checkHome()
    return redirect('/plugins/help/')
