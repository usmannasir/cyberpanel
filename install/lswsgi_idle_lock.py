"""Let Python threads run while the panel's web worker waits for a request.

    python lswsgi_idle_lock.py /path/to/wsgi-lsapi-X.Y/main.c

lscpd starts the panel as "lswsgi -m <wsgi.py>". In that mode lswsgi takes
Python's interpreter lock once and keeps it for as long as it serves, also
while it waits for the next request. A thread started by a request (a backup,
a restore, an installer) then cannot run until the same worker serves another
request: progress pages advance only while they poll and a job nobody polls
does not move at all.

This edit releases the lock for the wait only. It is exact: a source that is
not what is expected is left untouched and the exit status is 1, and the
caller then builds the worker as before.
"""
import sys

WAIT = '    while ( LSAPI_Prefork_Accept_r ( &g_req ) >= 0 )\n'
MAIN = 'int main ( int argc, char *argv[] )\n'
HELPER = '''/* A process waiting for its next request must not keep Python's interpreter
   lock: threads started by a request could not run until the next one. */
static int wsgi_wait_for_request(int holds_lock)
{
    PyThreadState *waiting = NULL;
    int accepted;

    if (holds_lock)
        waiting = PyEval_SaveThread();
    accepted = LSAPI_Prefork_Accept_r(&g_req);
    if (holds_lock)
        PyEval_RestoreThread(waiting);
    return accepted;
}


'''


def patched(source):
    """The source with the lock released for the wait, or ValueError."""
    if 'wsgi_wait_for_request' in source:
        return source
    if source.count(WAIT) != 1 or source.count(MAIN) != 1:
        raise ValueError('unexpected lswsgi source')
    # wsgi-lsapi 2.2 records the lock in gil_held; 2.1 holds it when an
    # application was preloaded.
    if 'int gil_held = 0;' in source:
        holds_lock = 'gil_held'
    elif 'PyObject *app = NULL;' in source:
        holds_lock = 'app != NULL'
    else:
        raise ValueError('unexpected lswsgi source')
    source = source.replace(MAIN, HELPER + MAIN)
    return source.replace(WAIT, '    while ( wsgi_wait_for_request( %s ) >= 0 )\n' % holds_lock)


def apply(path):
    """Edit main.c in place. True when the file now has the change."""
    try:
        with open(path) as handle:
            source = handle.read()
        result = patched(source)
    except (OSError, ValueError):
        return False
    if result != source:
        with open(path, 'w') as handle:
            handle.write(result)
    return True


if __name__ == '__main__':
    sys.exit(0 if len(sys.argv) == 2 and apply(sys.argv[1]) else 1)
