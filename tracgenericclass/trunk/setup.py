from setuptools import setup

setup(
    name='TracGenericClass',
    version='1.0.4',
    packages=['tracgenericclass'],
    package_data={'tracgenericclass' : ['*.txt', 'templates/*.html', 'htdocs/*.*', 'htdocs/js/*.js', 'htdocs/css/*.css', 'htdocs/images/*.*']},
    author = 'Roberto Longobardi',
    author_email='seccanj@gmail.com',
    license='BSD. See the file LICENSE.txt contained in the package.',
    url='http://trac-hacks.org/wiki/TestManagerForTracPlugin',
    download_url='https://sourceforge.net/projects/testman4trac/files/',
    description='Test management plugin for Trac - Trac Generic Class component',
    long_description='A Trac plugin to create Test Cases, organize them in catalogs and track their execution status and outcome. This module provides a framework to help creating classes on Trac that: are persisted on the DB, support change history, Support extensibility through custom properties that the User can specify declaratively in the trac.ini file. Also provides an intermediate class to build objects that wrap Wiki pages, plus additional properties.',
    keywords='trac plugin generic class framework persistence test case management project quality assurance statistics stats charts charting graph',
    entry_points = {'trac.plugins': ['tracgenericclass = tracgenericclass']}
    )
