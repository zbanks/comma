#!/usr/bin/env python

import fnmatch
import glob
import os
import sys

from setuptools import setup

VERSION = "0.1"

setup(
    name='comma',
    version=VERSION,
    description='CSV library for humans',
    author='Zach Banks',
    author_email='zjbanks@gmail.com',
    url='https://github.com/zbanks/comma',
    packages=[
        'comma', 
    ],
    download_url="https://github.com/zbanks/comma/tarball/{}".format(VERSION),
    zip_safe=True,
    scripts=[
    ],
    package_dir={
    },
    package_data={
        'comma': [
        ],
    },
)
