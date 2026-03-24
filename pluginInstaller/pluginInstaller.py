import sys
sys.path.append('/usr/local/CyberCP')
import subprocess
import shlex
import argparse
import os
import shutil
import time
import tempfile
import zipfile
import django
from plogical.processUtilities import ProcessUtilities

class pluginInstaller:
    installLogPath = "/home/cyberpanel/modSecInstallLog"
    tempRulesFile = "/home/cyberpanel/tempModSecRules"
    mirrorPath = "cyberpanel.net"

    @staticmethod
    def getUrlPattern(pluginName):
        """
        Generate URL pattern compatible with both Django 2.x and 3.x+
        Django 2.x uses url() with regex patterns
        Django 3.x+ prefers path() with simpler patterns
        Plugins are routed under /plugins/pluginName/ to match meta.xml URLs
        """
        try:
            django_version = django.get_version()
            major_version = int(django_version.split('.')[0])
            
            pluginInstaller.stdOut(f"Django version detected: {django_version}")
            
            if major_version >= 3:
                # Django 3.x+ - use path() syntax with /plugins/ prefix
                pluginInstaller.stdOut(f"Using path() syntax for Django 3.x+ compatibility")
                return "    path('plugins/" + pluginName + "/',include('" + pluginName + ".urls')),\n"
            else:
                # Django 2.x - use url() syntax with regex and /plugins/ prefix
                pluginInstaller.stdOut(f"Using url() syntax for Django 2.x compatibility")
                return "    url(r'^plugins/" + pluginName + "/',include('" + pluginName + ".urls')),\n"
        except Exception as e:
            # Fallback to modern path() syntax if version detection fails
            pluginInstaller.stdOut(f"Django version detection failed: {str(e)}, using path() syntax as fallback")
            return "    path('plugins/" + pluginName + "/',include('" + pluginName + ".urls')),\n"

    @staticmethod
    def stdOut(message):
        print("\n\n")
        print(("[" + time.strftime(
            "%m.%d.%Y_%H-%M-%S") + "] #########################################################################\n"))
        print(("[" + time.strftime("%m.%d.%Y_%H-%M-%S") + "] " + message + "\n"))
        print(("[" + time.strftime(
            "%m.%d.%Y_%H-%M-%S") + "] #########################################################################\n"))

    @staticmethod
    def migrationsEnabled(pluginName: str) -> bool:
        pluginHome = '/usr/local/CyberCP/' + pluginName
        return os.path.exists(pluginHome + '/enable_migrations')

    @staticmethod
    def _write_lines_to_protected_file(target_path, lines):
        """
        Write UTF-8 lines to a file. Core panel files are often root:root 644; the panel
        process may need a privileged copy (lscpd/sudo) to update them.
        """
        try:
            with open(target_path, 'w', encoding='utf-8') as wf:
                wf.writelines(lines)
            return
        except (PermissionError, OSError) as e:
            pluginInstaller.stdOut('Direct write failed for %s: %s' % (target_path, str(e)))
        fd, tmp_path = tempfile.mkstemp(prefix='cpwr_', suffix='.txt', dir='/tmp')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as wf:
                wf.writelines(lines)
            cmd = 'cp %s %s' % (shlex.quote(tmp_path), shlex.quote(target_path))
            if ProcessUtilities.executioner(cmd) == 1:
                pluginInstaller.stdOut('Wrote %s via privileged copy' % target_path)
                return
        except Exception as ex:
            pluginInstaller.stdOut('Privileged write failed: %s' % str(ex))
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        raise PermissionError(
            'Cannot write %s. As root: chgrp lscpd %s && chmod 664 %s'
            % (target_path, target_path, target_path)
        )

    ### Functions Related to plugin installation.

    @staticmethod
    def extractPlugin(pluginName, zip_path=None):
        """
        Extract plugin zip so that all files end up in /usr/local/CyberCP/pluginName/.
        Handles zips with: (1) top-level folder pluginName/, (2) top-level folder with
        another name (e.g. repo-main/), or (3) files at root (no top-level folder).
        If zip_path is given (absolute path), use it; otherwise use pluginName + '.zip' in cwd.
        """
        if zip_path is not None:
            pathToPlugin = os.path.abspath(zip_path)
        else:
            pathToPlugin = os.path.abspath(pluginName + '.zip')
        if not os.path.exists(pathToPlugin):
            raise Exception(f"Plugin zip not found: {pathToPlugin}")
        pluginPath = '/usr/local/CyberCP/' + pluginName
        # Remove existing plugin dir so we start clean (e.g. from a previous failed install)
        if os.path.exists(pluginPath):
            shutil.rmtree(pluginPath)
        extract_dir = tempfile.mkdtemp(prefix='cyberpanel_plugin_')
        try:
            with zipfile.ZipFile(pathToPlugin, 'r') as zf:
                zf.extractall(extract_dir)
            top_level = os.listdir(extract_dir)
            plugin_name_lower = pluginName.lower()
            # Prefer a top-level directory whose name matches pluginName (case-insensitive)
            matching_dir = None
            for name in top_level:
                if os.path.isdir(os.path.join(extract_dir, name)) and name.lower() == plugin_name_lower:
                    matching_dir = name
                    break
            if len(top_level) == 1:
                single = os.path.join(extract_dir, top_level[0])
                if os.path.isdir(single):
                    # One top-level directory
                    single_name = top_level[0]
                    # If it's the repo root (e.g. cyberpanel-plugins-main), check for plugin subdir
                    if single_name.lower() != plugin_name_lower:
                        plugin_subdir = os.path.join(single, pluginName)
                        if not os.path.isdir(plugin_subdir):
                            # Try case-insensitive subdir match
                            for entry in os.listdir(single):
                                if os.path.isdir(os.path.join(single, entry)) and entry.lower() == plugin_name_lower:
                                    plugin_subdir = os.path.join(single, entry)
                                    break
                        if os.path.isdir(plugin_subdir):
                            # Use the plugin subdir as the plugin content (avoid nesting repo root)
                            shutil.move(plugin_subdir, pluginPath)
                            shutil.rmtree(single, ignore_errors=True)
                        else:
                            shutil.move(single, pluginPath)
                    else:
                        shutil.move(single, pluginPath)
                else:
                    # Single file at root
                    os.makedirs(pluginPath, exist_ok=True)
                    shutil.move(single, os.path.join(pluginPath, top_level[0]))
            elif matching_dir:
                # Multiple items: one is a dir matching pluginName - use it as plugin, put rest inside pluginPath
                os.makedirs(pluginPath, exist_ok=True)
                src_match = os.path.join(extract_dir, matching_dir)
                # Move the matching plugin dir to pluginPath (replace if exists)
                if os.path.exists(pluginPath):
                    shutil.rmtree(pluginPath)
                shutil.move(src_match, pluginPath)
                for name in top_level:
                    if name == matching_dir:
                        continue
                    src = os.path.join(extract_dir, name)
                    dst = os.path.join(pluginPath, name)
                    if os.path.exists(dst):
                        if os.path.isdir(dst):
                            shutil.rmtree(dst)
                        else:
                            os.remove(dst)
                    shutil.move(src, dst)
            else:
                # Multiple items or empty: place everything inside pluginName/
                os.makedirs(pluginPath, exist_ok=True)
                for name in top_level:
                    src = os.path.join(extract_dir, name)
                    dst = os.path.join(pluginPath, name)
                    if os.path.exists(dst):
                        if os.path.isdir(dst):
                            shutil.rmtree(dst)
                        else:
                            os.remove(dst)
                    shutil.move(src, dst)
            if not os.path.exists(pluginPath):
                raise Exception(f"Plugin extraction failed: {pluginPath} does not exist after extraction")
        finally:
            shutil.rmtree(extract_dir, ignore_errors=True)

    @staticmethod
    def upgradingSettingsFile(pluginName):
        settings_path = "/usr/local/CyberCP/CyberCP/settings.py"
        with open(settings_path, 'r', encoding='utf-8') as rf:
            data = rf.readlines()
        line_plugin = "    '" + pluginName + "',\n"
        if any(line.strip() in ("'" + pluginName + "',", '"' + pluginName + '",') for line in data):
            pluginInstaller.stdOut(
                'Plugin %s already listed in settings.py; skipping INSTALLED_APPS insert.' % pluginName
            )
            return
        out = []
        inserted = False
        for items in data:
            if items.find("'emailPremium',") > -1:
                out.append(items)
                out.append(line_plugin)
                inserted = True
            else:
                out.append(items)
        if not inserted:
            out = []
            for items in data:
                if "'pluginHolder'," in items or '"pluginHolder",' in items:
                    out.append(items)
                    out.append(line_plugin)
                    inserted = True
                else:
                    out.append(items)
        if not inserted:
            pluginInstaller.stdOut(
                'Warning: no emailPremium or pluginHolder anchor in settings.py; '
                'add %r to INSTALLED_APPS manually or upgrade CyberPanel (auto-sync plugins on disk).'
                % pluginName
            )
            return
        pluginInstaller._write_lines_to_protected_file(settings_path, out)

    @staticmethod
    def upgradingURLs(pluginName):
        """
        Legacy: add explicit path('plugins/<name>/', ...). Modern CyberPanel uses
        pluginHolder.urls for all plugins — skip to avoid duplicate routes and root-only writes.
        """
        urls_path = "/usr/local/CyberCP/CyberCP/urls.py"
        with open(urls_path, 'r', encoding='utf-8') as rf:
            content = rf.read()
        if "include('pluginHolder.urls')" in content or 'include("pluginHolder.urls")' in content:
            pluginInstaller.stdOut(
                'pluginHolder.urls found; skipping per-plugin urls.py line for %s (dynamic routes).' % pluginName
            )
            return
        data = content.splitlines(keepends=True)
        out = []
        urlPatternAdded = False
        for items in data:
            if items.find("path('plugins/', include('pluginHolder.urls'))") > -1 or items.find(
                "path(\"plugins/\", include('pluginHolder.urls'))"
            ) > -1:
                if not urlPatternAdded:
                    out.append(pluginInstaller.getUrlPattern(pluginName))
                    urlPatternAdded = True
                out.append(items)
            else:
                out.append(items)
        if not urlPatternAdded:
            pluginInstaller.stdOut("Warning: 'plugins/' line not found, using fallback insertion after 'manageservices'")
            out = []
            for items in data:
                if items.find("manageservices") > -1:
                    out.append(items)
                    out.append(pluginInstaller.getUrlPattern(pluginName))
                    urlPatternAdded = True
                else:
                    out.append(items)
        pluginInstaller._write_lines_to_protected_file(urls_path, out)

    @staticmethod
    def informCyberPanel(pluginName):
        pluginPath = '/home/cyberpanel/plugins'

        if not os.path.exists(pluginPath):
            os.mkdir(pluginPath)

        pluginFile = pluginPath + '/' + pluginName
        command = 'touch ' + pluginFile
        subprocess.call(shlex.split(command))

    @staticmethod
    def addInterfaceLink(pluginName):
        path_html = "/usr/local/CyberCP/baseTemplate/templates/baseTemplate/index.html"
        with open(path_html, 'r', encoding='utf-8') as rf:
            data = rf.readlines()
        out = []
        for items in data:
            if items.find("{# pluginsList #}") > -1:
                out.append(items)
                out.append("                                ")
                out.append(
                    '<li><a href="{% url \'' + pluginName + '\' %}" title="{% trans \'' + pluginName + '\' %}"><span>{% trans "' + pluginName + '" %}</span></a></li>\n'
                )
            else:
                out.append(items)
        pluginInstaller._write_lines_to_protected_file(path_html, out)

    @staticmethod
    def staticContent():
        currentDir = os.getcwd()

        command = "rm -rf /usr/local/lscp/cyberpanel/static"
        subprocess.call(shlex.split(command))

        os.chdir('/usr/local/CyberCP')

        command = "python3 /usr/local/CyberCP/manage.py collectstatic --noinput"
        subprocess.call(shlex.split(command))

        command = "mv /usr/local/CyberCP/static /usr/local/lscp/cyberpanel"
        subprocess.call(shlex.split(command))


        os.chdir(currentDir)

    @staticmethod
    def installMigrations(pluginName):
        currentDir = os.getcwd()
        os.chdir('/usr/local/CyberCP')
        command = "python3 /usr/local/CyberCP/manage.py makemigrations %s" % pluginName
        subprocess.call(shlex.split(command))
        command = "python3 /usr/local/CyberCP/manage.py migrate %s" % pluginName
        subprocess.call(shlex.split(command))
        os.chdir(currentDir)


    @staticmethod
    def preInstallScript(pluginName):
        pluginHome = '/usr/local/CyberCP/' + pluginName

        if os.path.exists(pluginHome + '/pre_install'):
            command = 'chmod +x ' + pluginHome + '/pre_install'
            subprocess.call(shlex.split(command))

            command = pluginHome + '/pre_install'
            subprocess.call(shlex.split(command))

    @staticmethod
    def postInstallScript(pluginName):
        pluginHome = '/usr/local/CyberCP/' + pluginName

        if os.path.exists(pluginHome + '/post_install'):
            command = 'chmod +x ' + pluginHome + '/post_install'
            subprocess.call(shlex.split(command))

            command = pluginHome + '/post_install'
            subprocess.call(shlex.split(command))

    @staticmethod
    def preRemoveScript(pluginName):
        pluginHome = '/usr/local/CyberCP/' + pluginName

        if os.path.exists(pluginHome + '/pre_remove'):
            command = 'chmod +x ' + pluginHome + '/pre_remove'
            subprocess.call(shlex.split(command))

            command = pluginHome + '/pre_remove'
            subprocess.call(shlex.split(command))


    @staticmethod
    def installPlugin(pluginName, zip_path=None):
        try:
            ##

            pluginInstaller.stdOut('Extracting plugin..')
            pluginInstaller.extractPlugin(pluginName, zip_path=zip_path)
            pluginInstaller.stdOut('Plugin extracted.')

            ##

            pluginInstaller.stdOut('Executing pre_install script..')
            pluginInstaller.preInstallScript(pluginName)
            pluginInstaller.stdOut('pre_install executed.')

            ##

            pluginInstaller.stdOut('Restoring settings file.')
            pluginInstaller.upgradingSettingsFile(pluginName)
            pluginInstaller.stdOut('Settings file restored.')

            ##

            pluginInstaller.stdOut('Upgrading URLs')
            pluginInstaller.upgradingURLs(pluginName)
            pluginInstaller.stdOut('URLs upgraded.')

            ##

            pluginInstaller.stdOut('Informing CyberPanel about plugin.')
            pluginInstaller.informCyberPanel(pluginName)
            pluginInstaller.stdOut('CyberPanel core informed about the plugin.')

            ##

            pluginInstaller.stdOut('Adding interface link..')
            pluginInstaller.addInterfaceLink(pluginName)
            pluginInstaller.stdOut('Interface link added.')

            ##

            pluginInstaller.stdOut('Upgrading static content..')
            pluginInstaller.staticContent()
            pluginInstaller.stdOut('Static content upgraded.')

            ##

            if pluginInstaller.migrationsEnabled(pluginName):
                pluginInstaller.stdOut('Running Migrations..')
                pluginInstaller.installMigrations(pluginName)
                pluginInstaller.stdOut('Migrations Completed..')
            else:
                pluginInstaller.stdOut('Migrations not enabled, add file \'enable_migrations\' to plugin to enable')

            ##

            pluginInstaller.restartGunicorn()

            ##

            pluginInstaller.stdOut('Executing post_install script..')
            pluginInstaller.postInstallScript(pluginName)
            pluginInstaller.stdOut('post_install executed.')

            ##

            pluginInstaller.stdOut('Plugin successfully installed.')

        except BaseException as msg:
            pluginInstaller.stdOut(str(msg))

    ### Functions Related to plugin installation.

    @staticmethod
    def removeFiles(pluginName):
        pluginPath = '/usr/local/CyberCP/' + pluginName
        if not os.path.exists(pluginPath):
            # Directory doesn't exist - already removed
            pluginInstaller.stdOut(f'Plugin directory does not exist (already removed): {pluginName}')
            return
        
        try:
            # Check if we're running as root
            is_root = os.geteuid() == 0 if hasattr(os, 'geteuid') else False
            use_sudo = not is_root
            
            # First try: Use shutil.rmtree (works if permissions are correct)
            try:
                shutil.rmtree(pluginPath)
                pluginInstaller.stdOut(f'Plugin directory removed: {pluginName}')
                return
            except (OSError, PermissionError) as e:
                pluginInstaller.stdOut(f'Direct removal failed, trying with permission fix: {str(e)}')
            
            # Second try: Fix permissions, then remove
            try:
                import subprocess
                import stat
                
                if use_sudo:
                    # Use ProcessUtilities which handles privileged commands
                    # Fix ownership recursively
                    chown_cmd = f'chown -R cyberpanel:cyberpanel {pluginPath}'
                    ProcessUtilities.normalExecutioner(chown_cmd)
                    
                    # Fix permissions recursively
                    chmod_cmd = f'chmod -R u+rwX,go+rX {pluginPath}'
                    ProcessUtilities.normalExecutioner(chmod_cmd)
                else:
                    # Running as root - fix permissions directly
                    import pwd
                    import grp
                    try:
                        cyberpanel_uid = pwd.getpwnam('cyberpanel').pw_uid
                        cyberpanel_gid = grp.getgrnam('cyberpanel').gr_gid
                    except (KeyError, OSError):
                        cyberpanel_uid = 0
                        cyberpanel_gid = 0
                    
                    # Recursively fix ownership and permissions
                    for root, dirs, files in os.walk(pluginPath):
                        try:
                            os.chown(root, cyberpanel_uid, cyberpanel_gid)
                            os.chmod(root, stat.S_IRWXU | stat.S_IRWXG | stat.S_IROTH | stat.S_IXOTH)
                        except (OSError, PermissionError):
                            pass
                        
                        for d in dirs:
                            dir_path = os.path.join(root, d)
                            try:
                                os.chown(dir_path, cyberpanel_uid, cyberpanel_gid)
                                os.chmod(dir_path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IROTH | stat.S_IXOTH)
                            except (OSError, PermissionError):
                                pass
                        
                        for f in files:
                            file_path = os.path.join(root, f)
                            try:
                                os.chown(file_path, cyberpanel_uid, cyberpanel_gid)
                                os.chmod(file_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
                            except (OSError, PermissionError):
                                pass
                
                # Now try to remove
                shutil.rmtree(pluginPath)
                pluginInstaller.stdOut(f'Plugin directory removed after permission fix: {pluginName}')
                return
            except Exception as e:
                pluginInstaller.stdOut(f'Permission fix and removal failed: {str(e)}')
            
            # Third try: Use rm -rf (with or without sudo depending on privileges)
            try:
                if use_sudo:
                    # Use ProcessUtilities for privileged removal
                    rm_cmd = f'rm -rf {pluginPath}'
                    ProcessUtilities.normalExecutioner(rm_cmd)
                else:
                    # Running as root - use subprocess directly
                    result = subprocess.run(
                        ['rm', '-rf', pluginPath],
                        capture_output=True, text=True, timeout=30
                    )
                    if result.returncode != 0:
                        raise Exception(f"rm -rf failed: {result.stderr}")
                
                pluginInstaller.stdOut(f'Plugin directory removed using rm -rf: {pluginName}')
                return
            except Exception as e:
                raise Exception(f"All removal methods failed. Last error: {str(e)}")
                
        except Exception as e:
            pluginInstaller.stdOut(f"Error removing plugin files: {str(e)}")
            raise Exception(f"Failed to remove plugin directory: {str(e)}")

    @staticmethod
    def removeFromSettings(pluginName):
        settings_path = "/usr/local/CyberCP/CyberCP/settings.py"
        try:
            with open(settings_path, 'r', encoding='utf-8') as f:
                data = f.readlines()
        except (OSError, IOError) as e:
            raise Exception(f'Cannot read {settings_path}: {e}. Ensure the panel user can read it.')
        in_installed_apps = False
        out_lines = []
        for i, items in enumerate(data):
            if 'INSTALLED_APPS' in items and '=' in items:
                in_installed_apps = True
            elif in_installed_apps and items.strip().startswith(']'):
                in_installed_apps = False
            if in_installed_apps and (f"'{pluginName}'" in items or f'"{pluginName}"' in items):
                continue
            out_lines.append(items)
        try:
            pluginInstaller._write_lines_to_protected_file(settings_path, out_lines)
        except (OSError, IOError, PermissionError) as e:
            raise Exception(
                f'Cannot write {settings_path}: {e}. '
                'Ensure the file is writable by the panel user (e.g. chgrp lscpd ... ; chmod g+w ...).'
            )

    @staticmethod
    def removeFromURLs(pluginName):
        urls_path = "/usr/local/CyberCP/CyberCP/urls.py"
        try:
            with open(urls_path, 'r', encoding='utf-8') as f:
                data = f.readlines()
        except (OSError, IOError) as e:
            raise Exception(f'Cannot read {urls_path}: {e}.')
        out_lines = []
        for items in data:
            if (f"plugins/{pluginName}/" in items or f"'{pluginName}.urls'" in items or f'"{pluginName}.urls"' in items or
                f"include('{pluginName}.urls')" in items or f'include("{pluginName}.urls")' in items):
                continue
            out_lines.append(items)
        try:
            pluginInstaller._write_lines_to_protected_file(urls_path, out_lines)
        except (OSError, IOError, PermissionError) as e:
            raise Exception(f'Cannot write {urls_path}: {e}. Ensure the file is writable by the panel user (chgrp lscpd; chmod g+w).')

    @staticmethod
    def informCyberPanelRemoval(pluginName):
        pluginPath = '/home/cyberpanel/plugins'
        pluginFile = pluginPath + '/' + pluginName
        if os.path.exists(pluginFile):
            os.remove(pluginFile)

    @staticmethod
    def removeInterfaceLink(pluginName):
        path_html = "/usr/local/CyberCP/baseTemplate/templates/baseTemplate/index.html"
        with open(path_html, 'r', encoding='utf-8') as rf:
            data = rf.readlines()
        out = []
        for items in data:
            if items.find(pluginName) > -1 and items.find('<li>') > -1:
                continue
            out.append(items)
        pluginInstaller._write_lines_to_protected_file(path_html, out)

    @staticmethod
    def removeMigrations(pluginName):
        currentDir = os.getcwd()
        os.chdir('/usr/local/CyberCP')
        command = "python3 /usr/local/CyberCP/manage.py migrate %s zero" % pluginName
        subprocess.call(shlex.split(command))
        os.chdir(currentDir)

    @staticmethod
    def removePlugin(pluginName):
        try:
            ##

            pluginInstaller.stdOut('Executing pre_remove script..')
            pluginInstaller.preRemoveScript(pluginName)
            pluginInstaller.stdOut('pre_remove executed.')

            ##

            if pluginInstaller.migrationsEnabled(pluginName):
                pluginInstaller.stdOut('Removing migrations..')
                pluginInstaller.removeMigrations(pluginName)
                pluginInstaller.stdOut('Migrations removed..')
            else:
                pluginInstaller.stdOut('Migrations not enabled, add file \'enable_migrations\' to plugin to enable')

            ##

            pluginInstaller.stdOut('Removing files..')
            pluginInstaller.removeFiles(pluginName)
            pluginInstaller.stdOut('Files removed..')

            ##

            pluginInstaller.stdOut('Restoring settings file.')
            pluginInstaller.removeFromSettings(pluginName)
            pluginInstaller.stdOut('Settings file restored.')

            ###

            pluginInstaller.stdOut('Upgrading URLs')
            pluginInstaller.removeFromURLs(pluginName)
            pluginInstaller.stdOut('URLs upgraded.')

            ##

            pluginInstaller.stdOut('Informing CyberPanel about plugin removal.')
            pluginInstaller.informCyberPanelRemoval(pluginName)
            pluginInstaller.stdOut('CyberPanel core informed about the plugin removal.')

            ##

            pluginInstaller.stdOut('Remove interface link..')
            pluginInstaller.removeInterfaceLink(pluginName)
            pluginInstaller.stdOut('Interface link removed.')

            ##

            pluginInstaller.restartGunicorn()

            pluginInstaller.stdOut('Plugin successfully removed.')

        except BaseException as msg:
            pluginInstaller.stdOut(str(msg))

    ####

    @staticmethod
    def restartGunicorn():
        command = 'systemctl restart lscpd'
        ProcessUtilities.normalExecutioner(command)




def main():

    parser = argparse.ArgumentParser(description='CyberPanel Installer')
    parser.add_argument('function', help='Specify a function to call!')

    parser.add_argument('--pluginName', help='Temporary path to configurations data!')


    args = parser.parse_args()
    if args.function == 'install':
        pluginInstaller.installPlugin(args.pluginName)
    else:
        pluginInstaller.removePlugin(args.pluginName)

if __name__ == "__main__":
    main()