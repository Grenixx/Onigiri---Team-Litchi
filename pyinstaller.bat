@echo off
pip install pyinstaller pygame moderngl numpy miniupnpc screeninfo
cd Onigiri_client
pyinstaller --onefile --add-data "data;data" --add-data "scripts;scripts" --icon="..\icone.ico" menu.py
mkdir ..\ClientBuild
copy dist\menu.exe ..\ClientBuild\Onigiri.exe
copy logo.png ..\ClientBuild\
xcopy /E /I /Y data ..\ClientBuild\data
xcopy /E /I /Y scripts ..\ClientBuild\scripts

cd ..\Onigiri_server
pyinstaller --onefile --add-data "data;data" --icon="..\icone.ico" server.py
mkdir ..\ServerBuild
copy dist\server.exe ..\ServerBuild\Onigiri_server.exe
copy dist\server.exe ..\ClientBuild\Onigiri_server.exe
xcopy /E /I /Y data ..\ServerBuild\data
xcopy /E /I /Y data ..\ClientBuild\data

rmdir /S /Q dist
rmdir /S /Q build
rmdir /S /Q ..\Onigiri_client\dist
rmdir /S /Q ..\Onigiri_client\build
pause
