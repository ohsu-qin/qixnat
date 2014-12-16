import os
import re
import subprocess
import glob
from setuptools import (setup, find_packages)

def version(package):
    """
    Return package version as listed in the `__init.py__` `__version__`
    variable.
    """
    init_py = open(os.path.join(package, '__init__.py')).read()
    return re.search("__version__ = ['\"]([^'\"]+)['\"]", init_py).group(1)


def requires():
    """
    @return: the ``requirements.txt`` package specifications
    """
    with open('requirements.txt') as f:
        return f.read().splitlines()
        

def readme():
    with open("README.rst") as f:
        return f.read()


setup(
    name = 'qixnat',
    version = version('qixnat'),
    author = 'OHSU Knight Cancer Institute',
    author_email = 'loneyf@ohsu.edu',
    packages = find_packages(exclude=['test**']),
    scripts = glob.glob('bin/*'),
    url = 'https://github.com/ohsu-qin/qixnat',
    description = 'Quantitative Imaging XNAT helper.',
    long_description = readme(),
    classifiers = [
        'Development Status :: 5 - Production/Stable',
        'Topic :: Scientific/Engineering :: Bio-Informatics',
        'Environment :: Console',
        'Intended Audience :: Science/Research',
        'License :: Other/Proprietary License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
    ],
    install_requires = requires()
)
