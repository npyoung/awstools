#!/usr/bin/env python
from setuptools import setup

setup(
    name="awstools",
    version="0.0.1",
    description="Concise command line interface to make it easier to be productive with AWS",
    license="MIT",
    author="Noah Young",
    author_email="noahpyoung@gmail.com",
    url="https://github.com/npyoung/awstools",
    packages=['awstools'],
    install_requires=[
        'click',
        'boto3',
        'prettytable',
    ],
    entry_points={
        'console_scripts': [
            'awstools=awstools.awstools:main'
        ]
    }
)
