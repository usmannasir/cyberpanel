"""How an incremental backup or restore job ended, read from its status file.

A job appends one line for each thing it does. A step that fails writes a
line with the failure mark and the job stops; a job that finishes writes
`Completed` as a line of its own, and that line is its last.

Lines of a status file carry text the job did not choose: the messages of
the programs it ran, and in those the names of files and mail folders. So
the end of a job is not read from words found anywhere in the file. A
failure mark on any line means the job failed, whatever follows it; and the
job is done only when its last line is the `Completed` line and nothing else.
"""

FAILURE_MARK = '[5009]'
DONE_LINE = 'Completed'

FAILED = 'failed'
DONE = 'done'


def job_end(status):
    """FAILED, DONE, or None while the job still runs."""
    lines = [line.strip() for line in (status or '').splitlines() if line.strip()]
    if any(FAILURE_MARK in line for line in lines):
        return FAILED
    if lines and lines[-1] == DONE_LINE:
        return DONE
    return None
