#! /usr/bin/env python

from setuptools import setup


def readme():
    return """\
pyseminars
----------

This module downloads the various RSS feeds from LPENSL website,
and generate a calendar ics file.

"""


setup(name='pyseminars',
      version='1',
      description='pyseminars',
      long_description=readme(),
      url='https://gitlab.salort.eu/jsalort/pyseminars',
      author='Julien Salort',
      author_email='julien.salort@ens-lyon.fr',
      license='CeCILL-B',
      packages=['pyseminars'],
      )
