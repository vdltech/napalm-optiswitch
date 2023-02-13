# -*- coding: iso-8859-15 -*-
"""setup.py file."""

from setuptools import setup, find_packages

__author__ = "Fredrik Rönnvall <fred@vdltech.net>"

with open("requirements.txt") as f:
    install_requires = f.read().strip().splitlines()

setup(
    name="napalm-optiswitch",
    version="0.2.1",
    packages=find_packages(),
    author="Fredrik Rönnvall",
    author_email="fredr@vdltech.net",
    description="Network Automation and Programmability Abstraction Layer with Multivendor support",
    classifiers=[
        "Topic :: Utilities",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS",
    ],
    url="https://github.com/vdltech/napalm-optiswitch",
    include_package_data=True,
    install_requires=install_requires,
)
