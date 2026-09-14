"""Paid access applies to root mode; ordinary site file operations stay free."""
from functools import wraps

from plogical.acl import ACLManager


def require_root_entitlement(data):
    # A failed site operation must not silently become a root operation.
    if data.get('domainName'):
        raise PermissionError('Root operations require the root file manager.')
    try:
        status = ACLManager.CheckForPremFeature('Filemanager')
        available = type(status) is int and status == 1
    except Exception:
        available = False
    if not available:
        raise PermissionError('An active Root File Manager entitlement is required.')


def root_entitlement_required(operation):
    @wraps(operation)
    def checked(self, *args, **kwargs):
        if not self.data.get('domainName'):
            try:
                require_root_entitlement(self.data)
            except PermissionError as error:
                return self.ajaxPre(0, str(error))
        return operation(self, *args, **kwargs)
    return checked
