from setuptools import setup

setup(
    name='SQLExecutor',
    version='1.0.3',
    packages=['sqlexecutor'],
    package_data={'sqlexecutor' : ['*.txt', 'templates/*.html', 'htdocs/*.*', 'htdocs/js/*.js', 'htdocs/css/*.css', 'htdocs/images/*.*']},
    author = 'Roberto Longobardi',
    author_email='seccanj@gmail.com',
    license='BSD. See the file LICENSE.txt contained in the package.',
    url='http://trac-hacks.org/wiki/TestManagerForTracPlugin',
    download_url='https://sourceforge.net/projects/testman4trac/files/',
    description='Test management plugin for Trac - SQL Executor component',
    long_description='A Trac plugin to create Test Cases, organize them in catalogs and track their execution status and outcome. This module provides a generic SQL executor to help debugging your application.',
    keywords='trac plugin generic class framework persistence sql execution run test case management project quality assurance statistics stats charts charting graph',
    entry_points = {'trac.plugins': ['sqlexecutor = sqlexecutor']}
    )
