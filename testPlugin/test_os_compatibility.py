#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OS Compatibility Test Script for Test Plugin
Tests the plugin on different operating systems
"""
import os
import sys
import subprocess
import platform
import json
from pathlib import Path

# Add the plugin directory to Python path
plugin_dir = Path(__file__).parent
sys.path.insert(0, str(plugin_dir))

from os_config import OSConfig


class OSCompatibilityTester:
    """Test OS compatibility for the Test Plugin"""
    
    def __init__(self):
        self.os_config = OSConfig()
        self.test_results = {}
        
    def run_all_tests(self):
        """Run all compatibility tests"""
        print("🔍 Testing OS Compatibility for CyberPanel Test Plugin")
        print("=" * 60)
        
        # Test 1: OS Detection
        self.test_os_detection()
        
        # Test 2: Python Detection
        self.test_python_detection()
        
        # Test 3: Package Manager Detection
        self.test_package_manager_detection()
        
        # Test 4: Service Manager Detection
        self.test_service_manager_detection()
        
        # Test 5: Web Server Detection
        self.test_web_server_detection()
        
        # Test 6: File Permissions
        self.test_file_permissions()
        
        # Test 7: Network Connectivity
        self.test_network_connectivity()
        
        # Test 8: CyberPanel Integration
        self.test_cyberpanel_integration()
        
        # Display results
        self.display_results()
        
        return self.test_results
    
    def test_os_detection(self):
        """Test OS detection functionality"""
        print("\n📋 Testing OS Detection...")
        
        try:
            os_info = self.os_config.get_os_info()
            is_supported = self.os_config.is_supported_os()
            
            self.test_results['os_detection'] = {
                'status': 'PASS',
                'os_name': os_info['name'],
                'os_version': os_info['version'],
                'os_arch': os_info['architecture'],
                'is_supported': is_supported,
                'platform': os_info['platform']
            }
            
            print(f"   ✅ OS: {os_info['name']} {os_info['version']} ({os_info['architecture']})")
            print(f"   ✅ Supported: {is_supported}")
            
        except Exception as e:
            self.test_results['os_detection'] = {
                'status': 'FAIL',
                'error': str(e)
            }
            print(f"   ❌ Error: {e}")
    
    def test_python_detection(self):
        """Test Python detection and version"""
        print("\n🐍 Testing Python Detection...")
        
        try:
            python_path = self.os_config.python_path
            pip_path = self.os_config.pip_path
            
            # Test Python version
            result = subprocess.run([python_path, '--version'], 
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=10)
            
            if result.returncode == 0:
                version = result.stdout.strip()
                version_num = version.split()[1]
                major, minor = map(int, version_num.split('.')[:2])
                
                is_compatible = major == 3 and minor >= 6
                
                self.test_results['python_detection'] = {
                    'status': 'PASS' if is_compatible else 'WARN',
                    'python_path': python_path,
                    'pip_path': pip_path,
                    'version': version,
                    'is_compatible': is_compatible
                }
                
                print(f"   ✅ Python: {version}")
                print(f"   ✅ Path: {python_path}")
                print(f"   ✅ Pip: {pip_path}")
                print(f"   {'✅' if is_compatible else '⚠️'} Compatible: {is_compatible}")
                
            else:
                raise Exception("Python not working properly")
                
        except Exception as e:
            self.test_results['python_detection'] = {
                'status': 'FAIL',
                'error': str(e)
            }
            print(f"   ❌ Error: {e}")
    
    def test_package_manager_detection(self):
        """Test package manager detection"""
        print("\n📦 Testing Package Manager Detection...")
        
        try:
            package_manager = self.os_config.package_manager
            config = self.os_config.get_os_specific_config()
            
            # Test if package manager is available
            if package_manager in ['apt-get', 'apt']:
                test_cmd = ['apt', '--version']
            elif package_manager == 'dnf':
                test_cmd = ['dnf', '--version']
            elif package_manager == 'yum':
                test_cmd = ['yum', '--version']
            else:
                test_cmd = None
            
            is_available = True
            if test_cmd:
                try:
                    result = subprocess.run(test_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=5)
                    is_available = result.returncode == 0
                except:
                    is_available = False
            
            self.test_results['package_manager'] = {
                'status': 'PASS' if is_available else 'WARN',
                'package_manager': package_manager,
                'is_available': is_available,
                'config': config
            }
            
            print(f"   ✅ Package Manager: {package_manager}")
            print(f"   {'✅' if is_available else '⚠️'} Available: {is_available}")
            
        except Exception as e:
            self.test_results['package_manager'] = {
                'status': 'FAIL',
                'error': str(e)
            }
            print(f"   ❌ Error: {e}")
    
    def test_service_manager_detection(self):
        """Test service manager detection"""
        print("\n🔧 Testing Service Manager Detection...")
        
        try:
            service_manager = self.os_config.service_manager
            web_server = self.os_config.web_server
            
            # Test if service manager is available
            if service_manager == 'systemctl':
                test_cmd = ['systemctl', '--version']
            elif service_manager == 'service':
                test_cmd = ['service', '--version']
            else:
                test_cmd = None
            
            is_available = True
            if test_cmd:
                try:
                    result = subprocess.run(test_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=5)
                    is_available = result.returncode == 0
                except:
                    is_available = False
            
            self.test_results['service_manager'] = {
                'status': 'PASS' if is_available else 'WARN',
                'service_manager': service_manager,
                'web_server': web_server,
                'is_available': is_available
            }
            
            print(f"   ✅ Service Manager: {service_manager}")
            print(f"   ✅ Web Server: {web_server}")
            print(f"   {'✅' if is_available else '⚠️'} Available: {is_available}")
            
        except Exception as e:
            self.test_results['service_manager'] = {
                'status': 'FAIL',
                'error': str(e)
            }
            print(f"   ❌ Error: {e}")
    
    def test_web_server_detection(self):
        """Test web server detection"""
        print("\n🌐 Testing Web Server Detection...")
        
        try:
            web_server = self.os_config.web_server
            
            # Check if web server is installed
            if web_server == 'apache2':
                config_paths = ['/etc/apache2/apache2.conf', '/etc/apache2/httpd.conf']
            else:  # httpd
                config_paths = ['/etc/httpd/conf/httpd.conf', '/etc/httpd/conf.d']
            
            is_installed = any(os.path.exists(path) for path in config_paths)
            
            self.test_results['web_server'] = {
                'status': 'PASS' if is_installed else 'WARN',
                'web_server': web_server,
                'is_installed': is_installed,
                'config_paths': config_paths
            }
            
            print(f"   ✅ Web Server: {web_server}")
            print(f"   {'✅' if is_installed else '⚠️'} Installed: {is_installed}")
            
        except Exception as e:
            self.test_results['web_server'] = {
                'status': 'FAIL',
                'error': str(e)
            }
            print(f"   ❌ Error: {e}")
    
    def test_file_permissions(self):
        """Test file permissions and ownership"""
        print("\n🔐 Testing File Permissions...")
        
        try:
            # Test if we can create files in plugin directory
            plugin_dir = "/home/cyberpanel/plugins"
            cyberpanel_dir = "/usr/local/CyberCP"
            
            can_create_plugin_dir = True
            can_create_cyberpanel_dir = True
            
            try:
                os.makedirs(plugin_dir, exist_ok=True)
            except PermissionError:
                can_create_plugin_dir = False
            
            try:
                os.makedirs(f"{cyberpanel_dir}/test", exist_ok=True)
                os.rmdir(f"{cyberpanel_dir}/test")
            except PermissionError:
                can_create_cyberpanel_dir = False
            
            self.test_results['file_permissions'] = {
                'status': 'PASS' if can_create_plugin_dir and can_create_cyberpanel_dir else 'WARN',
                'can_create_plugin_dir': can_create_plugin_dir,
                'can_create_cyberpanel_dir': can_create_cyberpanel_dir,
                'plugin_dir': plugin_dir,
                'cyberpanel_dir': cyberpanel_dir
            }
            
            print(f"   {'✅' if can_create_plugin_dir else '⚠️'} Plugin Directory: {plugin_dir}")
            print(f"   {'✅' if can_create_cyberpanel_dir else '⚠️'} CyberPanel Directory: {cyberpanel_dir}")
            
        except Exception as e:
            self.test_results['file_permissions'] = {
                'status': 'FAIL',
                'error': str(e)
            }
            print(f"   ❌ Error: {e}")
    
    def test_network_connectivity(self):
        """Test network connectivity"""
        print("\n🌍 Testing Network Connectivity...")
        
        try:
            # Test GitHub connectivity
            github_result = subprocess.run(['curl', '-s', '--connect-timeout', '10', 
                                         'https://github.com'], 
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=15)
            github_available = github_result.returncode == 0
            
            # Test general internet connectivity
            internet_result = subprocess.run(['curl', '-s', '--connect-timeout', '10', 
                                           'https://www.google.com'], 
                                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=15)
            internet_available = internet_result.returncode == 0
            
            self.test_results['network_connectivity'] = {
                'status': 'PASS' if github_available and internet_available else 'WARN',
                'github_available': github_available,
                'internet_available': internet_available
            }
            
            print(f"   {'✅' if github_available else '⚠️'} GitHub: {github_available}")
            print(f"   {'✅' if internet_available else '⚠️'} Internet: {internet_available}")
            
        except Exception as e:
            self.test_results['network_connectivity'] = {
                'status': 'FAIL',
                'error': str(e)
            }
            print(f"   ❌ Error: {e}")
    
    def test_cyberpanel_integration(self):
        """Test CyberPanel integration"""
        print("\n⚡ Testing CyberPanel Integration...")
        
        try:
            cyberpanel_dir = "/usr/local/CyberCP"
            
            # Check if CyberPanel is installed
            cyberpanel_installed = os.path.exists(cyberpanel_dir)
            
            # Check if Django settings exist
            settings_file = f"{cyberpanel_dir}/cyberpanel/settings.py"
            settings_exist = os.path.exists(settings_file)
            
            # Check if URLs file exists
            urls_file = f"{cyberpanel_dir}/cyberpanel/urls.py"
            urls_exist = os.path.exists(urls_file)
            
            # Check if lscpd service exists
            lscpd_exists = os.path.exists("/usr/local/lscp/bin/lscpd")
            
            self.test_results['cyberpanel_integration'] = {
                'status': 'PASS' if cyberpanel_installed and settings_exist and urls_exist else 'WARN',
                'cyberpanel_installed': cyberpanel_installed,
                'settings_exist': settings_exist,
                'urls_exist': urls_exist,
                'lscpd_exists': lscpd_exists
            }
            
            print(f"   {'✅' if cyberpanel_installed else '⚠️'} CyberPanel Installed: {cyberpanel_installed}")
            print(f"   {'✅' if settings_exist else '⚠️'} Settings File: {settings_exist}")
            print(f"   {'✅' if urls_exist else '⚠️'} URLs File: {urls_exist}")
            print(f"   {'✅' if lscpd_exists else '⚠️'} LSCPD Service: {lscpd_exists}")
            
        except Exception as e:
            self.test_results['cyberpanel_integration'] = {
                'status': 'FAIL',
                'error': str(e)
            }
            print(f"   ❌ Error: {e}")
    
    def display_results(self):
        """Display test results summary"""
        print("\n" + "=" * 60)
        print("📊 COMPATIBILITY TEST RESULTS")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result['status'] == 'PASS')
        warned_tests = sum(1 for result in self.test_results.values() if result['status'] == 'WARN')
        failed_tests = sum(1 for result in self.test_results.values() if result['status'] == 'FAIL')
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"⚠️  Warnings: {warned_tests}")
        print(f"❌ Failed: {failed_tests}")
        
        if failed_tests == 0:
            print("\n🎉 All tests passed! The plugin is compatible with this OS.")
        elif warned_tests > 0 and failed_tests == 0:
            print("\n⚠️  Some warnings detected. The plugin should work but may need attention.")
        else:
            print("\n❌ Some tests failed. The plugin may not work properly on this OS.")
        
        # Show detailed results
        print("\n📋 Detailed Results:")
        for test_name, result in self.test_results.items():
            status_icon = {'PASS': '✅', 'WARN': '⚠️', 'FAIL': '❌'}[result['status']]
            print(f"   {status_icon} {test_name.replace('_', ' ').title()}: {result['status']}")
            if 'error' in result:
                print(f"      Error: {result['error']}")
        
        # Generate compatibility report
        self.generate_compatibility_report()
    
    def generate_compatibility_report(self):
        """Generate a compatibility report file"""
        try:
            report = {
                'timestamp': time.time(),
                'os_info': self.os_config.get_os_info(),
                'test_results': self.test_results,
                'compatibility_score': self.calculate_compatibility_score()
            }
            
            report_file = "compatibility_report.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
            
            print(f"\n📄 Compatibility report saved to: {report_file}")
            
        except Exception as e:
            print(f"\n⚠️  Could not save compatibility report: {e}")
    
    def calculate_compatibility_score(self):
        """Calculate overall compatibility score"""
        total_tests = len(self.test_results)
        if total_tests == 0:
            return 0
        
        score = 0
        for result in self.test_results.values():
            if result['status'] == 'PASS':
                score += 1
            elif result['status'] == 'WARN':
                score += 0.5
        
        return round((score / total_tests) * 100, 1)


def main():
    """Main function"""
    tester = OSCompatibilityTester()
    results = tester.run_all_tests()
    
    # Exit with appropriate code
    failed_tests = sum(1 for result in results.values() if result['status'] == 'FAIL')
    if failed_tests > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
