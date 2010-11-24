from setuptools import setup, find_packages
import os

version = '0.12.6'

setup(name='collective.zopeedit',
      version=version,
      description="ZopeEdit : External Editor Client",
      long_description=open("README.txt").read() + "\n" +
                       open(os.path.join("docs", "HISTORY.txt")).read(),
      # Get more strings from
      # http://pypi.python.org/pypi?%3Aaction=list_classifiers
      classifiers=[
        "Programming Language :: Python",
        ],
      keywords='zope plone externaleditor zopeedit edition',
      author='Thierry Benita - atReal',
      author_email='contact@atreal.net',
      url='http://svn.plone.org/svn/collective/collective.zopeedit/',
      license='ZPL',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['collective'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          # -*- Extra requirements: -*-
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
