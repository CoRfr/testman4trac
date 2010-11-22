rmdir /s /q bin

cd tracgenericclass\trunk
rmdir /s /q build 
rmdir /s /q dist 
rmdir /s /q TracGenericClass.egg-info

cd ..\..\tracgenericworkflow/trunk
rmdir /s /q build 
rmdir /s /q dist 
rmdir /s /q TracGenericWorkflow.egg-info

cd ..\..\sqlexecutor/trunk
rmdir /s /q build 
rmdir /s /q dist 
rmdir /s /q SQLExecutor.egg-info

cd ..\..\testman4trac/trunk
rmdir /s /q build 
rmdir /s /q dist 
rmdir /s /q TestManager.egg-info

cd ..\..
