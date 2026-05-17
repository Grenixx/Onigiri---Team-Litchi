Yo c est Enzo 
Pour lancer le jeu faut lancer un server le plus recent dans Onigiri_server
Puis dans Onigiri_client lancer game.py

Dependencies: 
pip install pygame moderngl numpy miniupnpc screeninfo

cd Onigiri_server
pyinstaller --onefile server.py
Copy-Item -Recurse -Force "data" "dist\data"

cd ../Onigiri_client

pyinstaller --onefile --add-data "data;data" --add-data "scripts;scripts" game.py
