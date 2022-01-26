#!/usr/bin/env python
# -*- coding: utf-8 -*-
##############################################################################
#
#   ZopeEdit, client for ExternalEditor
#
##############################################################################

from setuptools import find_packages
from setuptools import setup

import glob
import os
import sys


opj = os.path.join

def get_version():
    with open(os.path.join('collective', 'zopeedit', 'zopeedit.py')) as f:
        for line in f:
            if line.startswith('__version__'):
                return eval(line.split('=')[-1])

install_requires = ["setuptools"]
if sys.platform == "darwin":
    install_requires.extend(
        [
            "pyobjc-core",
            "pyobjc-framework-LaunchServices",
        ]
    )

packages = find_packages(exclude=["ez_setup"])


def data_files():
    """Build list of data files to be installed"""
    files = []

    files.append(
        (opj("share", "man", "man1", ""), ["collective/zopeedit/man/zopeedit.1"])
    )
    files.append(
        (
            opj("share", "mime", "application"),
            ["collective/zopeedit/posix/x-zope-edit-zem.xml"],
        )
    )
    files.append(
        (opj("share", "applications"), ["collective/zopeedit/posix/zopeedit.desktop"])
    )
    files.append((opj("share", "icons"), ["collective/zopeedit/posix/zopeedit.svg"]))
    files.append(
        (
            opj("collective", "zopeedit", "docs"),
            [f for f in glob.glob("docs/*") if os.path.isfile(f)],
        )
    )
    files.append((opj("collective", "zopeedit", "docs"), ["README.txt"]))

    return files


setup(
    name="collective.zopeedit",
    app=[os.path.join("collective", "zopeedit", "zopeedit.py")],
    version=get_version(),
    description="ZopeEdit : External Editor Client",
    long_description=open("README.txt").read()
    + "\n"
    + open(os.path.join("docs", "HISTORY.txt")).read(),
    # Get more strings from
    # http://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        "Programming Language :: Python",
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: Zope Public License",
    ],
    keywords="zope plone externaleditor zopeedit edition",
    author="Thierry Benita - atReal",
    author_email="contact@atreal.net",
    url="https://github.com/collective/collective.zopeedit/",
    license="ZPL",
    packages=packages,
    namespace_packages=["collective"],
    include_package_data=True,
    zip_safe=False,
    install_requires=install_requires,
    entry_points={
        "console_scripts": [
            "zopeedit = collective.zopeedit.zopeedit:main",
        ]
    },
    data_files=data_files(),
    windows=[
        {
            "script": os.path.join("collective", "zopeedit", "zopeedit.py"),
            "icon_resources": [
                (1, os.path.join("collective", "zopeedit", "win32", "zopeedit.ico"))
            ],
        }
    ],
    options={
        "py2app": {"argv_emulation": True},
    },
)
