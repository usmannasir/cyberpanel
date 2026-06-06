from ..models import PortManagerAudit

def log_action(actor, action, detail='', success=True):
    try:
        PortManagerAudit.objects.create(
            actor=(actor or '')[:128],
            action=(action or '')[:64],
            detail=(detail or '')[:2000],
            success=bool(success),
        )
    except Exception:
        pass
