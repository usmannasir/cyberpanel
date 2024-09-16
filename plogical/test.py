import os
import shutil
import subprocess


def edit_fstab(mount_point, options_to_add):
    # Backup the original fstab file
    fstab_path = '/etc/fstab'
    backup_path = fstab_path + '.bak'

    if not os.path.exists(backup_path):
        shutil.copy(fstab_path, backup_path)


    # Read the fstab file
    with open(fstab_path, 'r') as file:
        lines = file.readlines()

    # Modify the appropriate line
    WriteToFile = open(fstab_path, 'w')
    for i, line in enumerate(lines):

        if line.find('\t') > -1:
            parts = line.split('\t')
        else:
            parts = line.split(' ')

        #print(parts)
        try:
            if parts[1] == '/' and parts[3].find('usrquota,grpquota') == -1:
                parts[3] = f'{parts[3]},usrquota,grpquota'
                finalString = '\t'.join(parts)
                #print(finalString)
                WriteToFile.write(finalString)
            else:
                WriteToFile.write(line)
        except:
            WriteToFile.write(line)
    WriteToFile.close()


    try:
        command = "find /lib/modules/ -type f -name '*quota_v*.ko*'"
        result = subprocess.run(command, capture_output=True, text=True, shell=True)
        print(repr(result.stdout))

        # Only if the first command works, run the rest
        if result.returncode == 0:
            command = "echo '{}' | sed -n 's|/lib/modules/\\([^/]*\\)/.*|\\1|p' | sort -u".format(result.stdout)
            result = subprocess.run(command, capture_output=True, text=True, shell=True)
            print(repr(result.stdout.rstrip('\n')))

    except subprocess.CalledProcessError as e:
        print("Error:", e.output.decode())


edit_fstab('/', '/')


        

