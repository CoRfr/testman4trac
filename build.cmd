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
python setup.py bdist_egg
xcopy /y dist\*.egg ..\..\bin

cd ..\..

xcopy /y *.txt bin

xcopy /y bin\*.egg %1\plugins
