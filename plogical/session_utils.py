"""Invalidate Django panel sessions for a user (e.g. after username rename)."""
import logging

logger = logging.getLogger(__name__)


def invalidate_all_sessions_for_user(user_pk, except_session_key=None):
    """Delete every stored session whose data contains userID == user_pk."""
    removed = 0
    try:
        from django.contrib.sessions.models import Session
    except Exception as exc:
        logger.warning('Session model unavailable: %s', exc)
        return 0
    try:
        user_pk = int(user_pk)
    except (TypeError, ValueError):
        return 0
    for session in Session.objects.all().only('session_key', 'session_data', 'expire_date'):
        if except_session_key and session.session_key == except_session_key:
            continue
        try:
            data = session.get_decoded()
        except Exception:
            continue
        try:
            sid = data.get('userID')
            if sid is None:
                continue
            if int(sid) == user_pk:
                session.delete()
                removed += 1
        except (TypeError, ValueError):
            continue
    return removed


def flush_request_session(request):
    """Clear the current browser session (logout without rendering)."""
    if request is None or not hasattr(request, 'session'):
        return
    try:
        request.session.flush()
    except Exception as exc:
        logger.warning('flush_request_session failed: %s', exc)
