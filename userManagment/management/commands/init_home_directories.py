#!/usr/local/CyberCP/bin/python
from django.core.management.base import BaseCommand
from userManagment.homeDirectoryManager import HomeDirectoryManager
from userManagment.models import HomeDirectory
import os

class Command(BaseCommand):
    help = 'Initialize home directories for CyberPanel'

    def handle(self, *args, **options):
        self.stdout.write('Initializing home directories...')
        
        # Detect home directories
        detected_dirs = HomeDirectoryManager.detectHomeDirectories()
        
        if not detected_dirs:
            self.stdout.write(self.style.WARNING('No home directories detected'))
            return
        
        # Create default /home if it doesn't exist
        if not os.path.exists('/home'):
            self.stdout.write('Creating default /home directory...')
            os.makedirs('/home', mode=0o755)
            detected_dirs.insert(0, {
                'path': '/home',
                'name': 'home',
                'available_space': HomeDirectoryManager.getAvailableSpace('/home'),
                'total_space': HomeDirectoryManager.getTotalSpace('/home'),
                'user_count': 0
            })
        
        # Create database entries
        created_count = 0
        for dir_info in detected_dirs:
            if not HomeDirectory.objects.filter(path=dir_info['path']).exists():
                home_dir = HomeDirectory(
                    name=dir_info['name'],
                    path=dir_info['path'],
                    is_active=True,
                    is_default=(dir_info['path'] == '/home'),
                    description=f"Auto-detected home directory: {dir_info['path']}"
                )
                home_dir.save()
                created_count += 1
                self.stdout.write(f'Created home directory: {dir_info["name"]} ({dir_info["path"]})')
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully initialized {created_count} home directories')
        )
