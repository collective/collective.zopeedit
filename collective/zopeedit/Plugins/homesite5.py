##############################################################################
#
# Copyright (c) 2001, 2002 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""External Editor HomeSite Plugin

$Id: homesite5.py 67450 2002-09-01 05:03:43Z caseman $
"""

from time import sleep
from win32com import client  # Initialize Client module

import win32com


class EditorProcess:
    def __init__(self, file):
        """Launch editor process"""
        hs = win32com.client.Dispatch("AllaireClientApp.TAllaireClientApp")
        # Try to open the file, keep retrying until we succeed or timeout
        i = 0
        timeout = 45
        while i < timeout:
            try:
                hs.OpenFile(file)
            except:
                i += 1
                if i >= timeout:
                    raise RuntimeError("Could not launch Homesite.")
                sleep(1)
            else:
                break
        self.hs = hs
        self.file = file

    def wait(self, timeout):
        """Wait for editor to exit or until timeout"""
        sleep(timeout)

    def isAlive(self):
        """Returns true if the editor process is still alive"""
        return self.hs.IsFileOpen(self.file)


def test():
    import os
    from time import sleep
    from tempfile import mktemp

    fn = mktemp(".html")
    f = open(fn, "w")
    f.write("<html>\n  <head></head>\n  <body>\n  </body>\n</html>")
    f.close()
    print("Connecting to HomeSite...")
    f = EditorProcess(fn)
    print "Attached to %s %s" % (` f.hs `, f.hs.VersionText)
    print ("%s is open..." % fn),
    if f.isAlive():
        print("yes")
        print("Test Passed.")
    else:
        print("no")
        print("Test Failed.")


if __name__ == "__main__":
    test()
