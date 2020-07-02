"""setup.py file."""

import uuid

from setuptools import setup, find_packages

__author__ = 'Fredrik Rönnvall <fredronn@gmail.com>'

with open('requirements.txt') as f:
    install_requires = f.read().strip().splitlines()

setup(
    name="napalm-optiswitch",
    version="0.1.0",
    packages=find_packages(),
    author="Fredrik Rönnvall",
    author_email="fredronn@gmail.com",
    description="Network Automation and Programmability Abstraction Layer with Multivendor support",
    classifiers=[
        'Topic :: Utilities',
         'Programming Language :: Python',
         'Programming Language :: Python :: 2',
         'Programming Language :: Python :: 2.7',
        'Operating System :: POSIX :: Linux',
        'Operating System :: MacOS',
    ],
    url="https://github.com/fredronnv/napalm-optiswitch",
    include_package_data=True,
    install_requires=install_requires,
)
