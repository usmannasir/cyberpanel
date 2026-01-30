"""
Custom Django template filters for user management
"""
from django import template
from django.template.defaultfilters import filesizeformat

register = template.Library()


@register.filter(name='filesize')
def filesize_filter(value):
    """
    Alias for Django's filesizeformat filter to maintain compatibility
    with templates that use |filesize instead of |filesizeformat
    """
    if value is None:
        return '0 B'
    try:
        return filesizeformat(value)
    except (ValueError, TypeError):
        return '0 B'
