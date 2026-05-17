Salut c'est team litchi 
Pour lancer le jeu a partire du source code faut lancer le server dans Onigiri_server
Puis dans Onigiri_client lancer game.py

Sinon depuis les exec lancer juste le server puis le client

Pour compiler les exec server et client :
pip install pygame moderngl numpy miniupnpc screeninfo

cd Onigiri_server

pyinstaller --onefile server.py

Copy-Item -Recurse -Force "data" "dist\data"

cd ../Onigiri_client

pyinstaller --onefile --add-data "data;data" --add-data "scripts;scripts" game.py
