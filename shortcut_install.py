import os
import platform

app_root = os.path.dirname(os.path.realpath(__file__))


import ctypes
from ctypes import wintypes
_GetShortPathNameW = ctypes.windll.kernel32.GetShortPathNameW
_GetShortPathNameW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
_GetShortPathNameW.restype = wintypes.DWORD

import subprocess
import tempfile


def create_shortcut(shortcut_path, icon, target, arguments='', working_dir=''):

    def escape_path(path):
        return str(path).replace('\\', '/')

    def escape_str(str_):
        return str(str_).replace('\\', '\\\\').replace('"', '\\"')

    shortcut_path = escape_path(shortcut_path)
    target = escape_path(target)
    working_dir = escape_path(working_dir)
    arguments = escape_str(arguments)
    icon_path = escape_path(icon)
    js_content = 'var sh = WScript.CreateObject("WScript.Shell");\nvar shortcut = sh.CreateShortcut("{0}");shortcut.IconLocation = "{1}";\nshortcut.TargetPath = "{2}";\nshortcut.Arguments = "{3}";\nshortcut.WorkingDirectory = "{4}";\nshortcut.Save();'.format(shortcut_path,icon_path,target,arguments,working_dir)

    fd, path = tempfile.mkstemp('.js')
    try:
        with os.fdopen(fd, 'w') as f:
            f.write(js_content)
        subprocess.call([R'wscript.exe', path])
    finally:
        os.unlink(path)


def get_short_path_name(long_name):
    """
    Gets the short path name of a given long path for windows.
    http://stackoverflow.com/a/23598461/200291
    """
    output_buf_size = 0
    while True:
        output_buf = ctypes.create_unicode_buffer(output_buf_size)
        needed = _GetShortPathNameW(long_name, output_buf, output_buf_size)
        if output_buf_size >= needed:
            return output_buf.value
        else:
            output_buf_size = needed


def getDesktop():

    system_os = platform.system()
    if system_os == 'Darwin':
        desktop = os.path.join(os.getenv('HOME'), 'Desktop')

    elif system_os == 'Windows':
        desktop = os.path.join(os.getenv('userprofile'), 'Desktop')

    return desktop

def install_shortcut(shorcut_name,args,wdir,python_path,icon):

    desktop = getDesktop()
    python_path = get_short_path_name(python_path)
    #if "Windows-11" in platform.platform():
    shortcut_path = os.path.join(desktop, shorcut_name + ".lnk")
    wdir = get_short_path_name(wdir)

    if not os.path.exists(shortcut_path):
        print("creating {0} shortcut...".format(shorcut_name))
        create_shortcut(shortcut_path,icon, python_path, arguments=args, working_dir=wdir)
    else:
        print('not necessary to create {0} shortcut'.format(shorcut_name))



if __name__ == '__main__':

    app_root = os.path.dirname(os.path.realpath(__file__))
    python_path = os.path.join(app_root, 'events3', 'Scripts', 'python.exe')
    install_shortcut("ftrack_events",'events.py',app_root,python_path,os.path.join(app_root,"events.ico"))
