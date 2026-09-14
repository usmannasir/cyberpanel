"""Bounded waiting for website deletion without cancelling the worker."""
import json
import queue
import threading

RESULT_PREFIX = 'WEBSITE_DELETE_RESULT='


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
