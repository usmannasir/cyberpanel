import json
import configparser

CurrentContent = """[usman]
type = sftp
host = staging.cyberpanel.net
user = abcds2751
pass = s0RBbJU8EhfQ-wvFgbOVEmy3HK6y19A
shell_type = unix
md5sum_command = md5sum
sha1sum_command = sha1sum

[habbitest2gdrive]
type = drive
client_id = ""
client_secret = ""
scope = drive
root_folder_id = ""
service_account_file = ""
token = {"access_token":"ya29.a0Ael9sCPUpwAZpHChyBkAYrDGo5BRjkj2OV1r9KNBXdXZZrjTrjPOHxTkayEr-hfKNhsqYrvChowxQw-EgTO7JobBE7IrZpLDpdpEOTY49JOg-PagtPLU_TuqFPab356TdeC0-f2RHQ_2arU1pN92aKcgfp7CaCgYKASESARESFQF4udJhaS1_8FVFFkG-ds0yPY0APA0163","token_type":"Bearer","refresh_token":"1//09Sgboc4b9-kYCgYIARAAGAkSNgF-L9IrgxJ3jKcd0UDraNAncWDKRUNu0L5ORiaS8H_QaXv2y85p0cL3ZArEaShSxy2P_Kb0CQ"}
"""

# Read the configuration string
config = configparser.ConfigParser()
config.read_string(CurrentContent)

# Get the refresh token
refresh_token = json.loads(config.get('habbitest2gdrive', 'token'))['refresh_token']
old_access_token = json.loads(config.get('habbitest2gdrive', 'token'))['access_token']
print(refresh_token)

new_token ="jdskjkvnckjdfvnjknvkvdjc"
new_string = CurrentContent.replace(str(old_access_token), new_token)

print(new_string)