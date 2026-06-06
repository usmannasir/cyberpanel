import json
from plogical.processUtilities import ProcessUtilities
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging

def list_docker_maps(include_stopped=False):
    cmd = 'docker ps -a --format "{{json .}}"' if include_stopped else 'docker ps --format "{{json .}}"'
    try:
        out = ProcessUtilities.outputExecutioner(cmd) or ''
    except Exception as e:
        logging.writeToFile('Port Manager docker: %s' % e)
        return []
    rows = []
    for line in out.splitlines():
        line = line.strip()
        if not line: continue
        try: o = json.loads(line)
        except json.JSONDecodeError: continue
        state = (o.get('State') or o.get('Status') or '')
        running = (o.get('State') == 'running') or state.lower().startswith('up ')
        if not include_stopped and not running:
            continue
        ports = (o.get('Ports') or '').strip()
        rows.append({
            'id': o.get('ID', ''),
            'name': o.get('Names', ''),
            'image': o.get('Image', ''),
            'state': state,
            'running': running,
            'ports': ports if ports else '(no published ports)',
        })
    return sorted(rows, key=lambda x: (not x['running'], x['name'].lower()))
