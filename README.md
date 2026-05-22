Au nom de toute la team litchi, nous vous remercions de lancer notre jeu et vous n'en serez pas déçu.
Pour ce faire c'est très simple, voici plusieurs méthodes :

1. La première et la plus simple, depuis les exécutables :
   - Lancez `Onigiri_server\dist\server.exe`
   - Puis lancez `Onigiri_client\dist\game.exe`

2. La deuxième, depuis le code source :
   - Lancez le serveur : `Onigiri_server\server.py`
   - Puis lancez le client : `Onigiri_client\game.py`

Pour compiler les exécutables vous-mêmes :

```
pip install pygame moderngl numpy miniupnpc screeninfo

cd Onigiri_server
pyinstaller --onefile server.py
Copy-Item -Recurse -Force "data" "dist\data"

cd ../Onigiri_client
pyinstaller --onefile --add-data "data;data" --add-data "scripts;scripts" game.py
```
