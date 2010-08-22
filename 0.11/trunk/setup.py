from setuptools import setup

setup(
    name='TestManager',
    version='1.1.1',
    packages=['testmanager'],
    package_data={'testmanager' : ['*.txt', 'templates/*.html', 'htdocs/js/*.js', 'htdocs/css/*.css', 'htdocs/images/*.*']},
    author = 'Roberto Longobardi, Marco Cipriani',
    author_email='seccanj@gmail.com',
    license='BSD. See the file LICENSE.txt contained in the package.',
    url='http://trac-hacks.org/wiki/TestManagerForTracPlugin',
    download_url='https://sourceforge.net/projects/testman4trac/files/',
    description='Test management plugin for Trac',
    long_description='A Trac plugin to create Test Cases, organize them in catalogs and track their execution status and outcome.',
    keywords='trac plugin test case management project quality assurance statistics stats charts charting graph',
    entry_points = {'trac.plugins': ['testmanager = testmanager']},
    dependency_links=['http://svn.edgewall.org/repos/genshi/trunk#egg=Genshi-dev'],
    install_requires=['Genshi >= 0.5'],
    )
