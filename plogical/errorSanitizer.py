# -*- coding: utf-8 -*-

"""
CyberPanel Error Sanitization Utility
=====================================

This module provides secure error handling and sanitization to prevent
information disclosure vulnerabilities while maintaining useful error
reporting for debugging purposes.

Security Features:
- Sanitizes error messages to prevent information disclosure
- Provides user-friendly error messages
- Maintains detailed logging for administrators
- Prevents sensitive data exposure in API responses
"""

import re
import logging
import traceback
from typing import Optional, Dict, Any
from django.conf import settings
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging

class ErrorSanitizer:
    """
    Centralized error sanitization and handling utility
    """
    
    # Sensitive patterns that should be masked in error messages
    SENSITIVE_PATTERNS = [
        # File paths
        r'/home/[^/]+/',
        r'/usr/local/[^/]+/',
        r'/var/[^/]+/',
        r'/etc/[^/]+/',
        # Database credentials
        r'password[=\s]*[^\s]+',
        r'passwd[=\s]*[^\s]+',
        r'pwd[=\s]*[^\s]+',
        # API keys and tokens
        r'api[_-]?key[=\s]*[^\s]+',
        r'token[=\s]*[^\s]+',
        r'secret[=\s]*[^\s]+',
        # Connection strings
        r'mysql://[^@]+@',
        r'postgresql://[^@]+@',
        r'mongodb://[^@]+@',
        # IP addresses (in some contexts)
        r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
        # Email addresses
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    ]
    
    # Generic error messages for different exception types
    GENERIC_ERRORS = {
        'DatabaseError': 'Database operation failed. Please try again.',
        'ConnectionError': 'Unable to connect to the service. Please check your connection.',
        'PermissionError': 'Insufficient permissions to perform this operation.',
        'FileNotFoundError': 'Required file not found. Please contact support.',
        'OSError': 'System operation failed. Please try again.',
        'ValueError': 'Invalid input provided. Please check your data.',
        'KeyError': 'Required information is missing. Please try again.',
        'TypeError': 'Invalid data type provided. Please check your input.',
        'AttributeError': 'System configuration error. Please contact support.',
        'ImportError': 'System module error. Please contact support.',
        'TimeoutError': 'Operation timed out. Please try again.',
        'BaseException': 'An unexpected error occurred. Please try again.',
    }
    
    @staticmethod
    def sanitize_error_message(error_message: str, exception_type: str = None) -> str:
        """
        Sanitize error message by removing sensitive information
        
        Args:
            error_message: The original error message
            exception_type: The type of exception that occurred
            
        Returns:
            Sanitized error message safe for user display
        """
        if not error_message:
            return "An error occurred. Please try again."
        
        # Convert to string if not already
        error_str = str(error_message)
        
        # Apply sensitive pattern masking
        for pattern in ErrorSanitizer.SENSITIVE_PATTERNS:
            error_str = re.sub(pattern, '[REDACTED]', error_str, flags=re.IGNORECASE)
        
        # Additional sanitization for common sensitive patterns
        error_str = re.sub(r'[^\x00-\x7F]+', '[NON-ASCII]', error_str)  # Remove non-ASCII chars
        error_str = re.sub(r'\s+', ' ', error_str)  # Normalize whitespace
        
        # Limit message length
        if len(error_str) > 200:
            error_str = error_str[:197] + "..."
        
        return error_str.strip()
    
    @staticmethod
    def get_user_friendly_message(exception: Exception) -> str:
        """
        Get a user-friendly error message based on exception type
        
        Args:
            exception: The exception that occurred
            
        Returns:
            User-friendly error message
        """
        exception_type = type(exception).__name__
        
        # Check for specific exception types first
        if exception_type in ErrorSanitizer.GENERIC_ERRORS:
            return ErrorSanitizer.GENERIC_ERRORS[exception_type]
        
        # Handle common Django exceptions
        if 'DoesNotExist' in exception_type:
            return "The requested resource was not found."
        elif 'ValidationError' in exception_type:
            return "Invalid data provided. Please check your input."
        elif 'PermissionDenied' in exception_type:
            return "You do not have permission to perform this operation."
        
        # Default generic message
        return "An unexpected error occurred. Please try again."
    
    @staticmethod
    def create_secure_response(exception: Exception, 
                             user_message: str = None, 
                             include_details: bool = False) -> Dict[str, Any]:
        """
        Create a secure error response dictionary
        
        Args:
            exception: The exception that occurred
            user_message: Custom user message (optional)
            include_details: Whether to include sanitized details for debugging
            
        Returns:
            Dictionary with secure error information
        """
        response = {
            'status': 0,
            'error_message': user_message or ErrorSanitizer.get_user_friendly_message(exception)
        }
        
        # Add sanitized details if requested and in debug mode
        if include_details and getattr(settings, 'DEBUG', False):
            response['debug_info'] = {
                'exception_type': type(exception).__name__,
                'sanitized_message': ErrorSanitizer.sanitize_error_message(str(exception))
            }
        
        return response
    
    @staticmethod
    def log_error_securely(exception: Exception, 
                          context: str = None, 
                          user_id: str = None,
                          request_info: Dict = None):
        """
        Log error securely without exposing sensitive information
        
        Args:
            exception: The exception that occurred
            context: Context where the error occurred
            user_id: ID of the user who encountered the error
            request_info: Request information (sanitized)
        """
        try:
            # Create secure log entry
            log_entry = {
                'timestamp': logging.get_current_timestamp(),
                'exception_type': type(exception).__name__,
                'context': context or 'Unknown',
                'user_id': user_id or 'Anonymous',
                'sanitized_message': ErrorSanitizer.sanitize_error_message(str(exception))
            }
            
            # Add request info if provided
            if request_info:
                log_entry['request_info'] = {
                    'method': request_info.get('method', 'Unknown'),
                    'path': request_info.get('path', 'Unknown'),
                    'ip': request_info.get('ip', 'Unknown')
                }
            
            # Log the error
            logging.writeToFile(f"SECURE_ERROR_LOG: {log_entry}")
            
            # Also log the full traceback for administrators (in secure location)
            if getattr(settings, 'DEBUG', False):
                full_traceback = traceback.format_exc()
                sanitized_traceback = ErrorSanitizer.sanitize_error_message(full_traceback)
                logging.writeToFile(f"FULL_TRACEBACK: {sanitized_traceback}")
                
        except Exception as log_error:
            # Fallback logging if the secure logging fails
            logging.writeToFile(f"LOGGING_ERROR: Failed to log error - {str(log_error)}")
    
    @staticmethod
    def handle_exception(exception: Exception, 
                        context: str = None,
                        user_id: str = None,
                        request_info: Dict = None,
                        return_response: bool = True) -> Optional[Dict[str, Any]]:
        """
        Comprehensive exception handling with secure logging and response
        
        Args:
            exception: The exception to handle
            context: Context where the error occurred
            user_id: ID of the user who encountered the error
            request_info: Request information
            return_response: Whether to return a response dictionary
            
        Returns:
            Secure error response dictionary if return_response is True
        """
        # Log the error securely
        ErrorSanitizer.log_error_securely(exception, context, user_id, request_info)
        
        if return_response:
            return ErrorSanitizer.create_secure_response(exception)
        
        return None


class SecureExceptionHandler:
    """
    Context manager for secure exception handling
    """
    
    def __init__(self, context: str = None, user_id: str = None, request_info: Dict = None):
        self.context = context
        self.user_id = user_id
        self.request_info = request_info
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            ErrorSanitizer.handle_exception(
                exc_val, 
                self.context, 
                self.user_id, 
                self.request_info, 
                return_response=False
            )
            # Return True to suppress the exception (we've handled it)
            return True
        return False


# Convenience functions for common use cases
def secure_error_response(exception: Exception, user_message: str = None) -> Dict[str, Any]:
    """Create a secure error response for API endpoints"""
    return ErrorSanitizer.create_secure_response(exception, user_message)


def secure_log_error(exception: Exception, context: str = None, user_id: str = None):
    """Log an error securely without exposing sensitive information"""
    ErrorSanitizer.log_error_securely(exception, context, user_id)


def handle_secure_exception(exception: Exception, context: str = None) -> Dict[str, Any]:
    """Handle an exception securely and return a safe response"""
    return ErrorSanitizer.handle_exception(exception, context, return_response=True)
