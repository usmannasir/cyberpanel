# -*- coding: utf-8 -*-
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from plogical.mailUtilities import mailUtilities
import os
import subprocess
import shlex
import json
from xml.etree import ElementTree
from plogical.httpProc import httpProc
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
import sys
sys.path.append('/usr/local/CyberCP')
from pluginInstaller.pluginInstaller import pluginInstaller

# Plugin state file location
PLUGIN_STATE_DIR = '/home/cyberpanel/plugin_states'

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

def installed(request):
    mailUtilities.checkHome()
    pluginPath = '/home/cyberpanel/plugins'
    pluginList = []
    errorPlugins = []

    if os.path.exists(pluginPath):
        for plugin in os.listdir(pluginPath):
            # Skip files (like .zip files) - only process directories
            pluginDir = os.path.join(pluginPath, plugin)
            if not os.path.isdir(pluginDir):
                continue
            
            data = {}
            # Try installed location first, then fallback to source location
            completePath = '/usr/local/CyberCP/' + plugin + '/meta.xml'
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
