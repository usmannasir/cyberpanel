"""Tell a request made by this panel's own page from one another site caused.

Some list pages delete an item when its id arrives in the address. A browser
will load such an address for any site that asks it to, so the id is honoured
only when the browser reports that the panel's own page made the request.
"""
from urllib.parse import urlsplit


def sent_by_this_panel(request):
    site = request.META.get('HTTP_SEC_FETCH_SITE')
    if site is not None:
        return site == 'same-origin'
    # A browser without Fetch Metadata: the referring page must be this panel.
    try:
        host = request.get_host()
        return bool(host) and urlsplit(request.META.get('HTTP_REFERER') or '').netloc == host
    except Exception:
        return False


def confirmed_parameter(request, name):
    """The query parameter, or None unless this panel's own page asked for it."""
    value = request.GET.get(name)
    if value is None or not sent_by_this_panel(request):
        return None
    return value
