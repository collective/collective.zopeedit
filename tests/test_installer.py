import os.path
import os

def test():
    drive, tail = os.path.splitdrive(os.getcwd())
    path = list()
    path.append(drive)
    path.append("inst")
    path.append("zopeedit.exe")
    assert os.path.exists(os.sep.join(path))
