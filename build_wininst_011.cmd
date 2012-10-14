mkdir bin

cd tracgenericclass\0.11
python setup.py bdist_wininst

cd ..\..\tracgenericworkflow\0.11
python setup.py bdist_wininst

cd ..\..\sqlexecutor\trunk
python setup.py bdist_wininst

cd ..\..\testman4trac\0.11
python setup.py bdist_wininst

cd ..\..

xcopy /y *.txt bin

