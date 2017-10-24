"""
Django backend for angular-filemanager

The MIT License (MIT)

Copyright (c) 2017 Esmairi Adel

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""


import datetime
import json
import os
import shutil
import stat
import zipfile
from django.core.files.storage import FileSystemStorage
from distutils.dir_util import copy_tree
import tempfile
import shlex
import subprocess

def timestamp_to_str(timestamp, format_str='%Y-%m-%d %I:%M:%S'):
    date = datetime.datetime.fromtimestamp(timestamp)
    return date.strftime(format_str)


def filemode(mode):
    is_dir = 'd' if stat.S_ISDIR(mode) else '-'
    dic = {'7': 'rwx', '6': 'rw-', '5': 'r-x', '4': 'r--', '0': '---'}
    perm = str(oct(mode)[-3:])
    return is_dir + ''.join(dic.get(x, x) for x in perm)


def compress_zip(base_name, folders):
    with zipfile.ZipFile(base_name + '.zip',
                         "w",
                         zipfile.ZIP_DEFLATED,
                         allowZip64=True) as zf:
        for f in folders:
            if os.path.isfile(f):
                zf.write(f,os.path.basename(f))
                continue
            os.chdir(os.path.dirname(f))
            for root, _, filenames in os.walk(os.path.basename(f)):
                for name in filenames:
                    name = os.path.join(root, name)
                    name = os.path.normpath(name)
                    zf.write(name, name)


def get_file_information(path):
    fstat = os.stat(path)
    if stat.S_ISDIR(fstat.st_mode):
        ftype = 'dir'
    else:
        ftype = 'file'
    fsize = fstat.st_size
    ftime = timestamp_to_str(fstat.st_mtime)
    fmode = filemode(fstat.st_mode)
    return ftype, fsize, ftime, fmode


def change_permissions_recursive(path, mode):
    for root, dirs, files in os.walk(path, topdown=False):
        for d in [os.path.join(root, d) for d in dirs]:
            os.chmod(d, mode)
        for f in [os.path.join(root, f) for f in files]:
            os.chmod(f, mode)


class FileManager:
    def __init__(self, root,show_dotfiles=True):
        self.root = root
        self.show_dotfiles = show_dotfiles

    def list(self, request):
        path = os.path.abspath(self.root + request['path'])
        if not os.path.exists(path) or not path.startswith(self.root):
            return {'result': ''}

        command = 'chown -R nobody:nobody '+path

        cmd = shlex.split(command)

        res = subprocess.call(cmd)


        files = []
        for fname in sorted(os.listdir(path)):
            if fname.startswith('.') and not self.show_dotfiles:
                continue
            fpath = os.path.join(path, fname)
            try:
                ftype, fsize, ftime, fmode = get_file_information(fpath)
            except Exception as e:
                continue
            files.append({
                'name': fname,
                'rights': fmode,
                'size': fsize,
                'date': ftime,
                'type': ftype,
            })

        return {'result': files}

    def rename(self, request):
        try:
            src = os.path.abspath(self.root + request['item'])
            dst = os.path.abspath(self.root + request['newItemPath'])
            if not (os.path.exists(src) and src.startswith(self.root) and dst.startswith(self.root)):
                return {'result': {'success': 'false', 'error': 'Invalid path'}}
            shutil.move(src, dst)
        except Exception as e:
            return {'result': {'success': 'false', 'error': e.message}}
        return {'result': {'success': 'true', 'error': ''}}

    def copy(self, request):
        try:
            items = request['items']
            if len(items) == 1 and 'singleFilename' in request:
                src = os.path.abspath(self.root + items[0])
                dst = os.path.abspath(self.root + request['newPath'] + '/' + request['singleFilename'])
                if not (os.path.exists(src) and src.startswith(self.root) and dst.startswith(self.root)):
                    return {'result': {'success': 'false', 'error': 'File not found'}}
                shutil.copyfile(src, dst)
            else:
                path = os.path.abspath(self.root + request['newPath'])
                for item in items:
                    src = os.path.abspath(self.root + item)
                    if not (os.path.exists(src) and src.startswith(self.root) and path.startswith(self.root)):
                        return {'result': {'success': 'false', 'error': 'Invalid path'}}
                    shutil.copyfile(src, path)
        except Exception as e:
            return {'result': {'success': 'false', 'error': e.message}}
        return {'result': {'success': 'true', 'error': ''}}

    def remove(self, request):
        try:
            items = request['items']
            for item in items:
                path = os.path.abspath(self.root + item)
                if not (os.path.exists(path) and path.startswith(self.root)):
                    return {'result': {'success': 'false', 'error': 'Invalid path'}}
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
        except Exception as e:
            return {'result': {'success': 'false', 'error': e.message}}
        return {'result': {'success': 'true', 'error': ''}}

    def edit(self, request):
        try:
            path = os.path.abspath(self.root + request['item'])
            if not path.startswith(self.root):
                return {'result': {'success': 'false', 'error': 'Invalid path'}}
            content = request['content']
            with open(path, 'w') as f:
                f.write(content)
        except Exception as e:
            return {'result': {'success': 'false', 'error': e.message}}
        return {'result': {'success': 'true', 'error': ''}}

    def getContent(self, request):
        try:
            path = os.path.abspath(self.root + request['item'])
            if not path.startswith(self.root):
                return {'result': {'success': 'false', 'error': 'Invalid path'}}
            with open(path, 'r') as f:
                content = f.read()
        except Exception as e:
            content = e.message
        return {'result': content}

    def createFolder(self, request):
        try:
            path = os.path.abspath(self.root + request['newPath'])
            if not path.startswith(self.root):
                return {'result': {'success': 'false', 'error': 'Invalid path'}}
            os.makedirs(path)
        except Exception as e:
            return {'result': {'success': 'false', 'error': e.message}}
        return {'result': {'success': 'true', 'error': ''}}

    def move(self, request):
        try:
            dst = os.path.abspath(self.root + request['newPath'])
            if not dst.startswith(self.root):
                return {'result': {'success': 'false', 'error': 'Invalid path'}}
            for item in request['items']:
                src = os.path.abspath(self.root + item)
                if not (os.path.exists(src) and src.startswith(self.root) and dst.startswith(self.root)):
                    return {'result': {'success': 'false', 'error': 'Invalid path'}}
                shutil.move(src, dst)
        except Exception as e:
            return {'result': {'success': 'false', 'error': e.message}}
        return {'result': {'success': 'true', 'error': ''}}

    def changePermissions(self, request):
        try:
            items = request['items']
            permissions = int(request['permsCode'], 8)
            recursive = request['recursive']
            for item in items:
                path = os.path.abspath(self.root + item)
                if not (os.path.exists(path) and path.startswith(self.root)):
                    return {'result': {'success': 'false', 'error': 'Invalid path'}}
                if recursive:
                    change_permissions_recursive(path, permissions)
                else:
                    os.chmod(path, permissions)
        except Exception as e:
            return {'result': {'success': 'false', 'error': e.message}}
        return {'result': {'success': 'true', 'error': ''}}

    def compress(self, request):
        try:
            items = request['items']
            path = os.path.abspath(os.path.join(self.root + request['destination'], request['compressedFilename']))
            if not path.startswith(self.root):
                return {'result': {'success': 'false', 'error': 'Invalid path'}}
            folders = []
            for item in items:
                _path = os.path.abspath(self.root + item)
                if not (os.path.exists(_path) and _path.startswith(self.root)):
                    continue
                folders.append(_path)
            compress_zip(path, folders)
        except Exception as e:
            return {'result': {'success': 'false', 'error': e.message}}
        return {'result': {'success': 'true', 'error': ''}}

    def extract(self, request):
        try:
            src = os.path.abspath(self.root + request['item'])
            dst = os.path.abspath(self.root + request['destination'] + '/' + request['folderName'])
            if not (os.path.isfile(src) and src.startswith(self.root) and dst.startswith(self.root)):
                return {'result': {'success': 'false', 'error': 'Invalid path'}}
            zip_file = zipfile.ZipFile(src, 'r')
            zip_file.extractall(dst)
            zip_file.close()
        except Exception as e:
            return {'result': {'success': 'false', 'error': e.message}}
        return {'result': {'success': 'true', 'error': ''}}

    def upload(self, files, dest):
        try:
            for _file in list(files):
                path = os.path.join(self.root, dest.replace('/', '', 1))
                if not path.startswith(self.root):
                     return {'result': {'success': 'false', 'error': 'Invalid path'}}
                fs = FileSystemStorage(location=path)
                fs.save(files.get(_file).name, files.get(_file))
        except Exception as e:
            return {'result': {'success': 'false', 'error': e.message}}
        return {'result': {'success': 'true', 'error': ''}}

    def download(self, path, HttpResponse):
        path = os.path.abspath(self.root + path)
        response = ''
        if path.startswith(self.root) and os.path.isfile(path):
            try:
                with open(path, 'rb') as f:
                    response = HttpResponse(f.read(), content_type="application/octet-stream")
                    response['Content-Disposition'] = 'inline; filename=' + os.path.basename(path)
            except Exception as e:
                raise Http404
        return response

    def downloadMultiple(self, request, HttpResponse):
        items = dict(request.iterlists())
        folders = []
        for item in items['items[]']:
            _path = os.path.join(self.root + os.path.expanduser(item))
            if not ( (os.path.exists(_path) or os.path.isfile(_path))and _path.startswith(self.root)):
                continue
            folders.append(_path)
        tmpdir = tempfile.mkdtemp()
        filename = items['toFilename'][0].replace('.zip', '',1)
        saved_umask = os.umask(0077)
        path = os.path.join(tmpdir, filename)
        try:
            compress_zip(path, folders)
            with open(path+".zip", 'rb') as f:
                    response = HttpResponse(f.read(), content_type="application/octet-stream")
                    response['Content-Disposition'] = 'inline; filename=' + os.path.basename(path)+'.zip'
            return [response, saved_umask, tmpdir]
        except IOError as e:
            print("IOError")
        else:
            shutil.rmtree(tmpdir, ignore_errors=True)
