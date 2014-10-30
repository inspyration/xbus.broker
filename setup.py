# -*- encoding: utf-8 -*-
import os
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'README.rst')) as f:
    README = f.read()

with open(os.path.join(here, 'CHANGES.rst')) as f:
    CHANGES = f.read()

with open(os.path.join(here, 'CONTRIBUTORS.rst')) as f:
    CONTRIBUTORS = f.read()

setup(
    name='xbus.broker',
    version='0.1',
    description='Xbus Broker written in Python3',
    long_description="{}\n{}\n{}".format(README, CONTRIBUTORS, CHANGES),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: Financial and Insurance Industry",
        "Intended Audience :: Information Technology",
        "Intended Audience :: Other Audience",
        "Intended Audience :: Science/Research",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: Implementation :: CPython",
    ],
    author='Florent Aide',
    author_email='florent.aide@xcg-consulting.fr',
    url='https://bitbucket.org/xcg/xbus.broker',
    keywords='xbus',
    packages=find_packages(exclude=['tests', ]),
    namespace_packages=['xbus'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        "setuptools",
        "aiopg >= 0.4.1",
        "aiozmq >= 0.5.2",
        "hiredis",
        "aioredis >= 0.1.4",
        "msgpack-python",
        "sqlalchemy >= 0.9.8",
    ],
    tests_require=[
        "nose",
        "coverage",
    ],
    test_suite='nose.collector',
    entry_points={
        "console_scripts": [
            'setup_xbusbroker = xbus.broker.cli:setup_xbusbroker',
            'start_xbusbroker = xbus.broker.cli:start_server',
        ],
    },
)
