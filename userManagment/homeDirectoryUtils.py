#!/usr/local/CyberCP/bin/python
import os
import sys
from django.db import models
from loginSystem.models import Administrator
from .models import HomeDirectory, UserHomeMapping
from .homeDirectoryManager import HomeDirectoryManager

class HomeDirectoryUtils:
    """
    Utility functions for getting user home directories
    """
    
    @staticmethod
    def getUserHomeDirectory(username):
        """
        Get the home directory path for a specific user
        Returns the home directory path or None if not found
        """
        try:
            user = Administrator.objects.get(userName=username)
            try:
                mapping = UserHomeMapping.objects.get(user=user)
                return mapping.home_directory.path
            except UserHomeMapping.DoesNotExist:
                # Fallback to default home directory
                default_home = HomeDirectory.objects.filter(is_default=True).first()
                if default_home:
                    return default_home.path
                else:
                    return HomeDirectoryManager.getBestHomeDirectory()
        except Administrator.DoesNotExist:
            return None
    
    @staticmethod
    def getUserHomeDirectoryObject(username):
        """
        Get the home directory object for a specific user
        Returns the HomeDirectory object or None if not found
        """
        try:
            user = Administrator.objects.get(userName=username)
            try:
                mapping = UserHomeMapping.objects.get(user=user)
                return mapping.home_directory
            except UserHomeMapping.DoesNotExist:
                # Fallback to default home directory
                return HomeDirectory.objects.filter(is_default=True).first()
        except Administrator.DoesNotExist:
            return None
    
    @staticmethod
    def getWebsitePath(domain, username=None):
        """
        Get the website path for a domain, using the user's home directory
        """
        if username:
            home_path = HomeDirectoryUtils.getUserHomeDirectory(username)
        else:
            home_path = HomeDirectoryManager.getBestHomeDirectory()
        
        if not home_path:
            home_path = '/home'  # Fallback
        
        return os.path.join(home_path, domain)
    
    @staticmethod
    def getPublicHtmlPath(domain, username=None):
        """
        Get the public_html path for a domain
        """
        website_path = HomeDirectoryUtils.getWebsitePath(domain, username)
        return os.path.join(website_path, 'public_html')
    
    @staticmethod
    def getLogsPath(domain, username=None):
        """
        Get the logs path for a domain
        """
        website_path = HomeDirectoryUtils.getWebsitePath(domain, username)
        return os.path.join(website_path, 'logs')
    
    @staticmethod
    def updateUserHomeDirectory(username, new_home_directory_id):
        """
        Update a user's home directory
        """
        try:
            user = Administrator.objects.get(userName=username)
            home_dir = HomeDirectory.objects.get(id=new_home_directory_id)
            
            # Update or create mapping
            mapping, created = UserHomeMapping.objects.get_or_create(
                user=user,
                defaults={'home_directory': home_dir}
            )
            
            if not created:
                mapping.home_directory = home_dir
                mapping.save()
            
            return True, "Home directory updated successfully"
            
        except Administrator.DoesNotExist:
            return False, "User not found"
        except HomeDirectory.DoesNotExist:
            return False, "Home directory not found"
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def getAllUsersInHomeDirectory(home_directory_id):
        """
        Get all users assigned to a specific home directory
        """
        try:
            home_dir = HomeDirectory.objects.get(id=home_directory_id)
            mappings = UserHomeMapping.objects.filter(home_directory=home_dir)
            return [mapping.user for mapping in mappings]
        except HomeDirectory.DoesNotExist:
            return []
    
    @staticmethod
    def getHomeDirectoryUsageStats():
        """
        Get usage statistics for all home directories
        """
        home_dirs = HomeDirectory.objects.filter(is_active=True)
        stats = []
        
        for home_dir in home_dirs:
            user_count = UserHomeMapping.objects.filter(home_directory=home_dir).count()
            available_space = home_dir.get_available_space()
            total_space = home_dir.get_total_space()
            usage_percentage = home_dir.get_usage_percentage()
            
            stats.append({
                'id': home_dir.id,
                'name': home_dir.name,
                'path': home_dir.path,
                'user_count': user_count,
                'available_space': available_space,
                'total_space': total_space,
                'usage_percentage': usage_percentage,
                'is_default': home_dir.is_default
            })
        
        return stats
