project_path=$1

cd tracgenericclass/trunk
python setup.py bdist_egg
cp dist/*.egg $project_path/plugins

cd ../../tracgenericworkflow/trunk
python setup.py bdist_egg
cp dist/*.egg $project_path/plugins

cd ../../sqlexecutor/trunk
python setup.py bdist_egg
cp dist/*.egg $project_path/plugins

cd ../../testman4trac/trunk
python setup.py bdist_egg
cp dist/*.egg $project_path/plugins

cd ../..

