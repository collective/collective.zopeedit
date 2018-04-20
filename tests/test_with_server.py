import os.path
import os

import sys
import inspect
import socket, errno
import requests

def test_instance_script():
    path = list()
    basedir = os.path.dirname(inspect.getfile(sys.modules[__name__]))
    path.append(basedir)
    path.append("bin")
    filename = "instance"
    if sys.platform == "win32":
        filename += ".exe"
    path.append(filename)
    assert os.path.exists(os.sep.join(path))

def test_instance_started():
    socket_is_bound = False
    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
	s.bind(("127.0.0.1", 8080))
    except socket.error as e:
	if e.errno == errno.EADDRINUSE:
	    socket_is_bound = True
    s.close()
    assert(socket_is_bound)

def test_instance_has_externalfile():
    r = requests.get('http://localhost:8080/test_external')
    assert r.status_code == 200
  
