import os
import shutil
import pathlib


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
    os.chmod(file_path, int(str(perms), base=8))


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
    Symlink a patch to another if the src exists.
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


# https://docs.python.org/3.6/library/os.html#os.walk
#
#
def recursive_permissions(path, dir_mode=755, file_mode=644, topdir=True):
    """
    Recursively chmod a path and contents to mode.
    Defaults to chmod top level directory but can be optionally
    toggled off when you want to chmod only contents of like a user's homedir vs homedir itself
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
