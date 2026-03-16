import json
import time
import urllib.request
import urllib.error
import threading

# REMPLACE CETTE URL PAR LA TIENNE
FIREBASE_URL = "https://onigiri-83780-default-rtdb.europe-west1.firebasedatabase.app/"

# Nom du dossier dans la base de données
LOBBY_PATH = "/lobbies"

def get_public_ip():
    """Récupère l'IP publique de la machine via un service externe."""
    try:
        with urllib.request.urlopen('https://api.ipify.org') as response:
            return response.read().decode('utf-8')
    except Exception as e:
        print(f"Erreur récupération IP publique: {e}")
        return "127.0.0.1"

class LobbyManager:
    """Gère l'enregistrement (côté serveur) et la découverte (côté client)."""
    
    def __init__(self, mode='client', server_port=5, server_name="Game Room"):
        self.mode = mode
        self.running = False
        
        # Args Server
        self.server_port = server_port
        self.server_name = server_name
        self.public_ip = None
        self.my_id = None # ID unique généré par Firebase

    def start_heartbeat(self):
        """(SERVEUR) Lance le thread qui signale notre présence toutes les 5s."""
        if self.mode != 'server': return
        
        print("Récupération de l'IP publique...")
        self.public_ip = get_public_ip()
        print(f"IP Publique détectée : {self.public_ip}")

        self.running = True
        threading.Thread(target=self._heartbeat_loop, daemon=True).start()

    def _heartbeat_loop(self):
        while self.running:
            try:
                self._send_beat()
            except Exception as e:
                print(f"Erreur heartbeat: {e}")
            time.sleep(5) # Signale 'je suis vivant' toutes les 5 secondes
        
        self._remove_lobby()

    def _send_beat(self):
        """Envoie ou met à jour les infos du serveur sur Firebase."""
        data = {
            "ip": self.public_ip,
            "port": self.server_port,
            "name": self.server_name,
            "last_seen": time.time()
        }
        
        payload = json.dumps(data).encode('utf-8')
        
        # Si on n'a pas encore d'ID, on fait un POST (création)
        if self.my_id is None:
            url = f"{FIREBASE_URL}{LOBBY_PATH}.json"
            req = urllib.request.Request(url, data=payload, method='POST')
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode())
                self.my_id = result['name'] # Firebase retourne {"name": "-Nv..."}
                print(f"Lobby enregistré avec l'ID : {self.my_id}")
        else:
            url = f"{FIREBASE_URL}{LOBBY_PATH}/{self.my_id}.json"
            req = urllib.request.Request(url, data=payload, method='PUT')
            with urllib.request.urlopen(req) as response:
                pass 

    def _remove_lobby(self):
        """Supprime le lobby de la base de données."""
        if self.my_id:
            try:
                url = f"{FIREBASE_URL}{LOBBY_PATH}/{self.my_id}.json"
                req = urllib.request.Request(url, method='DELETE')
                with urllib.request.urlopen(req) as response:
                    print("Lobby supprimé de la liste.")
            except:
                pass

    def stop(self):
        self.running = False
        self._remove_lobby()

    # -----------------------------
    # MÉTHODES CLIENT
    # -----------------------------
    
    @staticmethod
    def get_server_list():
        """(CLIENT) Récupère la liste des serveurs actifs."""
        try:
            # Récupérer sa propre IP pour gérer le NAT Loopback (se connecter à soi-même)
            my_ip = get_public_ip()
            
            url = f"{FIREBASE_URL}{LOBBY_PATH}.json"
            req = urllib.request.Request(url, method='GET')
            with urllib.request.urlopen(req) as response:
                data_str = response.read().decode('utf-8')
                if data_str == 'null': return []
                
                lobbies = json.loads(data_str)
                active_servers = []
                now = time.time()
                
                # Filtrer les vieux serveurs (> 15s d'inactivité)
                for lid, info in lobbies.items():
                    if 'last_seen' in info:
                        if now - info['last_seen'] < 15: # 15 secondes timeout
                            # --- FIX NAT LOOPBACK ---
                            # Si le serveur a la même IP publique que nous, on utilise localhost
                            if info.get('ip') == my_ip:
                                info['ip'] = "127.0.0.1"
                                info['name'] += " (Local)"
                            
                            active_servers.append(info)
                            
                return active_servers
        except Exception as e:
            print(f"Erreur récupération liste: {e}")
            return []
