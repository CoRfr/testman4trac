set VER=%1

zip -r testman4trac.%VER%.zip bin

mkdir testman4trac.%VER%

xcopy /y *.sh testman4trac.%VER%
xcopy /y *.cmd testman4trac.%VER%
xcopy /y *.txt testman4trac.%VER%
xcopy /y /s /i sqlexecutor testman4trac.%VER%\sqlexecutor
xcopy /y /s /i testman4trac testman4trac.%VER%\testman4trac
xcopy /y /s /i tracgenericclass testman4trac.%VER%\tracgenericclass
xcopy /y /s /i tracgenericworkflow testman4trac.%VER%\tracgenericworkflow

cd testman4trac.%VER%

call clean.cmd

cd ..

zip -r testman4trac.%VER%.src.zip testman4trac.%VER%

rmdir /s /q testman4trac.%VER%
