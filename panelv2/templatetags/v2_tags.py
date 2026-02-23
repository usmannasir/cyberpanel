from django import template
from plogical.acl import ACLManager

register = template.Library()


@register.simple_tag
def has_permission(acl, permission):
    """Check if user has a specific permission.
    Usage: {% has_permission acl 'createDatabase' as can_create_db %}
    """
    if acl.get('admin'):
        return True
    return bool(acl.get(permission))


@register.filter
def ssl_badge(ssl_value):
    """Return badge class based on SSL status."""
    if ssl_value == 1:
        return 'badge-success'
    return 'badge-warning'


@register.filter
def site_state(state_value):
    """Return human-readable site state."""
    if state_value == 1:
        return 'Active'
    return 'Suspended'


@register.filter
def site_state_class(state_value):
    """Return CSS class for site state."""
    if state_value == 1:
        return 'text-success'
    return 'text-danger'
