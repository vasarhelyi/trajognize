"""Setup script for trajognize."""

from glob import glob
from os.path import basename, splitext
from setuptools import setup, find_packages

requires = [
    "numpy",
    "spgm",
]

__version__ = None
exec(open("trajognize/version.py").read())

setup(
    name="trajognize",
    version=__version__,
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.7",
    requires=requires,
    entry_points={"console_scripts": ["trajognize = trajognize.main:main"]},
)