#!/usr/bin/env python3

from setuptools import setup
from setuptools import find_packages


setup(
    name="litehelloworld",
    description="Litex core template repository that can be used to quick start a custom core design",
    author="AUTHOR NAME HERE",
    author_email="EMAIL HERE",
    version="0.0.1",
    url="https://yourprojectwebiste",
    download_url="https://github.com/litex-hub/litehelloworld",
    test_suite="test",
    license="To Be Done",
    python_requires=">3.6",
    packages=find_packages(exclude=("test*", "sim*", "doc*", "examples*")),
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "litehelloworld_manager=litehelloworld.manager:main",
        ],
    },
)
