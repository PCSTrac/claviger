#!/usr/bin/env python

import sys
from setuptools import setup

setup(
    name='claviger',
    version='0.5.0',
    description='Manages users and SSH keys across multiple servers',
    long_description="{0:s}". format(open('README.md').read()),
    author='Gregory Benner',
    author_email='gregory.benner@pcstrac.com',
    url='http://github.com/PCSTrac/claviger/',
    packages=['claviger', 'claviger.tests'],
    package_dir={'claviger': 'src'},
    package_data={'claviger': [
                    'config.schema.yml']},
    test_suite='claviger.tests',
    license='GPL 3.0',
    zip_safe=False,
    install_requires=['demandimport >=0.3.0',
                      'PyYAML',
                      'six',
                      'tarjan',
                      'jsonschema',
                            ],
    entry_points = {
        'console_scripts': [
                'claviger = claviger.main:entrypoint',
            ]
        },
    classifiers=[
        # TODO
            ]
    ),
