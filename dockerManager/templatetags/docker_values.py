from django import template
from django.utils.html import escapejs
from django.utils.safestring import mark_safe

register = template.Library()

## The panel's pages are AngularJS pages that use {$ $} for their own expressions.
_ANGULAR_SYMBOLS = {ord('{'): '\\u007B', ord('}'): '\\u007D', ord('$'): '\\u0024'}


@register.filter(is_safe=True)
def ngstring(value):
    """
    Text for the inside of a quoted string in an AngularJS expression.

    A value that comes from a Docker image or from the address of the page is
    written into ng-init="name='...'" and the like. HTML escaping alone does not
    keep it inside the quotes, because the browser turns the escaped quote back
    into a quote before AngularJS reads the attribute. Every character that
    could end the string or start an expression is written as a \\uXXXX escape,
    which AngularJS reads back as the same character.
    """
    return mark_safe(escapejs(str(value)).translate(_ANGULAR_SYMBOLS))
