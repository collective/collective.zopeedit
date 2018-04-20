import os.path
import os

def test_zopeedit_installed(host):
    path = list()
    path.append("C:")
    path.append("Program Files (x86)")
    path.append("ZopeExternalEditor")
    path.append("zopeedit.exe")
    host.file(os.sep.join(path)).exists
