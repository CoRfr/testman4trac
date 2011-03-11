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
    version='1.4.4',
    packages=['testmanager'],
    package_data={
        'testmanager' : [
            '*.txt', 
            'templates/*.html', 
            'htdocs/js/*.js', 
            'htdocs/css/*.css', 
            'htdocs/css/images/*.*', 
            'htdocs/images/*.*', 
            'locale/*.*', 
            'locale/*/LC_MESSAGES/*.mo',
            'htdocs/testmanager/*.js'
        ]
    },
    author = 'Roberto Longobardi',
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
    **extra
    )
