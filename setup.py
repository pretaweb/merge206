from setuptools import setup, find_packages
import sys, os

version = '1.0'

setup(name='merge206',
      version=version,
      description="Web log util to arregate 206 requests",
      long_description="""\
"""+open("README.md").read(),
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='apache, nginx, log analyzer',
      author='Dylan Jay',
      author_email='software@pretaweb.com',
      url='http://pypi.python.org/pypi/merge206',
      license='GPL',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          "apache_log_parser", "docopt"
          # -*- Extra requirements: -*-
      ],
      entry_points = {
                      'console_scripts': ['merge206 = merge206:main'],
                      },
      )