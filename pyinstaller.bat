@echo off
cd Onigiri_client
pyinstaller --onefile --add-data "data;data" --add-data "scripts;scripts" --icon="..\icone.ico" menu.py
mkdir ..\..\ClientBuild
copy dist\menu.exe ..\..\ClientBuild\
xcopy /E /I /Y data ..\..\ClientBuild\data
xcopy /E /I /Y scripts ..\..\ClientBuild\scripts
 
cd ..\Onigiri_server
pyinstaller --onefile --add-data "data;data" --icon="..\icone.ico" server.py
mkdir ..\..\ServerBuild
copy dist\server.exe ..\..\ServerBuild\
xcopy /E /I /Y data ..\..\ServerBuild\data
pause
