#!/usr/bin/env python3

import requests
import json
import re
import logging
from typing import Optional, Tuple

class VersionFetcher:
    """
    Utility class to fetch latest versions of components from GitHub API
    """
    
    # GitHub API endpoints for different components
    GITHUB_API_BASE = "https://api.github.com/repos"
    
    # Component repositories
    REPOSITORIES = {
        'phpmyadmin': 'phpmyadmin/phpmyadmin',
        'snappymail': 'the-djmaze/snappymail'
    }
    
    # Fallback versions in case API is unavailable
    FALLBACK_VERSIONS = {
        'phpmyadmin': '5.2.2',
        'snappymail': '2.38.2'
    }
    
    @staticmethod
    def get_latest_version(component: str) -> str:
        """
        Get the latest version of a component from GitHub
        
        Args:
            component (str): Component name ('phpmyadmin' or 'snappymail')
            
        Returns:
            str: Latest version number or fallback version
        """
        try:
            if component not in VersionFetcher.REPOSITORIES:
                logging.warning(f"Unknown component: {component}")
                return VersionFetcher.FALLBACK_VERSIONS.get(component, "unknown")
            
            repo = VersionFetcher.REPOSITORIES[component]
            url = f"{VersionFetcher.GITHUB_API_BASE}/{repo}/releases/latest"
            
            logging.info(f"Fetching latest version for {component} from {url}")
            
            # Make request with timeout and proper headers
            headers = {
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'CyberPanel-VersionFetcher/1.0'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            version = data.get('tag_name', '')
            
            # Clean version string (remove 'v' prefix if present)
            version = re.sub(r'^v', '', version)
            
            if version and VersionFetcher._is_valid_version(version):
                logging.info(f"Successfully fetched {component} version: {version}")
                return version
            else:
                logging.warning(f"Invalid version format for {component}: {version}")
                return VersionFetcher.FALLBACK_VERSIONS[component]
                
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to fetch {component} version: {e}")
            return VersionFetcher.FALLBACK_VERSIONS[component]
        except Exception as e:
            logging.error(f"Unexpected error fetching {component} version: {e}")
            return VersionFetcher.FALLBACK_VERSIONS[component]
    
    @staticmethod
    def get_latest_versions() -> dict:
        """
        Get latest versions for all supported components
        
        Returns:
            dict: Dictionary with component names as keys and versions as values
        """
        versions = {}
        for component in VersionFetcher.REPOSITORIES.keys():
            versions[component] = VersionFetcher.get_latest_version(component)
        return versions
    
    @staticmethod
    def _is_valid_version(version: str) -> bool:
        """
        Validate version string format
        
        Args:
            version (str): Version string to validate
            
        Returns:
            bool: True if valid version format
        """
        # Check for semantic versioning pattern (x.y.z)
        pattern = r'^\d+\.\d+\.\d+$'
        return bool(re.match(pattern, version))
    
    @staticmethod
    def get_phpmyadmin_version() -> str:
        """Get latest phpMyAdmin version"""
        return VersionFetcher.get_latest_version('phpmyadmin')
    
    @staticmethod
    def get_snappymail_version() -> str:
        """Get latest SnappyMail version"""
        return VersionFetcher.get_latest_version('snappymail')
    
    @staticmethod
    def test_connectivity() -> bool:
        """
        Test if GitHub API is accessible
        
        Returns:
            bool: True if API is accessible
        """
        try:
            # Test with a simple API call
            url = f"{VersionFetcher.GITHUB_API_BASE}/octocat/Hello-World"
            headers = {
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'CyberPanel-VersionFetcher/1.0'
            }
            
            response = requests.get(url, headers=headers, timeout=5)
            return response.status_code == 200
        except:
            return False

# Convenience functions for backward compatibility
def get_latest_phpmyadmin_version():
    """Get latest phpMyAdmin version"""
    return VersionFetcher.get_phpmyadmin_version()

def get_latest_snappymail_version():
    """Get latest SnappyMail version"""
    return VersionFetcher.get_snappymail_version()

def get_latest_versions():
    """Get latest versions for all components"""
    return VersionFetcher.get_latest_versions()

if __name__ == "__main__":
    # Test the version fetcher
    print("Testing version fetcher...")
    print(f"GitHub API accessible: {VersionFetcher.test_connectivity()}")
    print(f"Latest phpMyAdmin: {get_latest_phpmyadmin_version()}")
    print(f"Latest SnappyMail: {get_latest_snappymail_version()}")
    print(f"All versions: {get_latest_versions()}")
