mkdir bin

cd tracgenericclass\trunk
python setup.py bdist_egg
xcopy /y dist\*.egg ..\..\bin

cd ..\..\tracgenericworkflow\trunk
python setup.py bdist_egg
xcopy /y dist\*.egg ..\..\bin

cd ..\..\sqlexecutor\trunk
python setup.py bdist_egg
xcopy /y dist\*.egg ..\..\bin

cd ..\..\testman4trac\trunk

rem python setup.py extract_messages
rem python setup.py extract_messages_js
rem python setup.py update_catalog -l it
rem python setup.py update_catalog_js -l it
rem python setup.py compile_catalog -f -l it
rem python setup.py compile_catalog_js -f -l it
rem python setup.py update_catalog -l es
rem python setup.py update_catalog_js -l es
rem python setup.py compile_catalog -f -l es
rem python setup.py compile_catalog_js -f -l es
rem python setup.py update_catalog -l de
rem python setup.py update_catalog_js -l de
rem python setup.py compile_catalog -f -l de
rem python setup.py compile_catalog_js -f -l de
rem python setup.py update_catalog -l fr
rem python setup.py update_catalog_js -l fr
rem python setup.py compile_catalog -f -l fr
rem python setup.py compile_catalog_js -f -l fr

python setup.py bdist_egg
xcopy /y dist\*.egg ..\..\bin

cd ..\..

xcopy /y *.txt bin

xcopy /y bin\*.egg %1\plugins
