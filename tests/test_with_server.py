import os.path
import os

def test_instance():
    path = list()
    path.append(os.getcwd())
    path.append("tests")
    path.append("bin")
    path.append("instance")
    assert os.path.exists(os.sep.join(path))
