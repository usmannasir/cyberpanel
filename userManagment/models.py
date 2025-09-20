from django.db import models
from loginSystem.models import Administrator

class HomeDirectory(models.Model):
    """
    Model to store home directory configurations
    """
    name = models.CharField(max_length=50, unique=True, help_text="Directory name (e.g., home, home2)")
    path = models.CharField(max_length=255, unique=True, help_text="Full path to home directory")
    is_active = models.BooleanField(default=True, help_text="Whether this home directory is active")
    is_default = models.BooleanField(default=False, help_text="Whether this is the default home directory")
    max_users = models.IntegerField(default=0, help_text="Maximum number of users (0 = unlimited)")
    description = models.TextField(blank=True, help_text="Description of this home directory")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'home_directories'
        verbose_name = 'Home Directory'
        verbose_name_plural = 'Home Directories'
    
    def __str__(self):
        return f"{self.name} ({self.path})"
    
    def get_available_space(self):
        """Get available space in bytes"""
        try:
            import os
            statvfs = os.statvfs(self.path)
            return statvfs.f_frsize * statvfs.f_bavail
        except:
            return 0
    
    def get_total_space(self):
        """Get total space in bytes"""
        try:
            import os
            statvfs = os.statvfs(self.path)
            return statvfs.f_frsize * statvfs.f_blocks
        except:
            return 0
    
    def get_user_count(self):
        """Get number of users in this home directory"""
        try:
            import os
            count = 0
            if os.path.exists(self.path):
                for item in os.listdir(self.path):
                    item_path = os.path.join(self.path, item)
                    if os.path.isdir(item_path) and not item.startswith('.'):
                        # Check if it's a user directory (has public_html)
                        if os.path.exists(os.path.join(item_path, 'public_html')):
                            count += 1
            return count
        except:
            return 0
    
    def get_usage_percentage(self):
        """Get usage percentage"""
        try:
            total = self.get_total_space()
            if total > 0:
                used = total - self.get_available_space()
                return (used / total) * 100
            return 0
        except:
            return 0

class UserHomeMapping(models.Model):
    """
    Model to map users to their home directories
    """
    user = models.OneToOneField(Administrator, on_delete=models.CASCADE, related_name='home_mapping')
    home_directory = models.ForeignKey(HomeDirectory, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_home_mappings'
        verbose_name = 'User Home Mapping'
        verbose_name_plural = 'User Home Mappings'
    
    def __str__(self):
        return f"{self.user.userName} -> {self.home_directory.name}"