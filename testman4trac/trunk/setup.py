# -*- coding: utf-8 -*-
#
# Copyright (C) 2010-2011 Roberto Bordolanghi
# 
# This file is part of the Test Manager plugin for Trac.
# 
# The Test Manager plugin for Trac is free software: you can 
# redistribute it and/or modify it under the terms of the GNU 
# General Public License as published by the Free Software Foundation, 
# either version 3 of the License, or (at your option) any later 
# version.
# 
# The Test Manager plugin for Trac is distributed in the hope that it 
# will be useful, but WITHOUT ANY WARRANTY; without even the implied 
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  
# See the GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with the Test Manager plugin for Trac. See the file LICENSE.txt. 
# If not, see <http://www.gnu.org/licenses/>.
#

from setuptools import setup

extra = {} 

try:
    from trac.util.dist import get_l10n_js_cmdclass 
    cmdclass = get_l10n_js_cmdclass() 
    if cmdclass: # OK, Babel is there
        extra['cmdclass'] = cmdclass 
        extractors = [ 
            ('**.py',                'python', None), 
            ('**/templates/**.html', 'genshi', None), 
            ('**/templates/**.txt',  'genshi', { 
                'template_class': 'genshi.template:TextTemplate' 
            }), 
        ] 
        extra['message_extractors'] = { 
            'testmanager': extractors, 
        }
except ImportError: 
    pass

setup(
    name='TestManager',
    version='1.4.9',
    packages=['testmanager','testmanager.upgrades'],
    package_data={
        'testmanager' : [
            '*.txt', 
            'templates/*.html', 
            'htdocs/js/*.js', 
            'htdocs/js/*.swf', 
            'htdocs/css/*.css', 
            'htdocs/css/blitzer/*.css', 
            'htdocs/css/blitzer/images/*.*', 
            'htdocs/css/images/*.*', 
            'htdocs/images/*.*', 
            'locale/*.*', 
            'locale/*/LC_MESSAGES/*.mo',
            'htdocs/testmanager/*.js'
        ]
    },
    author = 'Roberto Bordolanghi',
    author_email='seccanj@gmail.com',
    license='BSD. See the file LICENSE.txt contained in the package.',
    url='http://trac-hacks.org/wiki/TestManagerForTracPlugin',
    download_url='https://sourceforge.net/projects/testman4trac/files/',
    description='Test management plugin for Trac',
    long_description='A Trac plugin to create Test Cases, organize them in catalogs and track their execution status and outcome.',
    keywords='trac plugin test case management project quality assurance statistics stats charts charting graph',
    entry_points = {'trac.plugins': ['testmanager = testmanager']},
    dependency_links=['http://svn.edgewall.org/repos/genshi/trunk#egg=Genshi-dev', 'http://trac-hacks.org/wiki/TestManagerForTracPluginGenericClass', 'http://trac-hacks.org/wiki/TracGenericWorkflowPlugin'],
    install_requires=['Genshi >= 0.5', 'TracGenericClass >= 1.1.1', 'TracGenericWorkflow >= 1.0.3'],
    **extra
    )
