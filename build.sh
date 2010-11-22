project_path=$1

mkdir bin

cd tracgenericclass/trunk
python setup.py bdist_egg
cp dist/*.egg ../../bin

cd ../../tracgenericworkflow/trunk
python setup.py bdist_egg
cp dist/*.egg ../../bin

cd ../../sqlexecutor/trunk
python setup.py bdist_egg
cp dist/*.egg ../../bin

cd ../../testman4trac/trunk
python setup.py bdist_egg
cp dist/*.egg ../../bin

cd ../..

cp *.txt bin

cp bin/*.egg $project_path/plugins
