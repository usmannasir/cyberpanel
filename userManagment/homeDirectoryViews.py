#!/usr/local/CyberCP/bin/python
import json
import os
import sys
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from loginSystem.views import loadLoginPage
from loginSystem.models import Administrator
from plogical.acl import ACLManager
from plogical.httpProc import httpProc
from .homeDirectoryManager import HomeDirectoryManager
from .models import HomeDirectory, UserHomeMapping
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging

def loadHomeDirectoryManagement(request):
    """Load home directory management interface"""
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)
        
        if currentACL['admin'] != 1:
            return ACLManager.loadError()
        
        # Get all home directories
        home_directories = HomeDirectory.objects.all().order_by('name')
        
        # Get statistics
        stats = HomeDirectoryManager.getHomeDirectoryStats()
        
        proc = httpProc(request, 'userManagment/homeDirectoryManagement.html', {
            'home_directories': home_directories,
            'stats': stats
        }, 'admin')
        return proc.render()
        
    except Exception as e:
        logging.CyberCPLogFileWriter.writeToFile(f"Error loading home directory management: {str(e)}")
        return ACLManager.loadError()

def detectHomeDirectories(request):
    """Detect and add new home directories"""
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)
        
        if currentACL['admin'] != 1:
            return JsonResponse({'status': 0, 'error_message': 'Unauthorized access'})
        
        # Detect home directories
        detected_dirs = HomeDirectoryManager.detectHomeDirectories()
        added_count = 0
        
        for dir_info in detected_dirs:
            # Check if directory already exists in database
            if not HomeDirectory.objects.filter(path=dir_info['path']).exists():
                # Create new home directory entry
                home_dir = HomeDirectory(
                    name=dir_info['name'],
                    path=dir_info['path'],
                    is_active=True,
                    is_default=(dir_info['path'] == '/home')
                )
                home_dir.save()
                added_count += 1
        
        return JsonResponse({
            'status': 1,
            'message': f'Detected and added {added_count} new home directories',
            'added_count': added_count
        })
        
    except Exception as e:
        logging.CyberCPLogFileWriter.writeToFile(f"Error detecting home directories: {str(e)}")
        return JsonResponse({'status': 0, 'error_message': str(e)})

def updateHomeDirectory(request):
    """Update home directory settings"""
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)
        
        if currentACL['admin'] != 1:
            return JsonResponse({'status': 0, 'error_message': 'Unauthorized access'})
        
        data = json.loads(request.body)
        home_dir_id = data.get('id')
        is_active = data.get('is_active', True)
        is_default = data.get('is_default', False)
        max_users = data.get('max_users', 0)
        description = data.get('description', '')
        
        try:
            home_dir = HomeDirectory.objects.get(id=home_dir_id)
            
            # If setting as default, unset other defaults
            if is_default:
                HomeDirectory.objects.filter(is_default=True).update(is_default=False)
            
            home_dir.is_active = is_active
            home_dir.is_default = is_default
            home_dir.max_users = max_users
            home_dir.description = description
            home_dir.save()
            
            return JsonResponse({'status': 1, 'message': 'Home directory updated successfully'})
            
        except HomeDirectory.DoesNotExist:
            return JsonResponse({'status': 0, 'error_message': 'Home directory not found'})
        
    except Exception as e:
        logging.CyberCPLogFileWriter.writeToFile(f"Error updating home directory: {str(e)}")
        return JsonResponse({'status': 0, 'error_message': str(e)})

