"""A managed server and the controllers that may manage it: ending a link.
"""
import re
import time

from multiServer import audit, keys, models

_LINK = re.compile(r'[0-9a-f]{32}')


def end(link_id, actor, raise_counter):
    """End the link of one controller on this managed server, for good.

    True when it was ended now, None when it had been ended before, False when
    there is no such link. Run as root (msctl.py), because one step is root's
    alone: `raise_counter` raises the revocation counter in the key directory
    and returns its new value.

    What is done, in this order: the revocation marker of the link is written
    (it alone stops the link from then on, and it outlasts a restored
    database); the panel sessions and login tickets that came through the link
    are removed; the row becomes REVOKED; the counter is raised; every other
    link that counted until now is moved on to the new value. The ended link
    keeps the old value, so nothing brings it back. One audit row is written.

    The rows of all links are locked while this runs. A request of another
    controller that arrives in that moment is refused once and passes when it
    is sent again, and a panel session that another controller had opened
    here ends and has to be opened again.
    """
    if type(link_id) is not str or _LINK.fullmatch(link_id) is None:
        raise ValueError('This is not a link.')
    from django.db import transaction
    from multiServer import sso
    live = (models.PENDING, models.ACTIVE, models.PAUSED)
    with transaction.atomic():
        found = dict((row.link_id, row) for row in models.Link.objects.select_for_update().order_by('link_id'))
        link = found.get(link_id)
        if link is None:
            return False
        if link.status not in live:
            # Closed before: rejected, never approved in time, or ended. The marker is there or is made up for.
            keys.mark_revoked(link_id)
            return None
        counter = keys.generation()
        if counter < 1:
            raise RuntimeError('The revocation counter cannot be read.')
        keys.mark_revoked(link_id)
        sso.clear(link)
        models.Link.objects.filter(pk=link_id).update(status=models.REVOKED, updated_at=int(time.time()))
        raised = raise_counter()
        if type(raised) is not int or raised != counter + 1:
            raise RuntimeError('The revocation counter was not raised by one.')
        models.Link.objects.exclude(pk=link_id).filter(generation=counter, status__in=live).update(generation=raised)
    audit.record('link_revoke', link_id=link_id, **(dict(actor=actor) if actor else {}))
    return True
