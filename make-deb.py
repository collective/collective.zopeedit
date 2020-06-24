#!/usr/bin/env python
# -*- coding: utf-8 -*-
##############################################################################
#
#   ZopeEdit, client for ExternalEditor
#
#   zopeedit.deb package creator
#
#   Install collective.zopeedit as a python lib
#   and create a launcher that calls zopeedit.main()
#
##############################################################################
from glob import glob
from py2deb import *

import os


opj = os.path.join
# Open the VERSION file for reading.
f = open("docs/VERSION.txt", "r")
# Below, "[:-1]" means we omit the last character, which is "\n".
version = f.readline()[:-1]
f.close

os.system("gzip collective/zopeedit/man/zopeedit.1")

changelog = open("docs/HISTORY.txt", "r").read()

p = Py2deb("collective.zopeedit")
p.author = "Thierry Benita - atReal"
p.mail = "contact@atreal.net"
p.description = """ZopeEdit is a Zope ExternalEditor client."""
p.url = "http://svn.plone.org/svn/collective/collective.zopeedit/"
p.depends = "bash, psmisc, python2.6, python-tk"
p.license = "gpl"
p.section = "utils"
p.arch = "all"
p.preremove = "collective/zopeedit/posix/preremove.sh"

p["/usr/share/app-install/desktop"] = [
    "collective/zopeedit/posix/zopeedit.desktop|zopeedit.desktop"
]
p["/usr/share/applications"] = [
    "collective/zopeedit/posix/zopeedit.desktop|zopeedit.desktop"
]
p["/usr/share/app-install/icons"] = [
    "collective/zopeedit/posix/zopeedit.svg|zopeedit.svg"
]
p["/usr/share/pixmaps"] = ["collective/zopeedit/posix/zopeedit.svg|zopeedit.svg"]
p["/usr/share/man/man1"] = ["collective/zopeedit/man/zopeedit.1.gz|zopeedit.1.gz"]
p["/usr/share/mime/application"] = [
    "collective/zopeedit/posix/x-zope-edit-zem.xml|x-zope-edit-zem.xml"
]
p["/usr/lib/python2.6/dist-packages"] = [
    "collective/zopeedit/posix/collective.zopeedit.pth|collective.zopeedit.pth"
]

p["/usr/lib/python2.6/dist-packages/collective.zopeedit/collective"] = [
    "collective/__init__.py|__init__.py"
]

p["/usr/lib/python2.6/dist-packages/collective.zopeedit/collective/zopeedit"] = [
    "collective/zopeedit/zopeedit.py|zopeedit.py",
    "collective/zopeedit/__init__.py|__init__.py",
]

p[
    "/usr/lib/python2.6/dist-packages/collective.zopeedit/collective/zopeedit/locales"
] = [i + "|" + i[28:] for i in glob("collective/zopeedit/locales/*/*/zopeedit.mo")]

p[
    "/usr/lib/python2.6/dist-packages/collective.zopeedit/collective/zopeedit/Plugins"
] = [i + "|" + i[28:] for i in glob("collective/zopeedit/Plugins/*.py")]

p["/usr/lib/python2.6/dist-packages/collective.zopeedit/collective/zopeedit/docs"] = [
    i + "|" + i[5:] for i in glob("docs/*.txt")
]

p["/usr/bin"] = ["collective/zopeedit/posix/zopeedit_launcher.py|zopeedit"]
p["/usr/share/doc/zopeedit"] = [i + "|" + i[5:] for i in glob("docs/*")]

p.generate(version, changelog, rpm=True, src=True)

os.system("gunzip collective/zopeedit/man/zopeedit.1.gz")
