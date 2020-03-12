# -*- coding: utf-8 -*-

from setuptools import setup, find_packages


with open('README.md') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='salabim_plus',
    version='0.0.dev2',
    description='Package for running more complex processes using salabim',
    long_description=readme,
    author='Jack Nelson',
    author_email='jack.nelson245@gmail.com',
    url='https://github.com/JackNelson/salabim_plus',
    license=license,
    packages=find_packages(exclude=('tests', 'docs')),
    install_requires=[
        'pandas>=1.0.1',
        'plotly>=4.4.1',
        'salabim>=20.0.1'
    ]
)