@echo off
title Onigiri Server
cd /d "%~dp0"
python server.py %*
pause
