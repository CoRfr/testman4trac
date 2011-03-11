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

#python setup.py extract_messages
#python setup.py extract_messages_js
#python ./setup.py update_catalog -l it
#python ./setup.py update_catalog_js -l it
#python ./setup.py compile_catalog -f -l it
#python ./setup.py compile_catalog_js -f -l it

python setup.py bdist_egg
cp dist/*.egg ../../bin

cd ../..

cp *.txt bin

cp bin/*.egg $project_path/plugins
