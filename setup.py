#!/usr/bin/env python3
import os

from setuptools import find_packages, setup


def exec_file(path_segments):
    """Execute a single python file to get the variables defined in it"""
    result = {}
    code = read_file(path_segments)
    exec(code, result)
    return result


def read_file(path_segments):
    """Read a file from the package. Takes a list of strings to join to
    make the path"""
    file_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), *path_segments)
    with open(file_path) as f:
        return f.read()


version = exec_file(("matrix_reminder_bot", "__init__.py"))["__version__"]
long_description = read_file(("README.md",))


setup(
    name="matrix-reminder-bot",
    version=version,
    url="https://github.com/anoadragon453/matrix-reminder-bot",
    description="A matrix bot to remind you about things!",
    packages=find_packages(exclude=["tests", "tests.*"]),
    install_requires=[
        "matrix-nio[e2e]>=0.10.0",
        "Markdown>=3.1.1",
        "PyYAML>=5.1.2",
        "dateparser>=0.7.4",
        "readabledelta>=0.0.2",
        "apscheduler>=3.6.3",
        "pytz>=2020.1",
    ],
    extras_require={
        "postgres": ["psycopg2>=2.8.5"],
    },
    classifiers=[
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    long_description=long_description,
    # Allow the user to run the bot with `matrix-reminder-bot ...`
    scripts=["matrix-reminder-bot"],
)
