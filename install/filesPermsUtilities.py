import os
import shutil
import pathlib
import stat


def mkdir_p(path, exist_ok=True):
    """
    Creates the directory and paths leading up to it like unix mkdir -p .
    Defaults to exist_ok so if it exists were not throwing fatal errors
    https://docs.python.org/3.7/library/os.html#os.makedirs
    """
    if not os.path.exists(path):
        print('creating directory: ' + path)
        os.makedirs(path, exist_ok)


def chmod_digit(file_path, perms):
    """
    Helper function to chmod like you would in unix without having to preface 0o or converting to octal yourself.
    Credits: https://stackoverflow.com/a/60052847/1621381
    """
    try:
        os.chmod(file_path, int(str(perms), base=8))
    except:
        print(f'Could not chmod : {file_path} to {perms}')
        pass


def touch(filepath: str, exist_ok=True):
    """
    Touches a file like unix `touch somefile` would.
    """
    try:
        pathlib.Path(filepath).touch(exist_ok)
    except FileExistsError:
        print('Could touch : ' + filepath)
        pass


def symlink(src, dst):
    """
    Symlink a path to another if the src exists.
    """
    try:
        if os.access(src, os.R_OK):
            os.symlink(src, dst)
    except:
        print(f'Could not symlink Source: {src} > Destination: {dst}')
        pass


def chown(path, user, group=-1):
    """
    Chown file/path to user/group provided. Passing -1 to user or group will leave it unchanged.
    Useful if just changing user or group vs both.
    """
    try:
        shutil.chown(path, user, group)
    except PermissionError:
        print(f'Could not change permissions for: {path} to {user}:{group}')
        pass


def recursive_chown(path, owner, group=-1):
    """
    Recursively chown a path and contents to owner.
    https://docs.python.org/3/library/shutil.html
    """
    for dirpath, dirnames, filenames in os.walk(path):
        try:
            shutil.chown(dirpath, owner, group)
        except PermissionError:
            print('Could not change permissions for: ' + dirpath + ' to: ' + owner)
            pass
        for filename in filenames:
            try:
                shutil.chown(os.path.join(dirpath, filename), owner, group)
            except PermissionError:
                print('Could not change permissions for: ' + os.path.join(dirpath, filename) + ' to: ' + owner)
                pass


def recursive_permissions(path, dir_mode=755, file_mode=644, topdir=True):
    """
    Recursively chmod a path and contents to mode.
    Defaults to chmod top level directory but can be optionally
    toggled off when you want to chmod only contents of like a user's homedir vs homedir itself
    https://docs.python.org/3.6/library/os.html#os.walk
    """

    # Here we are converting the integers to string and then to octal.
    # so this function doesn't need to be called with 0o prefixed for the file and dir mode
    dir_mode = int(str(dir_mode), base=8)
    file_mode = int(str(file_mode), base=8)

    if topdir:
        # Set chmod on top level path
        try:
            os.chmod(path, dir_mode)
        except:
            print('Could not chmod :' + path + ' to ' + str(dir_mode))
    for root, dirs, files in os.walk(path):
        for d in dirs:
            try:
                os.chmod(os.path.join(root, d), dir_mode)
            except:
                print('Could not chmod :' + os.path.join(root, d) + ' to ' + str(dir_mode))
                pass
        for f in files:
            try:
                os.chmod(os.path.join(root, f), file_mode)
            except:
                print('Could not chmod :' + path + ' to ' + str(file_mode))
                pass


# Left intentionally here for reference.
# Set recursive chown for a path
# recursive_chown(my_path, 'root', 'root')
# for changing group recursively without affecting user
# recursive_chown('/usr/local/lscp/cyberpanel/rainloop/data', -1, 'lscpd')

# explicitly set permissions for directories/folders to 0755 and files to 0644
# recursive_permissions(my_path, 755, 644)

# Fix permissions and use default values
# recursive_permissions(my_path)
# =========================================================
# Below is a helper class for getting and working with permissions
# Original credits to : https://github.com/keysemble/perfm

def perm_octal_digit(rwx):
    digit = 0
    if rwx[0] == 'r':
        digit += 4
    if rwx[1] == 'w':
        digit += 2
    if rwx[2] == 'x':
        digit += 1
    return digit


class FilePerm:
    def __init__(self, filepath):
        filemode = stat.filemode(os.stat(filepath).st_mode)
        permissions = [filemode[-9:][i:i + 3] for i in range(0, len(filemode[-9:]), 3)]
        self.filepath = filepath
        self.access_dict = dict(zip(['user', 'group', 'other'], [list(perm) for perm in permissions]))

    def mode(self):
        mode = 0
        for shift, digit in enumerate(self.octal()[::-1]):
            mode += digit << (shift * 3)
        return mode

    def digits(self):
        """Get the octal chmod equivalent value 755 in single string"""
        return "".join(map(str, self.octal()))

    def octal(self):
        """Get the octal value in a list [7, 5, 5]"""
        return [perm_octal_digit(p) for p in self.access_dict.values()]

    def access_bits(self, access):
        if access in self.access_dict.keys():
            r, w, x = self.access_dict[access]
            return [r == 'r', w == 'w', x == 'x']

    def update_bitwise(self, settings):
        def perm_list(read=False, write=False, execute=False):
            pl = ['-', '-', '-']
            if read:
                pl[0] = 'r'
            if write:
                pl[1] = 'w'
            if execute:
                pl[2] = 'x'
            return pl

        self.access_dict = dict(
            [(access, perm_list(read=r, write=w, execute=x)) for access, [r, w, x] in settings.items()])
        os.chmod(self.filepath, self.mode())

# project_directory = os.path.abspath(os.path.dirname(sys.argv[0]))
# home_directory = os.path.expanduser('~')
# print(f'Path: {home_directory}  Mode: {FilePerm(home_directory).mode()}  Octal: {FilePerm(home_directory).octal()} '
#      f'Digits: {FilePerm(home_directory).digits()}')
# Example: Output
# Path: /home/cooluser  Mode: 493  Octal: [7, 5, 5] Digits: 755
