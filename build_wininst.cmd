mkdir bin

cd tracgenericclass\trunk
python setup.py bdist_wininst

cd ..\..\tracgenericworkflow\trunk
python setup.py bdist_wininst

cd ..\..\sqlexecutor\trunk
python setup.py bdist_wininst

cd ..\..\testman4trac\trunk
python setup.py bdist_wininst

cd ..\..

xcopy /y *.txt bin

