#!/usr/local/CyberCP/bin/python
import os
import sys
import json
import shutil
import subprocess
import pwd
import grp
from django.db import models
from django.conf import settings
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
from plogical.processUtilities import ProcessUtilities

class HomeDirectoryManager:
    """
    Manages multiple home directories for CyberPanel users
    Supports /home, /home2, /home3, etc. for storage balance
    """
    
    @staticmethod
    def detectHomeDirectories():
        """
        Automatically detect all available home directories
        Returns list of available home directories
        """
        try:
            home_dirs = []
            
            # Check for /home (default)
            if os.path.exists('/home') and os.path.isdir('/home'):
                home_dirs.append({
                    'path': '/home',
                    'name': 'home',
                    'available_space': HomeDirectoryManager.getAvailableSpace('/home'),
                    'total_space': HomeDirectoryManager.getTotalSpace('/home'),
                    'user_count': HomeDirectoryManager.getUserCount('/home')
                })
            
            # Check for /home2, /home3, etc.
            for i in range(2, 10):  # Check up to /home9
                home_path = f'/home{i}'
                if os.path.exists(home_path) and os.path.isdir(home_path):
                    home_dirs.append({
                        'path': home_path,
                        'name': f'home{i}',
                        'available_space': HomeDirectoryManager.getAvailableSpace(home_path),
                        'total_space': HomeDirectoryManager.getTotalSpace(home_path),
                        'user_count': HomeDirectoryManager.getUserCount(home_path)
                    })
            
            return home_dirs
            
        except Exception as e:
            logging.writeToFile(f"Error detecting home directories: {str(e)}")
            return []
    
    @staticmethod
    def getAvailableSpace(path):
        """Get available space in bytes for a given path"""
        try:
            statvfs = os.statvfs(path)
            return statvfs.f_frsize * statvfs.f_bavail
        except:
            return 0
    
    @staticmethod
    def getTotalSpace(path):
        """Get total space in bytes for a given path"""
        try:
            statvfs = os.statvfs(path)
            return statvfs.f_frsize * statvfs.f_blocks
        except:
            return 0
    
    @staticmethod
    def getUserCount(path):
        """Get number of users in a home directory"""
        try:
            count = 0
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                if os.path.isdir(item_path) and not item.startswith('.'):
                    # Check if it's a user directory (has public_html)
                    if os.path.exists(os.path.join(item_path, 'public_html')):
                        count += 1
            return count
        except:
            return 0
    
    @staticmethod
    def getBestHomeDirectory():
        """
        Automatically select the best home directory based on available space
        Returns the path with most available space
        """
        try:
            home_dirs = HomeDirectoryManager.detectHomeDirectories()
            if not home_dirs:
                return '/home'  # Fallback to default
            
            # Sort by available space (descending)
            home_dirs.sort(key=lambda x: x['available_space'], reverse=True)
            return home_dirs[0]['path']
            
        except Exception as e:
            logging.writeToFile(f"Error selecting best home directory: {str(e)}")
            return '/home'
    
    @staticmethod
    def createUserDirectory(username, home_path, owner_uid=5003, owner_gid=5003):
        """
        Create user directory in specified home path
        """
        try:
            user_path = os.path.join(home_path, username)
            
            # Create user directory
            if not os.path.exists(user_path):
                os.makedirs(user_path, mode=0o755)
            
            # Create public_html directory
            public_html_path = os.path.join(user_path, 'public_html')
            if not os.path.exists(public_html_path):
                os.makedirs(public_html_path, mode=0o755)
            
            # Create logs directory
            logs_path = os.path.join(user_path, 'logs')
            if not os.path.exists(logs_path):
                os.makedirs(logs_path, mode=0o755)
            
            # Set ownership
            HomeDirectoryManager.setOwnership(user_path, owner_uid, owner_gid)
            
            return True
            
        except Exception as e:
            logging.writeToFile(f"Error creating user directory: {str(e)}")
            return False
    
    @staticmethod
    def setOwnership(path, uid, gid):
        """Set ownership for a path recursively"""
        try:
            # Set ownership for the directory
            os.chown(path, uid, gid)
            
            # Set ownership for all contents recursively
            for root, dirs, files in os.walk(path):
                for d in dirs:
                    os.chown(os.path.join(root, d), uid, gid)
                for f in files:
                    os.chown(os.path.join(root, f), uid, gid)
            
            return True
            
        except Exception as e:
            logging.writeToFile(f"Error setting ownership: {str(e)}")
            return False
    
    @staticmethod
    def migrateUser(username, from_home, to_home, owner_uid=5003, owner_gid=5003):
        """
        Migrate user from one home directory to another
        """
        try:
            from_path = os.path.join(from_home, username)
            to_path = os.path.join(to_home, username)
            
            if not os.path.exists(from_path):
                return False, f"User directory {from_path} does not exist"
            
            if os.path.exists(to_path):
                return False, f"User directory {to_path} already exists"
            
            # Create target directory structure
            if not HomeDirectoryManager.createUserDirectory(username, to_home, owner_uid, owner_gid):
                return False, "Failed to create target directory"
            
            # Copy all files and directories
            shutil.copytree(from_path, to_path, dirs_exist_ok=True)
            
            # Set proper ownership
            HomeDirectoryManager.setOwnership(to_path, owner_uid, owner_gid)
            
            # Remove old directory
            shutil.rmtree(from_path)
            
            return True, "User migrated successfully"
            
        except Exception as e:
            logging.writeToFile(f"Error migrating user: {str(e)}")
            return False, str(e)
    
    @staticmethod
    def getHomeDirectoryStats():
        """
        Get comprehensive statistics for all home directories
        """
        try:
            home_dirs = HomeDirectoryManager.detectHomeDirectories()
            stats = {
                'total_directories': len(home_dirs),
                'total_users': sum(d['user_count'] for d in home_dirs),
                'total_space': sum(d['total_space'] for d in home_dirs),
                'total_available': sum(d['available_space'] for d in home_dirs),
                'directories': home_dirs
            }
            
            # Calculate usage percentages
            for directory in stats['directories']:
                if directory['total_space'] > 0:
                    used_space = directory['total_space'] - directory['available_space']
                    directory['usage_percentage'] = (used_space / directory['total_space']) * 100
                else:
                    directory['usage_percentage'] = 0
            
            return stats
            
        except Exception as e:
            logging.writeToFile(f"Error getting home directory stats: {str(e)}")
            return None
    
    @staticmethod
    def formatBytes(bytes_value):
        """Convert bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} PB"
