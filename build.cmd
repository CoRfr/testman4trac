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
rem python setup.py update_catalog -l it_IT
rem python setup.py update_catalog_js -l it_IT
rem python ./setup.py compile_catalog -f -l it_IT
rem python ./setup.py compile_catalog_js -f -l it_IT

python setup.py bdist_egg
xcopy /y dist\*.egg ..\..\bin

cd ..\..

xcopy /y *.txt bin

xcopy /y bin\*.egg %1\plugins
