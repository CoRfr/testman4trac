VER=$1

zip -r testman4trac.$VER.zip bin

mkdir testman4trac.$VER

cp *.sh testman4trac.$VER
cp *.txt testman4trac.$VER
cp *.cmd testman4trac.$VER
cp -R sqlexecutor testman4trac.$VER
cp -R testman4trac testman4trac.$VER
cp -R tracgenericclass testman4trac.$VER
cp -R tracgenericworkflow testman4trac.$VER

cd testman4trac.$VER

. ./clean.sh
find . -type d -name .svn -print -exec rm -rf {} \;

cd ..

zip -r testman4trac.$VER.src.zip testman4trac.$VER

rm -rf testman4trac.$VER
