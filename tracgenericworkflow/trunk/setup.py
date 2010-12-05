from setuptools import setup

setup(
    name='TracGenericWorkflow',
    version='1.0.2',
    packages=['tracgenericworkflow'],
    package_data={'tracgenericworkflow' : ['*.txt', 'templates/*.html', 'htdocs/*.*', 'htdocs/js/*.js', 'htdocs/css/*.css', 'htdocs/images/*.*']},
    author = 'Roberto Longobardi',
    author_email='seccanj@gmail.com',
    license='BSD. See the file LICENSE.txt contained in the package.',
    url='http://trac-hacks.org/wiki/TestManagerForTracPlugin',
    download_url='https://sourceforge.net/projects/testman4trac/files/',
    description='Test management plugin for Trac - Generic Workflow Engine component',
    long_description='A Trac plugin to create Test Cases, organize them in catalogs and track their execution status and outcome. This module provides a generic workflow engine working on any Trac Resource.',
    keywords='trac plugin test case management workflow engine resource project quality assurance statistics stats charts charting graph',
    entry_points = {'trac.plugins': ['tracgenericworkflow = tracgenericworkflow']},
    dependency_links=['http://svn.edgewall.org/repos/genshi/trunk#egg=Genshi-dev'],
    install_requires=['Genshi >= 0.5'],
    )
