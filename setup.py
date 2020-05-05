#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
dataiq RESTful API
"""
from setuptools import setup, find_packages


setup(name="vlab-dataiq-api",
      author="Nicholas Willhite,",
      author_email='willnx84@gmail.com',
      version='2020.05.05',
      packages=find_packages(),
      include_package_data=True,
      package_files={'vlab_dataiq_api' : ['app.ini']},
      description="dataiq",
      install_requires=['flask', 'ldap3', 'pyjwt', 'uwsgi', 'vlab-api-common',
                        'ujson', 'cryptography', 'vlab-inf-common', 'celery']
      )
