Yo c est Enzo 
Pour lancer le jeu faut lancer un server le plus recent dans Onigiri_server
Puis dans Onigiri_client lancer game.py

Dependencies: 
pip install pygame moderngl numpy miniupnpc screeninfo

C:\Users\enzom\Downloads\Onigiri\Onigiri_client>pyinstaller --onefile --add-data "data;data" --add-data "scripts;scripts" game.py

Pour compiler en exe il faut allez dans Onigiri_client puis lancer la commande suivante :
pyinstaller --onefile --add-data "data;data" --add-data "scripts;scripts" game.py