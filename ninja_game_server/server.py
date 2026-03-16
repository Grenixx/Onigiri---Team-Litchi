import socket
import struct
import time
import miniupnpc
import os #pour listdir les level les faire looper entre eux

from TilemapServer import TilemapServer
from enemy_manager import Blob, EnemyManager

# Message types:
#  10 : Connexion
#   1 : Déconnexion
#   0 : Mise à jour du joueur (position/action)
#   3 : Suppression d’un ennemi
#   9 : Ping

import sys
# Ajout du chemin vers les scripts du client
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../ninja_game/scripts')))
try:
    from lobby_discovery import LobbyManager
except ImportError as e:
    print("Erreur import LobbyManager:", e)
    LobbyManager = None

# ==============================
# --- Player Manager ---
# ==============================

# ==============================
# --- Player Manager ---
# ==============================
class PlayerManager:
    def __init__(self):
        self.clients = {}   # addr -> id
        self.players = {}   # id -> (x, y, action:str, flip:bool)
        self.next_id = 1
        

    def add_player(self, addr):
        pid = self.next_id
        self.next_id += 1
        self.clients[addr] = pid
        self.players[pid] = (0, 0, 'idle', False, 1, 0.0, 0.0) # x, y, action, flip, weapon_id, vx, vy
        return pid

    def remove_player(self, addr):
        if addr not in self.clients:
            return
        pid = self.clients[addr]
        del self.clients[addr]
        if pid in self.players:
            del self.players[pid]
        return pid

    def update_player(self, addr, data):
        if addr not in self.clients:
            return
        pid = self.clients[addr]

        if len(data) < 19:
            return  # paquet trop court (maintenant 19 bytes avec vx, vy)

        x, y, vx, vy = struct.unpack("ffff", data[:16])
        action_id, flip_byte, weapon_id = struct.unpack("BBB", data[16:19])
        action_map = {0: 'idle', 1: 'run', 2: 'jump', 3: 'wall_slide', 4: 'slide', 5: 'attack_front', 6: 'attack_up', 7: 'attack_down'}
        action = action_map.get(action_id, 'idle')
        flip = bool(flip_byte)
        self.players[pid] = (x, y, action, flip, weapon_id, vx, vy)


