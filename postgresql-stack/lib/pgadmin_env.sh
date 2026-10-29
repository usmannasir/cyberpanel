#!/usr/bin/env bash
# Run pgAdmin setup.py via venv Python (avoid /usr/local package conflicts).
pgadmin_python() {
    local pgadmin_web="/usr/pgadmin4/web"
    local pgadmin_py="/usr/pgadmin4/venv/bin/python3"
    local args_json
    args_json="$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1:]))' -- "$@")"
    (
        cd "${pgadmin_web}"
        ARGS_JSON="${args_json}" "${pgadmin_py}" -c "
import json, os, runpy, sys
sys.path = [p for p in sys.path if '/usr/local/' not in p]
sys.argv = ['setup.py'] + json.loads(os.environ['ARGS_JSON'])
runpy.run_path('setup.py', run_name='__main__')
"
    )
}
