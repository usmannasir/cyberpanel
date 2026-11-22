"""Bounded waiting for website deletion without cancelling the worker."""
import json
import queue
import threading

RESULT_PREFIX = 'WEBSITE_DELETE_RESULT='

# What the creation of a website uses when it is already there instead of
# making it: the DNS zone of that name, its mail folder, and the work folder
# of its certificate. Undoing a creation leaves those of them it found.
REUSABLE = ('dns', 'mail', 'ssl')


def found_before_creation(zone, mail, certificate):
    """The names of what was already there when a website's creation began.

    Each argument is True, False, or None when it could not be told. Only a
    clear "it was not there" makes a thing the creation's own.
    """
    return tuple(name for name, found in zip(REUSABLE, (zone, mail, certificate)) if found is not False)


def kept_by_creation(text):
    """The names in a worker's --keep argument; anything else in it is ignored."""
    return tuple(name for name in REUSABLE if name in str(text or '').split(','))


def wait_for_deletion(command, execute, log, timeout=15):
    result_queue = queue.Queue(maxsize=1)

    def run():
        try:
            result = execute(command, retRequired=True)
            succeeded = False
            if result and len(result) == 2:
                code, output = result
                lines = str(output or '').splitlines()
                if lines and lines[-1].startswith(RESULT_PREFIX):
                    payload = json.loads(lines[-1][len(RESULT_PREFIX):])
                    succeeded = code == 1 and payload.get('completed') is True
            if not succeeded:
                log('Website deletion worker did not confirm completion. See the preceding helper errors.')
            result_queue.put('completed' if succeeded else 'failed')
        except BaseException as error:
            log('Website deletion worker failed: %s' % error)
            result_queue.put('failed')

    worker = threading.Thread(target=run, name='website-deletion')
    # A wait timeout never terminates a deletion already in progress.
    try:
        worker.start()
    except RuntimeError as error:
        log('Website deletion worker could not start: %s' % error)
        return 'failed'
    try:
        return result_queue.get(timeout=timeout)
    except queue.Empty:
        return 'pending'