# ==============================
# --- Game Server ---
# ==============================
class GameServer:
    def __init__(self,  local : bool = False, ip="0.0.0.0", port=5006, server_name="Ninja Server", rate=1/60):
        self.ip = ip
        self.port = port
        self.rate = rate
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((ip, port))
        self.sock.settimeout(0.002)

        self.next_map = 0

        # --- Charger la map ---
        self.map = TilemapServer()
        self.map_id = 0
        self.map.load(f"data/maps/{self.map_id}.json")
        print("carte chargée sur le serveur.")

        # --- Managers ---
        self.players = PlayerManager()
        self.EnemyManager = EnemyManager(self.map)
        self.last_update = time.time()

        print(f"Serveur en ligne sur {ip}:{port}")
        if not local:
            self.init_upnp()
        
        # Démarrage du Lobby Discovery (même en local pour tester)
        if LobbyManager:
            self.lobby = LobbyManager(mode='server', server_port=self.port, server_name=server_name)
            self.lobby.start_heartbeat()

    def init_upnp(self):
        upnp = miniupnpc.UPnP()
        upnp.discoverdelay = 200
        upnp.discover()
        upnp.selectigd()
        try:
            upnp.addportmapping(self.port, 'UDP', upnp.lanaddr, self.port, 'Python Game Server', '')
            print(f"UPnP : port {self.port} ouvert ! IP publique : {upnp.externalipaddress()}")
        except Exception as e:
            print("UPnP non disponible :", e)

    # ---------------------------
    # --- Boucle principale ---
    # ---------------------------
    def run(self):
        print("Serveur en cours d’exécution...")
        try:
            while True:
                try:
                    data, addr = self.sock.recvfrom(1024)
                    self.handle_message(data, addr)
                except ConnectionResetError:
                    # Ignore les erreurs quand un client quitte brutalement
                    continue
                except socket.timeout:
                    pass
                except OSError as e:
                    print("Erreur socket:", e)
                    continue

                now = time.time()
                if now - self.last_update >= self.rate:
                    self.last_update = now
                    self.update_world()
        except KeyboardInterrupt:
            print("Arrêt du serveur...")
            if hasattr(self, 'lobby') and self.lobby:
                self.lobby.stop()
            self.sock.close()


    def handle_message(self, data, addr):
        msg_type = data[0]


        if msg_type == 10: # 10 = connexion
            if addr not in self.players.clients:
                pid = self.players.add_player(addr)
                print(f"New player: {pid} ({addr})") 
            else:
                pid = self.players.clients[addr]
            
            # renvoyer le PID à chaque paquet de connexion reçu
            self.sock.sendto(struct.pack("I", pid), addr)
            return

        # -- ping --
        if msg_type == 9:  # 9 = ping
            self.sock.sendto(b'\x09' + data[1:9], addr)

        # --- Déconnexion ---
        if msg_type == 1:
            pid = self.players.remove_player(addr)
            print(f"Déconnexion du joueur {pid}")
            # Supprime la cible si l’ennemi le suivait
            for e in self.EnemyManager.enemies.values():
                if e.properties['target_player'] == pid:
                    e.properties['target_player'] = None
            return

        # --- Mise à jour joueur ---
        if msg_type == 0 and addr in self.players.clients and len(data) >= 10:
            self.players.update_player(addr, data[1:])

        # --- Suppression ennemi ---
        if msg_type == 3 and len(data) >= 5:
            eid = struct.unpack("I", data[1:5])[0]
            if eid in self.EnemyManager.enemies:
                del self.EnemyManager.enemies[eid]
            return

        if msg_type == 8 and len(data) >= 12:
            eid, damage_number, pid = struct.unpack("III", data[1:13])
            if eid in self.EnemyManager.enemies:
                self.EnemyManager.enemies[eid].damage(damage_number, pid)
            return

        # --- Request Level Change (Debug) ---
        if msg_type == 5:
            self.next_map = int((self.map_id) + 1) % len(os.listdir("data/maps")) #modulo nombre de map dans le fichier
            self.change_level(self.next_map)
            return

    # ---------------------------
    # --- Mises à jour ---
    # ---------------------------
    def update_world(self):
        self.EnemyManager.update(self.players.players)
        
        # Example condition de changement de map automatique (tous les ennemis morts)
        if len(self.EnemyManager.enemies) == 0:
            self.next_map = int((self.map_id) + 1) % len(os.listdir("data/maps")) #modulo nombre de map dans le fichier
            self.change_level(self.next_map)

        self.broadcast_state()

    def change_level(self, map_id):
        try:
            filename = f"data/maps/{map_id}.json"
            self.map.load(filename)
            self.map_id = map_id
        except FileNotFoundError:
            print(f"Map {map_id} not found!")
            return

        print(f"Map changée vers {map_id}")
        self.EnemyManager.reset(self.map)
        
        # Reset players (Spawn au spawn point si disponible)
        spawn_pos = (50, 50)
        if hasattr(self.map, 'spawners'):
            for s in self.map.spawners:
                if s['variant'] == 0: # Player spawn
                    spawn_pos = s['pos']
                    break
        
        for pid in self.players.players:
            _, _, a, f, w, vx, vy = self.players.players[pid]
            self.players.players[pid] = (spawn_pos[0], spawn_pos[1], a, f, w, vx, vy)

        self.broadcast_map_change(map_id)

    def broadcast_map_change(self, map_id):
        # Type 4 : Changement de map
        payload = struct.pack("<BI", 4, int(map_id))
        for addr in self.players.clients:
            self.sock.sendto(payload, addr)

    # ---------------------------
    # --- Envoi aux clients ---
    # ---------------------------
    def broadcast_state(self):
        # Type 2 : Update World
        # On préfixe avec \x02
        payload = struct.pack("BB", 2, len(self.players.players))
        for pid, (x, y, action, flip, weapon_id, vx, vy) in self.players.players.items():
            action_bytes = action.encode('utf-8')[:15]
            action_bytes += b'\x00' * (15 - len(action_bytes))
            flip_byte = b'\x01' if flip else b'\x00'
            payload += struct.pack("Iffff", pid, x, y, vx, vy) + action_bytes + flip_byte + struct.pack("B", weapon_id)

        payload += struct.pack("B", len(self.EnemyManager.enemies))
        #for eid, e in self.EnemyManager.enemies.items():
        #    payload += struct.pack("Iff?", eid, e.properties['x'], e.properties['y'], e.properties['flip'])

        for eid, e in self.EnemyManager.enemies.items():
            state = e.properties.get("state", "")
            state_bytes = state.encode("utf-8")[:15]
            state_bytes += b'\x00' * (15 - len(state_bytes))

            payload += (
                struct.pack("Iff?", eid,
                            e.properties['x'],
                            e.properties['y'],
                            e.properties['flip'])
                + state_bytes
            )
        for addr in self.players.clients:
            self.sock.sendto(payload, addr)


# ==============================
# --- Lancement ---
# ==============================
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Ninja Game Server')
    parser.add_argument('--start_local', type=int, default=1, help='Whether the server starts in local')
    parser.add_argument('--name', type=str, default="Ninja Server", help='Name of the server')
    args = parser.parse_args()
    server = GameServer(local=args.start_local == 1, server_name=args.name)  # mode local == True
    server.run()
