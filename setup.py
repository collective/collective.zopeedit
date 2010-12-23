#!/usr/bin/env python
# -*- coding: utf-8 -*-
##############################################################################
#
#   ZopeEdit, client for ExternalEditor
#
##############################################################################

from setuptools import setup, find_packages
import os
import sys
import glob
opj = os.path.join
# Open the VERSION file for reading.
try:
    f=open('docs/VERSION.txt', 'r')
except IOError:
    # zopeedit is not properly installed : try uninstalled path
    f=open('../../docs/VERSION.txt', 'r')  # Open the VERSION file for reading.
# Below, "[:-1]" means we omit the last character, which is "\n".
version = f.readline()[:-1]
f.close

try:
    import py2exe
except ImportError:
    if sys.platform == 'win32':
        raise

install_requires = ['setuptools']
if sys.platform == 'darwin':
    install_requires.extend(['pyobjc',
        'pyobjc-core',
        'pyobjc-framework-LaunchServices',
    ])

packages = find_packages(exclude=['ez_setup'])

def data_files():
    '''Build list of data files to be installed'''
    files = []

    files.append((opj('share','man','man1',''),['collective/zopeedit/man/zopeedit.1']))
    files.append((opj('share','mime','application'),['collective/zopeedit/posix/x-zope-edit-zem.xml']))
    files.append((opj('share','applications'),['collective/zopeedit/posix/zopeedit.desktop']))
    files.append((opj('share','icons'),['collective/zopeedit/posix/zopeedit.svg']))
    files.append((opj('collective','zopeedit', 'docs'), [f for
        f in glob.glob('docs/*') if os.path.isfile(f)]))
    files.append((opj('collective','zopeedit','docs'),['README.txt']))

    return files


setup(name='collective.zopeedit',
      app=[os.path.join('collective', 'zopeedit', 'zopeedit.py')],
      version=version,
      description="ZopeEdit : External Editor Client",
      long_description=open("README.txt").read() + "\n" +
                       open(os.path.join("docs", "HISTORY.txt")).read(),
      # Get more strings from
      # http://pypi.python.org/pypi?%3Aaction=list_classifiers
      classifiers=[
        "Programming Language :: Python",
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: Zope Public License",
        ],
      keywords='zope plone externaleditor zopeedit edition',
      author='Thierry Benita - atReal',
      author_email='contact@atreal.net',
      url='http://svn.plone.org/svn/collective/collective.zopeedit/',
      license='ZPL',
      packages=packages,
      namespace_packages=['collective'],
      include_package_data=True,
      zip_safe=False,
      install_requires=install_requires,
      entry_points = {
        'console_scripts': [
            'zopeedit = collective.zopeedit.zopeedit:main',
        ]
      },
      data_files = data_files(),
      windows=[{
              'script': os.path.join('collective','zopeedit','zopeedit.py'),
              'icon_resources': [(1, os.path.join('collective','zopeedit','win32','zopeedit.ico'))]
              }],
      options={"py2exe": {"packages": ["encodings", "Plugins", "win32com"]},
               "py2app" : {'argv_emulation':True},
              },
      )
