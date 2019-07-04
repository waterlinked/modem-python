# -*- coding: utf-8 -*-
"""setup.py"""

from setuptools import setup


def read_content(filepath):
    with open(filepath) as fobj:
        return fobj.read()


classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python",
    "Programming Language :: Python :: 2",
    "Programming Language :: Python :: 2.7",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.6",
    "Programming Language :: Python :: 3.7",
    "Programming Language :: Python :: Implementation :: CPython",
    "Programming Language :: Python :: Implementation :: PyPy",
]


long_description = (
    read_content("README.md")
#    read_content(os.path.join("docs/source", "CHANGELOG.rst"))
)

requires = [
    'setuptools',
    'pyserial',
    'crcmod',
]

extras_require = {
#   'reST': ['Sphinx'],
    }

setup(name='wlmodem',
      version='1.1.1',
      description='Python library for Water Linked underwater modems',
      long_description=long_description,
      long_description_content_type="text/markdown",
      author='Water Linked AS',
      author_email='support@waterlinked.com',
      url='https://www.waterlinked.com',
      classifiers=classifiers,
      packages=['wlmodem'],
      data_files=[],
      install_requires=requires,
      include_package_data=True,
      extras_require=extras_require,
)
