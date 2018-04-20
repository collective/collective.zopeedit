import os.path
import os

from sys import platform

def test_instance():
    path = list()
    path.append(os.getcwd())
    path.append("tests")
    path.append("bin")
    filename = "instance"
    if platform == "win32":
        filename += ".exe"
    path.append(filename)
    assert os.path.exists(os.sep.join(path))
