from distutils.command.build_py import build_py
import os
import sys

from setuptools import setup

from eulexistdb import __version__

# fullsplit and packages calculation inspired by django setup.py

def fullsplit(path):
    result = []
    while path:
        path, tail = os.path.split(path)
        result.append(tail)
    result.reverse()
    return result

packages = []
for path, dirs, files in os.walk(__file__):
    if '.svn' in dirs:
        dirs.remove('.svn')
    if '__init__.py' in files:
        packages.append(path.replace(os.path.sep, '.'))

setup(
    name='eulexistdb',
    version=__version__,
    author='Emory University Libraries',
    author_email='libsysdev-l@listserv.cc.emory.edu',
    packages=packages,
    package_dir={'': '.'},
    install_requires=[
#        'eulxml',
    ],
)
