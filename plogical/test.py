import subprocess
import json

command = 'postqueue -j'

result = subprocess.check_output(command, shell=True).decode().split('\n')

result = result[0]

data = json.loads(result)

print(data['queue_name'])