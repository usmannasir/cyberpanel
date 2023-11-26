import subprocess

# Run the shell command and capture the output
result = subprocess.run(['ls', '-la'], capture_output=True, text=True)

# Get the lines containing 'lsphp' in the output
lsphp_lines = [line for line in result.stdout.split('\n') if 'lsphp' in line]

# Extract the version from the lines
php_versions = [line.split()[8] for line in lsphp_lines]

print(php_versions)

