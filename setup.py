#!/usr/bin/env python
from setuptools import setup

setup(
    name="awstools",
    description="Scripts to make it easier to be productive with AWS",
    license="MIT",
    author="Noah Young",
    author_email="noahpyoung@gmail.com",
    url="https://github.com/npyoung/awstools",
    packages=['awstools'],
    entry_points={
        'console_scripts': [
            'awstools=awstools.awstools:main'
        ]
    }
)