def deleteHomeDirectory(request):
    """Delete home directory (only if no users assigned)"""
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)
        
        if currentACL['admin'] != 1:
            return JsonResponse({'status': 0, 'error_message': 'Unauthorized access'})
        
        data = json.loads(request.body)
        home_dir_id = data.get('id')
        
        try:
            home_dir = HomeDirectory.objects.get(id=home_dir_id)
            
            # Check if any users are assigned to this home directory
            user_count = UserHomeMapping.objects.filter(home_directory=home_dir).count()
            if user_count > 0:
                return JsonResponse({
                    'status': 0, 
                    'error_message': f'Cannot delete home directory. {user_count} users are assigned to it.'
                })
            
            # Don't allow deletion of /home (default)
            if home_dir.path == '/home':
                return JsonResponse({
                    'status': 0, 
                    'error_message': 'Cannot delete the default /home directory'
                })
            
            home_dir.delete()
            return JsonResponse({'status': 1, 'message': 'Home directory deleted successfully'})
            
        except HomeDirectory.DoesNotExist:
            return JsonResponse({'status': 0, 'error_message': 'Home directory not found'})
        
    except Exception as e:
        logging.CyberCPLogFileWriter.writeToFile(f"Error deleting home directory: {str(e)}")
        return JsonResponse({'status': 0, 'error_message': str(e)})

def getHomeDirectoryStats(request):
    """Get home directory statistics"""
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)
        
        if currentACL['admin'] != 1:
            return JsonResponse({'status': 0, 'error_message': 'Unauthorized access'})
        
        stats = HomeDirectoryManager.getHomeDirectoryStats()
        return JsonResponse({'status': 1, 'stats': stats})
        
    except Exception as e:
        logging.CyberCPLogFileWriter.writeToFile(f"Error getting home directory stats: {str(e)}")
        return JsonResponse({'status': 0, 'error_message': str(e)})

def getUserHomeDirectories(request):
    """Get available home directories for user creation"""
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)
        
        if currentACL['admin'] != 1 and currentACL['createNewUser'] != 1:
            return JsonResponse({'status': 0, 'error_message': 'Unauthorized access'})
        
        # Get active home directories
        home_dirs = HomeDirectory.objects.filter(is_active=True).order_by('name')
        
        directories = []
        for home_dir in home_dirs:
            directories.append({
                'id': home_dir.id,
                'name': home_dir.name,
                'path': home_dir.path,
                'available_space': home_dir.get_available_space(),
                'user_count': home_dir.get_user_count(),
                'is_default': home_dir.is_default,
                'description': home_dir.description
            })
        
        return JsonResponse({'status': 1, 'directories': directories})
        
    except Exception as e:
        logging.CyberCPLogFileWriter.writeToFile(f"Error getting user home directories: {str(e)}")
        return JsonResponse({'status': 0, 'error_message': str(e)})

def migrateUser(request):
    """Migrate user to different home directory"""
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)
        
        if currentACL['admin'] != 1:
            return JsonResponse({'status': 0, 'error_message': 'Unauthorized access'})
        
        data = json.loads(request.body)
        username = data.get('username')
        target_home_id = data.get('target_home_id')
        
        try:
            user = Administrator.objects.get(userName=username)
            target_home = HomeDirectory.objects.get(id=target_home_id)
            
            # Get current home directory
            try:
                current_mapping = UserHomeMapping.objects.get(user=user)
                current_home = current_mapping.home_directory
            except UserHomeMapping.DoesNotExist:
                current_home = HomeDirectory.objects.filter(is_default=True).first()
                if not current_home:
                    current_home = HomeDirectory.objects.first()
            
            if not current_home:
                return JsonResponse({'status': 0, 'error_message': 'No home directory found for user'})
            
            # Perform migration
            success, message = HomeDirectoryManager.migrateUser(
                username, 
                current_home.path, 
                target_home.path
            )
            
            if success:
                # Update user mapping
                UserHomeMapping.objects.update_or_create(
                    user=user,
                    defaults={'home_directory': target_home}
                )
                return JsonResponse({'status': 1, 'message': message})
            else:
                return JsonResponse({'status': 0, 'error_message': message})
            
        except Administrator.DoesNotExist:
            return JsonResponse({'status': 0, 'error_message': 'User not found'})
        except HomeDirectory.DoesNotExist:
            return JsonResponse({'status': 0, 'error_message': 'Target home directory not found'})
        
    except Exception as e:
        logging.CyberCPLogFileWriter.writeToFile(f"Error migrating user: {str(e)}")
        return JsonResponse({'status': 0, 'error_message': str(e)})
